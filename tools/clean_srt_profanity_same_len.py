#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Clean profanity in .srt subtitle files with fixed-word replacement.

Design goals:
- Only modify subtitle text lines (do not touch index lines, timecode lines, or blank lines)
- Replace matched profanities with a fixed safe word
- Recursive scan under --root
- Default is dry-run unless --apply is specified (safer)
- When applying, write a NEW file named: <stem>_clean_<YYYYMMDD_HHMMSS>.srt (do not overwrite original)
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

SAFE_WORD = "可爱"  # fixed replacement word


def is_index_line(line: str) -> bool:
    t = line.strip()
    return t.isdigit()


def is_timecode_line(line: str) -> bool:
    return "-->" in line


def build_phrase_pattern() -> re.Pattern:
    # Expanded list: keep phrases explicit to avoid false positives like 草丛/海草
    phrases = [
        # strong profanity / insults
        "我操你祖宗的",
        "我操你妈",
        "操你妈",
        "草你妈",
        "艹你妈",
        "去你妈的",
        "滚你妈",
        "你妈的",
        "你他妈的",
        "他妈的",
        "她妈的",
        "这他妈",
        "真他娘的",
        "他娘的",
        "操他娘的",
        "操他妈的",
        "妈的",
        "尼玛",
        "妈蛋",
        "卧槽",
        "我操",
        "我擦",
        "艹",
        # insults
        "狗东西",
        "王八蛋",
        "混蛋",
        "垃圾",
        "傻逼",
        "傻B",
        "煞笔",
        "SB",
        "sb",
        "贱人",
        "婊子",
        # explicit body-part profanities (common in subtitles)
        "鸡巴",
        "鸡儿",
        "几把",
        "屌",
        # mild / colloquial swears
        "奶奶的",
    ]

    # sort long->short, de-dup
    uniq = sorted(set(phrases), key=len, reverse=True)
    return re.compile("|".join(re.escape(x) for x in uniq))


def build_single_char_pattern() -> re.Pattern:
    # Single-character profanity is tricky; only match when surrounded by punctuation/space or line boundaries.
    # Example matches: "操！" "操，" "…操" "操…"
    # Non-matches: words where '操' is inside other text without separators (rare in Chinese, but safer).
    punct = r"[\s\t\r\n\"\'\“\”\‘\’\(\)\[\]{}<>《》【】,，。.!！?？:：;；…—-]"
    return re.compile(rf"(?:(?<=^{punct})|^|(?<={punct}))操(?:(?={punct})|$)")


def clean_srt_text(text: str, phrase_pat: re.Pattern, single_pat: re.Pattern) -> tuple[str, int]:
    repls = 0

    def repl(m: re.Match) -> str:
        nonlocal repls
        repls += 1
        return SAFE_WORD

    out_lines = []
    for line in text.splitlines(keepends=True):
        if is_index_line(line) or is_timecode_line(line) or line.strip() == "":
            out_lines.append(line)
            continue

        # phrases first, then single char (so "我操" won't get split)
        newline = phrase_pat.sub(repl, line)
        newline = single_pat.sub(repl, newline)
        out_lines.append(newline)

    return "".join(out_lines), repls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Root directory to scan recursively for .srt")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write NEW cleaned files (default is dry-run: no writes)",
    )
    args = ap.parse_args()

    root = Path(args.root)
    phrase_pat = build_phrase_pattern()
    single_pat = build_single_char_pattern()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    total_files = 0
    changed_files = 0
    total_repls = 0

    for p in sorted(root.rglob("*.srt")):
        total_files += 1
        old = p.read_text(encoding="utf-8")
        new, n = clean_srt_text(old, phrase_pat, single_pat)

        if n > 0:
            changed_files += 1
            total_repls += n
            out_path = p.with_name(f"{p.stem}_clean_{ts}{p.suffix}")
            print(f"CHANGE {p}  repls={n}  ->  {out_path}")
            if args.apply:
                out_path.write_text(new, encoding="utf-8")
        else:
            print(f"SKIP   {p}")

    print("----")
    print(f"FILES={total_files} CHANGED={changed_files} REPLS={total_repls} APPLY={args.apply} TS={ts}")


if __name__ == "__main__":
    main()
