#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HappyHorse 图生视频最小测试脚本。

默认配置刻意保守：单条 3 秒、720P、固定 seed，用于控制首次测试成本。
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_FIRST_FRAME = (
    PROJECT_ROOT
    / "data/Data_results/picture_results/video_episode_002_womankingdom_cthulhu_v1"
    / "keyframes/shot_01_bajie_shadow_escape.png"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/Data_results/video_results/happyhorse_womankingdom_test_20260525_001"
)
CREATE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
QUERY_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


DEFAULT_PROMPT = """天书奇谭式中国经典动画，手绘赛璐璐和水墨纸纹质感。夜色女儿国宫门前，猪八戒的黑色影子从地面脱离，像墨水一样贴着石阶快速爬走；镜头低角度缓慢跟随，宫灯轻微摇晃，纸面颗粒稳定，角色不要变形，不要写实化，不要现代3D感。"""


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def image_to_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"first frame not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"

    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def create_task(
    api_key: str,
    first_frame_path: Path,
    prompt: str,
    output_dir: Path,
    resolution: str,
    duration: int,
    watermark: bool,
    seed: int,
) -> str:
    payload = {
        "model": "happyhorse-1.0-i2v",
        "input": {
            "prompt": prompt,
            "media": [
                {
                    "type": "first_frame",
                    "url": image_to_data_url(first_frame_path),
                }
            ],
        },
        "parameters": {
            "resolution": resolution,
            "duration": duration,
            "watermark": watermark,
            "seed": seed,
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    response = requests.post(CREATE_TASK_URL, headers=headers, json=payload, timeout=60)
    result = response.json()
    save_json(output_dir / "create_task_response.json", result)
    response.raise_for_status()

    task_id = result.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"missing task_id in response: {result}")
    return task_id


def query_task(api_key: str, task_id: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(QUERY_TASK_URL.format(task_id=task_id), headers=headers, timeout=60)
    result = response.json()
    response.raise_for_status()
    return result


def poll_task(api_key: str, task_id: str, output_dir: Path, interval: int, max_wait: int) -> dict:
    started = time.time()
    attempt = 0

    while True:
        attempt += 1
        result = query_task(api_key, task_id)
        status = result.get("output", {}).get("task_status", "UNKNOWN")
        save_json(output_dir / f"poll_{attempt:03d}_{status.lower()}.json", result)
        print(f"[poll {attempt}] status={status}")

        if status in {"SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"}:
            save_json(output_dir / "final_task_response.json", result)
            return result

        if time.time() - started > max_wait:
            raise TimeoutError(f"task polling timeout after {max_wait}s: {task_id}")

        time.sleep(interval)


def download_video(video_url: str, output_dir: Path, filename: str) -> Path:
    response = requests.get(video_url, stream=True, timeout=120)
    response.raise_for_status()

    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / filename
    with video_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    return video_path


def infer_filename(video_url: str, fallback: str) -> str:
    name = os.path.basename(urlparse(video_url).path)
    if not name or "." not in name:
        return fallback
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description="HappyHorse 图生视频最小可用测试")
    parser.add_argument("--first-frame", default=str(DEFAULT_FIRST_FRAME), help="首帧图片路径")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="视频提示词")
    parser.add_argument("--resolution", default="720P", choices=["720P", "1080P"], help="分辨率档位")
    parser.add_argument("--duration", type=int, default=3, help="视频时长，3-15 秒")
    parser.add_argument("--seed", type=int, default=20260525, help="随机种子")
    parser.add_argument("--watermark", action="store_true", help="添加 Happy Horse 水印")
    parser.add_argument("--poll-interval", type=int, default=15, help="轮询间隔秒数")
    parser.add_argument("--max-wait", type=int, default=600, help="最大等待秒数")
    parser.add_argument("--create-only", action="store_true", help="只创建任务，不轮询下载")
    args = parser.parse_args()

    if args.duration < 3 or args.duration > 15:
        raise ValueError("--duration must be between 3 and 15")

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is missing in env/default.env")

    first_frame = Path(args.first_frame).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    run_info = {
        "created_at": now_stamp(),
        "model": "happyhorse-1.0-i2v",
        "endpoint": CREATE_TASK_URL,
        "first_frame": str(first_frame),
        "output_dir": str(output_dir),
        "prompt": args.prompt,
        "parameters": {
            "resolution": args.resolution,
            "duration": args.duration,
            "watermark": bool(args.watermark),
            "seed": args.seed,
        },
    }
    save_json(output_dir / "run_config.json", run_info)

    print("creating task...")
    task_id = create_task(
        api_key=api_key,
        first_frame_path=first_frame,
        prompt=args.prompt,
        output_dir=output_dir,
        resolution=args.resolution,
        duration=args.duration,
        watermark=bool(args.watermark),
        seed=args.seed,
    )
    print(f"task_id={task_id}")

    if args.create_only:
        return 0

    final_result = poll_task(
        api_key=api_key,
        task_id=task_id,
        output_dir=output_dir,
        interval=args.poll_interval,
        max_wait=args.max_wait,
    )

    output = final_result.get("output", {})
    if output.get("task_status") != "SUCCEEDED":
        raise RuntimeError(f"task did not succeed: {output}")

    video_url = output.get("video_url")
    if not video_url:
        raise RuntimeError(f"missing video_url in final result: {final_result}")

    filename = infer_filename(video_url, f"happyhorse_i2v_{task_id}.mp4")
    video_path = download_video(video_url, output_dir, filename)
    print(f"video_path={video_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
