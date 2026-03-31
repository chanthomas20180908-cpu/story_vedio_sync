#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Cloubic banana (OpenAI-compat) image generator.

Purpose:
- Provide an activity-compatible CLI that prints:
  saved_paths:\n<path1>\n<path2>...

Input:
- prompt (positional)
- --image <local_path> (repeatable)

Output:
- One or more image files saved to current working directory
- Prints saved_paths: block for upstream parser

Notes:
- The API response is expected to be Markdown containing images like:
  ![Image 1](data:image/png;base64,....)
- We extract data URLs and decode them to image files.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import re
import time
from pathlib import Path

from openai import OpenAI


_MD_IMG_DATAURL_RE = re.compile(
    r"!\[[^\]]*\]\(\s*(data:image/(png|jpeg|jpg|webp);base64,[A-Za-z0-9+/=\s]+)\s*\)",
    re.I,
)
_DATAURL_RE = re.compile(
    r"(data:image/(png|jpeg|jpg|webp);base64,[A-Za-z0-9+/=\s]+)",
    re.I,
)


def _to_data_url(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"
    blob = Path(path).read_bytes()
    b64 = base64.b64encode(blob).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _extract_data_urls(markdown_text: str) -> list[str]:
    if not markdown_text:
        return []
    urls = [m.group(1) for m in _MD_IMG_DATAURL_RE.finditer(markdown_text)]
    if urls:
        return urls
    return [m.group(1) for m in _DATAURL_RE.finditer(markdown_text)]


def _data_url_to_bytes(data_url: str) -> tuple[bytes, str]:
    # data:image/png;base64,XXXX
    head, b64 = data_url.split(",", 1)
    mime = head.split(";", 1)[0].split(":", 1)[1].strip().lower()
    b64 = re.sub(r"\s+", "", b64)
    return base64.b64decode(b64), mime


def _ext_from_mime(mime: str) -> str:
    return {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
    }.get(mime, "png")


def _save_images_from_markdown(*, md: str, out_dir: Path, prefix: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    data_urls = _extract_data_urls(md)
    if not data_urls:
        raise RuntimeError("未在返回内容中找到 data:image/...;base64 图片（message.content 可能非预期格式）")

    saved: list[Path] = []
    for idx, u in enumerate(data_urls, 1):
        blob, mime = _data_url_to_bytes(u)
        ext = _ext_from_mime(mime)
        p = (out_dir / f"{prefix}_{int(time.time())}_{idx:02d}.{ext}").resolve()
        p.write_bytes(blob)
        saved.append(p)
    return saved


def main() -> int:
    ap = argparse.ArgumentParser(description="Cloubic banana (OpenAI-compat) image generator")
    ap.add_argument("prompt", help="文本提示词")
    ap.add_argument(
        "--image",
        dest="images",
        action="append",
        default=[],
        required=True,
        help="本地参考图路径；可重复传参：--image a.png --image b.jpg",
    )
    ap.add_argument(
        "--model",
        default="gemini-2.5-flash-image",
        help="banana 生图模型名（默认 gemini-2.5-flash-image）",
    )
    ap.add_argument(
        "--base_url",
        default="https://api.cloubic.com/v1",
        help="Cloubic OpenAI 兼容 base_url（默认 https://api.cloubic.com/v1）",
    )

    args = ap.parse_args()

    api_key = os.getenv("CLOUBIC_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 CLOUBIC_API_KEY")

    for p in args.images:
        if not Path(p).expanduser().resolve().exists():
            raise FileNotFoundError(f"参考图不存在: {p}")

    client = OpenAI(base_url=str(args.base_url), api_key=api_key)

    content_parts = []
    for p in args.images:
        content_parts.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
    content_parts.append({"type": "text", "text": str(args.prompt)})

    resp = client.chat.completions.create(
        model=str(args.model),
        messages=[{"role": "user", "content": content_parts}],
    )

    md = (resp.choices[0].message.content or "").strip()
    saved = _save_images_from_markdown(md=md, out_dir=Path.cwd(), prefix="cloubic_banana")

    print("saved_paths:")
    for p in saved:
        print(str(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
