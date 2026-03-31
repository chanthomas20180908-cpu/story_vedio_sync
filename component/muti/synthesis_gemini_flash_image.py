"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: prompt + (optional) 本地图片路径列表
Output: 生成图片文件（落盘到 picture_results）
Pos: Gemini Flash 图片生成（最小可用版本）

说明（最简实现约束）：
- 模型固定：gemini-2.5-flash-image
- API Key：环境变量 GEMINI_API_KEY（或显式传入）
- 图片入参：只支持本地路径；允许多张
- 传图时：会先上传到 OSS（upload_file_to_oss(path, 300)），仅用于记录/回显，不参与 Gemini 请求数据链路
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import Image

import config.config as config
from config.logging_config import get_logger
from util.util_url import upload_file_to_oss_dedup_with_meta

logger = get_logger(__name__)


def _resolve_api_key(api_key: str | None) -> str:
    if api_key:
        return api_key

    # 跟项目现有习惯保持一致：优先尝试加载 env/default.env
    try:
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
    except Exception:
        # 不阻断：允许用户自行 export 环境变量
        pass

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("未找到 GEMINI_API_KEY，请设置环境变量或在函数参数中传入 api_key")
    return key


def gemini_flash_generate_image(
    prompt: str,
    image_paths: list[str] | None = None,
    api_key: str | None = None,
    save_dir: Path | str | None = None,
    oss_expire_seconds: int = 300,
    aspect_ratio: str | None = None,
    request_timeout_seconds: int = 300,
) -> tuple[list[str], dict[str, Any]]:
    """Gemini Flash 文生图 / 图文生图（最小实现）

    Args:
        prompt: 文本提示词
        image_paths: 本地图片路径列表（可选，支持多张）
        api_key: Gemini API Key（可选；不传则读 GEMINI_API_KEY）
        save_dir: 输出目录（默认 config.PICTURE_RESULTS_DIR）
        oss_expire_seconds: 上传到 OSS 的 URL 有效期（秒），默认 300

    Returns:
        (saved_paths, meta)
    """

    # 这里采用“函数内导入”，避免在未安装 google-genai 时影响项目其他模块导入
    from google import genai

    if not prompt or not prompt.strip():
        raise ValueError("prompt 不能为空")

    # 重试 + 退避等待（尽量自动恢复：网络抖动/服务端偶发空返回等）
    retry_max_attempts = 5
    retry_initial_sleep_seconds = 2.0
    retry_backoff_multiplier = 2.0
    retry_max_sleep_seconds = 30.0

    key = _resolve_api_key(api_key)
    out_dir = Path(save_dir) if save_dir is not None else Path(config.PICTURE_RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_paths = image_paths or []

    meta: dict[str, Any] = {
        "model": "gemini-2.5-flash-image",
        "prompt": prompt,
        "input_image_paths": list(image_paths),
        "input_image_oss_urls": [],
        "oss_uploads": [],
        "text_parts": [],
        "saved_paths": [],
        "requested_aspect_ratio": aspect_ratio,
        "request_timeout_seconds": request_timeout_seconds,
        "retry_max_attempts": retry_max_attempts,
        "retry_initial_sleep_seconds": retry_initial_sleep_seconds,
        "retry_backoff_multiplier": retry_backoff_multiplier,
        "retry_max_sleep_seconds": retry_max_sleep_seconds,
        "attempts": [],
    }

    contents: list[Any] = [prompt]

    if image_paths:
        # OSS 上传仅用于记录/回显，不参与 Gemini 请求数据链路；因此这里采用 best-effort。
        image_url_list: list[str] = []
        oss_uploads: list[dict[str, Any]] = []
        for image_path in image_paths:
            try:
                url, up_meta = upload_file_to_oss_dedup_with_meta(image_path, oss_expire_seconds)
                image_url_list.append(url)
                oss_uploads.append(up_meta)
            except Exception as e:
                logger.warning(f"OSS 上传失败（已忽略，不影响生图） image={image_path}: {e}")

        meta["input_image_oss_urls"] = image_url_list
        meta["oss_uploads"] = oss_uploads

        pil_images = [Image.open(p) for p in image_paths]
        contents.extend(pil_images)

    logger.info(
        "Gemini Flash 生成图片 - model=%s, images=%d, aspect_ratio=%s, timeout_seconds=%s",
        meta["model"],
        len(image_paths),
        aspect_ratio,
        request_timeout_seconds,
    )

    overall_start = time.time()

    # 设置硬超时，避免网络/服务端异常导致一直卡住
    from google.genai import types

    client = genai.Client(
        api_key=key,
        # google-genai 的 HttpOptions.timeout 单位是“毫秒”
        http_options=types.HttpOptions(timeout=request_timeout_seconds * 1000),
    )

    last_err: Exception | None = None

    for attempt in range(1, retry_max_attempts + 1):
        attempt_start = time.time()
        attempt_meta: dict[str, Any] = {
            "attempt": attempt,
            "start_ts": attempt_start,
            "status": "started",
            "error": None,
            "elapsed_seconds": None,
        }

        try:
            if aspect_ratio:
                image_config_kwargs: dict[str, Any] = {"aspect_ratio": aspect_ratio}

                response = client.models.generate_content(
                    model=meta["model"],
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                        image_config=types.ImageConfig(**image_config_kwargs),
                    ),
                )
            else:
                response = client.models.generate_content(
                    model=meta["model"],
                    contents=contents,
                )

            # 每次尝试都重新收集结果（避免上一轮残留）
            text_parts: list[str] = []
            saved_paths: list[str] = []

            # 兼容 parts 同时含 TEXT/IMAGE
            for idx, part in enumerate(getattr(response, "parts", []) or []):
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                    continue

                if getattr(part, "inline_data", None) is not None:
                    try:
                        image = part.as_image()
                    except Exception as e:
                        logger.error(f"Gemini 返回图片 part 解析失败 idx={idx}: {e}")
                        continue

                    file_path = out_dir / f"gemini_flash_{int(time.time())}_{idx}.png"
                    image.save(str(file_path))
                    saved_paths.append(str(file_path))

            # 写入 meta（以最后一次尝试为准）
            meta["text_parts"] = list(text_parts)
            meta["saved_paths"] = list(saved_paths)

            if not saved_paths:
                raise RuntimeError(
                    "Gemini 未返回图片结果（saved_paths 为空）。"
                    "请检查：prompt 是否有效、模型是否可用、API Key 是否正确、以及输入图片是否合规。"
                )

            # 成功
            attempt_meta["status"] = "ok"
            attempt_meta["elapsed_seconds"] = round(time.time() - attempt_start, 3)
            meta["attempts"].append(attempt_meta)
            meta["elapsed_seconds"] = round(time.time() - overall_start, 3)
            return saved_paths, meta

        except Exception as e:
            last_err = e
            attempt_elapsed = round(time.time() - attempt_start, 3)
            attempt_meta["status"] = "failed"
            attempt_meta["elapsed_seconds"] = attempt_elapsed
            attempt_meta["error"] = f"{type(e).__name__}: {e}"
            meta["attempts"].append(attempt_meta)

            # 如果已到最后一次，抛出最后错误
            if attempt >= retry_max_attempts:
                meta["elapsed_seconds"] = round(time.time() - overall_start, 3)
                raise

            # 退避等待
            sleep_s = min(
                retry_max_sleep_seconds,
                retry_initial_sleep_seconds * (retry_backoff_multiplier ** (attempt - 1)),
            )
            logger.warning(
                "Gemini Flash 生图失败，将重试 attempt=%s/%s after %.1fs, err=%s",
                attempt,
                retry_max_attempts,
                sleep_s,
                attempt_meta["error"],
            )
            time.sleep(sleep_s)

    # 理论不可达：为了类型/静态检查
    meta["elapsed_seconds"] = round(time.time() - overall_start, 3)
    if last_err:
        raise last_err
    raise RuntimeError("Gemini Flash 生图失败：未知错误")
