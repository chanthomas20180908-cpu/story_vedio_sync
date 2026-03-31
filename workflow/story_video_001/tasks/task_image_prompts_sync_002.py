"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: storyboard scenes（每个 scene 一条：start/end/text），以及外部传入的 system_prompt/user_prompt_template
Output: 生图提示词（每个 scene 对应 1 条；批量调用模型；并用“提示词模板文件”中的 base 结构补全缺失字段）
Pos: 工作流 - 生成图提示词（taskgroup 002，不修改 001）

设计目标（保持最简单）：
- 分批生成，避免一次输出太长导致后半段质量退化
- 不改变模板：system_prompt 默认仍用 KESULU_IMAGE_PROMPT_SYNC_PROMPT_001
- 允许模型输出不完整（现实会发生），程序用 base 模板补齐字段，确保“no text”等约束始终存在

约定：
- base 模板与默认负面词/禁令，必须从 data/test_prompt_script.py 读取（不要在逻辑代码里写死）
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, TypeVar

from dotenv import load_dotenv

from component.chat.chat import chat_with_model
from data import test_prompt_script

# 复用 001 的输出规范与解析逻辑（不修改 001）
from workflow.taskgroup.taskgroup_image_prompts_sync_001 import (  # noqa: F401
    ImagePromptsResult,
    _normalize_prompts,
    _strip_json_fence,
)


T = TypeVar("T")


def _chunk_list(xs: list[T], batch_size: int) -> list[list[T]]:
    if batch_size <= 0:
        raise ValueError("batch_size 必须 > 0")
    return [xs[i : i + batch_size] for i in range(0, len(xs), batch_size)]


def _build_scene_prompt_request(scenes: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for sc in scenes:
        sid = int(sc["scene_id"])
        parts.append(
            f"scene_id={sid}\n"
            f"start={sc.get('start_ts','')} end={sc.get('end_ts','')}\n"
            f"text=\n{sc.get('text','')}\n"
            "---"
        )
    return "\n".join(parts)


def _load_base_prompt(*, base_prompt: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """加载 base 提示词结构。

    - 若调用方传入 base_prompt，则使用它（适用于不同 IP 的 schema）。
    - 否则默认使用 KESULU_IMAGE_PROMPT_BASE_001（保持向后兼容）。
    """

    base = base_prompt if isinstance(base_prompt, dict) else getattr(test_prompt_script, "KESULU_IMAGE_PROMPT_BASE_001", None)
    if not isinstance(base, dict):
        raise RuntimeError(
            "缺少 base 提示词结构：请在 data/test_prompt_script.py 中定义 KESULU_IMAGE_PROMPT_BASE_001 (dict)，"
            "或在调用 image_prompts_sync_002 时传入 base_prompt"
        )
    # defensive copy
    return json.loads(json.dumps(base, ensure_ascii=False))


def _render_json_one_liner(obj: dict[str, Any]) -> str:
    """把 dict 渲染成单行 JSON（用于两段式拼接的固定段）。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def image_prompts_sync_002(
    scenes: list[dict[str, Any]],
    *,
    system_prompt: str,
    user_prompt_template: str,
    base_prompt: Optional[dict[str, Any]] = None,
    api_key: Optional[str] = None,
    model_type: str = "gemini",
    model: str = "gemini-3-flash-preview",
    thinking_level: Optional[str] = None,
    batch_size: int = 8,
) -> ImagePromptsResult:
    """分批生成 prompts，并用“固定 JSON(base) + 动态 JSON(模型输出)”两段式直接拼接。

    说明：
    - base_prompt 由调用方传入（cabian/kesulu 各自 schema）。
    - 本函数不再做 dict 级补齐/合并；只做字符串拼接。
    """

    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes 不能为空")
    if not system_prompt.strip():
        raise ValueError("system_prompt 不能为空")
    if not user_prompt_template.strip():
        raise ValueError("user_prompt_template 不能为空")

    # api_key: follow model_type convention
    # - gemini: GEMINI_API_KEY
    # - gemini_cloubic: CLOUBIC_API_KEY
    if api_key is None:
        # keep project convention: try env/default.env first
        try:
            load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../env/default.env"))
        except Exception:
            pass
        if str(model_type).strip() == "gemini_cloubic":
            api_key = os.getenv("CLOUBIC_API_KEY")
        else:
            api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        key_name = "CLOUBIC_API_KEY" if str(model_type).strip() == "gemini_cloubic" else "GEMINI_API_KEY"
        raise RuntimeError(f"缺少 API Key：请设置环境变量 {key_name} 或显式传 api_key")

    base = _load_base_prompt(base_prompt=base_prompt)

    all_prompts: list[str] = []
    raw_parts: list[str] = []

    for batch in _chunk_list(scenes, batch_size=batch_size):
        scene_text = _build_scene_prompt_request(batch)
        user_prompt = user_prompt_template.format(text=scene_text, num_images=len(batch))

        raw = chat_with_model(
            api_key=api_key,
            model_type=model_type,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            thinking_level=thinking_level,
        )
        if not raw:
            raise RuntimeError("模型调用失败：未返回内容")

        raw_parts.append(raw)
        cleaned = _strip_json_fence(raw)
        try:
            data = json.loads(cleaned)
        except Exception as e:
            raise RuntimeError(f"模型输出不是合法 JSON：{e}\nraw={raw[:800]}")

        prompts = _normalize_prompts(data)
        if len(prompts) != len(batch):
            raise RuntimeError(
                f"prompts 数量不匹配：got={len(prompts)} expected={len(batch)} (batch_size={len(batch)})"
            )

        # post-process: JSON 两段式拼接（固定 base + 动态输出）
        fixed = _render_json_one_liner(base)
        for p in prompts:
            dynamic = (p or "").strip()
            if not dynamic:
                dynamic = "{}"
            all_prompts.append(f"{fixed}\n{dynamic}")

    return ImagePromptsResult(prompts=all_prompts, raw_response="\n\n---BATCH---\n\n".join(raw_parts))
