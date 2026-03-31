"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 口播稿/文本
Output: 生图提示词（JSON/结构化 prompt 串；一次模型调用输出全部）
Pos: 工作流 - 生成图提示词（taskgroup）

说明（刻意做最简单）：
- 外部传入 system_prompt / user_prompt_template（不写死在函数内部）
- 一次模型调用，要求模型输出 JSON（允许 ```json 代码块包裹）
- 兼容输出形态：
  - {"prompts": ["...", ...]}
  - ["...", ...]
  - [{...}, {...}]  -> 每个 dict 会被 json.dumps 成一个 prompt 字符串（给下游直接用）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from component.chat.chat import chat_with_model


@dataclass
class ImagePromptsResult:
    prompts: list[str]
    raw_response: str


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n([\s\S]*?)\n```\s*$", re.IGNORECASE)


def _strip_json_fence(s: str) -> str:
    s2 = (s or "").strip()
    m = _CODE_FENCE_RE.match(s2)
    if m:
        return (m.group(1) or "").strip()
    return s2


def _normalize_prompts(data: Any) -> list[str]:
    # dict: {prompts: [...]}
    if isinstance(data, dict) and isinstance(data.get("prompts"), list):
        data = data["prompts"]

    # list[str]
    if isinstance(data, list) and all(isinstance(x, str) for x in data):
        return [x.strip() for x in data if x and x.strip()]

    # list[dict] -> list[str] (json-serialized)
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        out: list[str] = []
        for obj in data:
            out.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        return out

    raise RuntimeError(
        "JSON 结构不符合预期：需要 {prompts:[str]} 或 [str] 或 [dict]"
    )


def image_prompts_sync_001(
    text: str,
    *,
    system_prompt: str,
    user_prompt_template: str,
    api_key: Optional[str] = None,
    model_type: str = "gemini",
    model: str = "gemini-3-flash-preview",
    thinking_level: Optional[str] = None,
    num_images: int = 8,
) -> ImagePromptsResult:
    """一次模型调用生成全部生图 prompts。"""

    if not system_prompt.strip():
        raise ValueError("system_prompt 不能为空")
    if not user_prompt_template.strip():
        raise ValueError("user_prompt_template 不能为空")

    user_prompt = user_prompt_template.format(text=text, num_images=num_images)

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

    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        raise RuntimeError(f"模型输出不是合法 JSON：{e}\nraw={raw[:800]}")

    prompts = _normalize_prompts(data)
    if not prompts:
        raise RuntimeError("解析得到的 prompts 为空")

    return ImagePromptsResult(prompts=prompts, raw_response=raw)


def write_image_prompts_json(
    out_path: Path,
    *,
    prompts: list[str],
    meta: Optional[dict[str, Any]] = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"prompts": prompts}
    if meta:
        payload["meta"] = meta
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="taskgroup: 一次调用生成全部生图提示词(JSON)")
    ap.add_argument("--input", required=True, help="输入 txt/md 文件路径")
    ap.add_argument("--output", required=True, help="输出 JSON 路径")
    ap.add_argument("--num_images", type=int, default=8, help="生成几条 prompt")
    ap.add_argument("--model_type", default="gemini")
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--system_prompt", required=True)
    ap.add_argument("--user_prompt_template", required=True)
    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("输入文件为空")

    res = image_prompts_sync_001(
        text,
        system_prompt=args.system_prompt,
        user_prompt_template=args.user_prompt_template,
        model_type=args.model_type,
        model=args.model,
        num_images=int(args.num_images),
    )

    write_image_prompts_json(Path(args.output), prompts=res.prompts)
    print(f"OK: prompts={len(res.prompts)} -> {args.output}")
