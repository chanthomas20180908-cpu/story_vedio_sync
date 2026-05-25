#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Split a novel markdown file into chapter files and (optionally) LLM-guided segments.

Stage 1 (fixed): split by chapter heading like "第X回 ...".
Stage 2 (optional): within each chapter, let an LLM decide finer segment boundaries
(maximize number of segments while keeping each segment a complete mini-story), and
persist a structured JSON plan for downstream spoken-script generation.

Notes:
- The source may contain HTML tags (e.g. <span ...>) around headings; we strip tags
  for matching but keep original lines in outputs.
- Default is dry-run (no writes). Use --apply to write outputs.
- Never modifies the input file.

Outputs (when --apply):
- Timestamped output dir by default: <input_dir>/03_split_md_<YYYYMMDD_HHMMSS>/
- Chapter files: 001_第一回....md, ...
- If --stage=chapter+llm:
  - Per-chapter JSON plan: 001_第一回....__split_plan.json
  - Per-chapter segments: 001_第一回....__seg001.md, __seg002.md, ...
  - Aggregated JSON: split_all.json
  - split_report.txt

Example:
  python3 tools/split_md_chapters.py --input "/path/to/book.md" --apply
  python3 tools/split_md_chapters.py --input "/path/to/book.md" --stage chapter+llm --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Allow running as: python3 tools/split_md_chapters.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TAG_RE = re.compile(r"<[^>]+>")
CHAPTER_RE = re.compile(
    r"^\s*(?:#+\s*)?第([一二三四五六七八九十百千0-9]+)回(?:\s+|$)(.*)$"
)


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s)


def normalize_spaces(s: str) -> str:
    # normalize common whitespace (including full-width ideographic space)
    return s.replace("\u3000", " ")


def is_chapter_heading_line(line: str) -> Optional[str]:
    """Return canonical chapter title if the line is a chapter heading, else None."""

    raw = normalize_spaces(line)
    plain = strip_tags(raw).strip()

    if not CHAPTER_RE.match(plain):
        return None

    # Keep heading text without markdown heading markers, trim excessive spaces.
    plain = re.sub(r"^\s*#+\s*", "", plain)
    return re.sub(r"\s+", " ", plain)


def safe_filename(s: str, max_len: int = 100) -> str:
    """Make a filesystem-friendly filename fragment."""

    s = s.strip()
    s = s.replace("/", "_").replace("\\", "_")
    s = s.replace(":", "_").replace("*", "_").replace("?", "_")
    s = s.replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
    s = re.sub(r"\s+", " ", s)
    return s[:max_len].rstrip() if len(s) > max_len else s


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def parse_json_from_model(s: str) -> Dict[str, Any]:
    """Parse JSON from model output. Tries strict JSON first, then extracts fenced block."""

    s = s.strip()
    try:
        v = json.loads(s)
        if isinstance(v, dict):
            return v
        raise ValueError("Model JSON is not an object")
    except Exception:
        pass

    # Try to extract ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    # Try to extract first {...} block (best-effort)
    m2 = re.search(r"(\{.*\})", s, flags=re.DOTALL)
    if m2:
        return json.loads(m2.group(1))

    raise ValueError("Could not parse JSON from model output")


@dataclass
class Chapter:
    title: str
    start_line_no: int  # 1-based
    lines: List[str]


@dataclass
class Unit:
    unit_id: int  # 1-based within chapter
    text: str

    @property
    def char_len(self) -> int:
        return len(self.text)


def split_into_chapters(all_lines: List[str]) -> Tuple[List[str], List[Chapter]]:
    prelude: List[str] = []
    chapters: List[Chapter] = []
    current: Optional[Chapter] = None

    for idx, line in enumerate(all_lines, start=1):
        title = is_chapter_heading_line(line)
        if title is not None:
            if current is not None:
                chapters.append(current)
            current = Chapter(title=title, start_line_no=idx, lines=[line])
            continue

        if current is None:
            prelude.append(line)
        else:
            current.lines.append(line)

    if current is not None:
        chapters.append(current)

    return prelude, chapters


def default_out_dir_for(input_path: Path, ts: str) -> Path:
    # Timestamped to avoid overwriting directory-level outputs.
    return input_path.parent / f"03_split_md_{ts}"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def split_chapter_into_units(ch: Chapter) -> List[Unit]:
    """Split a chapter into paragraph units (blank-line separated)."""

    content = "".join(ch.lines)
    # Normalize newlines
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Preserve paragraph text with trailing newline to keep formatting stable
    raw_parts = re.split(r"\n\s*\n+", content)
    units: List[Unit] = []
    uid = 0
    for part in raw_parts:
        p = part.strip("\n")
        if p.strip() == "":
            continue
        uid += 1
        # Ensure each unit ends with a newline for clean concatenation
        units.append(Unit(unit_id=uid, text=p + "\n"))
    return units


def sample_text_for_meta(full_text: str, head_chars: int = 1600, tail_chars: int = 1600) -> str:
    """Cheap sampling: head + tail, to let LLM see setup and resolution."""

    t = full_text.strip()
    if len(t) <= head_chars + tail_chars + 200:
        return t
    head = t[:head_chars]
    tail = t[-tail_chars:]
    return head + "\n\n[...中间略... ]\n\n" + tail


def build_prev_next_intro(prev_meta: Optional[Dict[str, Any]], next_meta: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    prev_intro = ""
    next_intro = ""
    if prev_meta:
        parts = []
        if prev_meta.get("chapter_title"):
            parts.append(f"上一章《{prev_meta.get('chapter_title')}》")
        if prev_meta.get("chapter_summary"):
            parts.append(str(prev_meta.get("chapter_summary")).strip())
        if prev_meta.get("chapter_end_state"):
            parts.append(f"结尾：{str(prev_meta.get('chapter_end_state')).strip()}")
        prev_intro = "；".join(p for p in parts if p)

    if next_meta:
        parts = []
        if next_meta.get("chapter_title"):
            parts.append(f"下一章《{next_meta.get('chapter_title')}》")
        if next_meta.get("next_chapter_teaser"):
            parts.append(f"看点：{str(next_meta.get('next_chapter_teaser')).strip()}")
        elif next_meta.get("chapter_hook"):
            parts.append(f"看点：{str(next_meta.get('chapter_hook')).strip()}")
        next_intro = "；".join(p for p in parts if p)

    return prev_intro, next_intro


def llm_init(env_file: Path) -> Tuple[Any, Any]:
    """Init logging + dotenv + return (logger, chat_with_model)."""

    from dotenv import load_dotenv
    from config.logging_config import setup_logging, get_logger
    from component.chat.chat import chat_with_model

    setup_logging()
    logger = get_logger(__name__)

    if env_file.exists():
        load_dotenv(dotenv_path=str(env_file))
    else:
        logger.warning(f"env file not found: {env_file}")

    return logger, chat_with_model


def llm_call_json(
    chat_with_model_fn,
    api_key: str,
    model_type: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    res = chat_with_model_fn(
        api_key=api_key,
        model_type=model_type,
        model=model,
        messages=messages,
    )
    if not res:
        raise ValueError("LLM returned empty response")
    return parse_json_from_model(res)


def build_chapter_meta_prompt(chapter_title: str, sampled_text: str) -> Tuple[str, str]:
    system_prompt = (
        "你是一个中文长文本拆分与剧情梳理助手。\n"
        "你的输出必须是严格 JSON（不要出现解释文字，不要代码块）。\n"
        "字段必须齐全，若不确定可用空字符串。"
    )

    user_prompt = (
        "请阅读下面章节文本样本，输出该章节的元信息 JSON。\n"
        "要求：简短、信息密度高、适合用于后续生成口播稿的上下文提示。\n\n"
        "必须输出如下 JSON 结构：\n"
        "{\n"
        "  \"chapter_title\": string,\n"
        "  \"chapter_summary\": string,\n"
        "  \"chapter_hook\": string,\n"
        "  \"chapter_end_state\": string,\n"
        "  \"next_chapter_teaser\": string\n"
        "}\n\n"
        f"章节标题：{chapter_title}\n\n"
        "章节文本样本：\n"
        f"{sampled_text}"
    )
    return system_prompt, user_prompt


def build_split_plan_prompt(
    chapter_title: str,
    prev_intro: str,
    next_intro: str,
    units: List[Unit],
    overlap_units: int,
) -> Tuple[str, str]:
    system_prompt = (
        "你是一个中文小说拆分助手。\n"
        "目标：把一章拆成尽可能多的片段（用于后续口播稿生成），但每个片段必须是一个完整的小故事："
        "有起因/铺垫、有冲突/高潮、有收束或明确悬念，不要把高潮一刀切断。\n"
        "只能在段落边界拆（给你的 unit 边界就是可拆边界）。\n"
        "你的输出必须是严格 JSON（不要出现解释文字，不要代码块）。"
    )

    # Provide compact unit previews to keep token cost down.
    unit_lines = []
    for u in units:
        t = u.text.strip()
        head = t[:60]
        tail = t[-60:] if len(t) > 60 else ""
        preview = head if not tail else (head + " ... " + tail)
        unit_lines.append(f"{u.unit_id}: (len={len(t)}) {preview}")

    user_prompt = (
        "请基于下面给出的段落单元列表 units，规划该章节的拆分边界，输出 segments。\n"
        "拆分原则：\n"
        "1) 尽量多拆：优先把每个‘完整事件/冲突’单独成段；\n"
        "2) 完整性硬约束：每段必须读起来完整（有头有尾，有高潮），宁可段长一点也不要断在关键转折中间；\n"
        "3) 连贯性：相邻段之间允许有少量重复上下文，脚本会自动做 overlap，你只需要选好边界；\n"
        "4) 输出 segments 必须覆盖所有 units，且不重叠、不遗漏，按顺序排列。\n\n"
        "必须输出如下 JSON 结构：\n"
        "{\n"
        "  \"chapter_title\": string,\n"
        "  \"overlap_units\": number,\n"
        "  \"segments\": [\n"
        "    {\n"
        "      \"segment_index\": number,\n"
        "      \"start_unit_id\": number,\n"
        "      \"end_unit_id\": number,\n"
        "      \"why_complete\": string,\n"
        "      \"highlight\": string\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"章节标题：{chapter_title}\n"
        f"上一章简介：{prev_intro}\n"
        f"下一章简介：{next_intro}\n"
        f"overlap_units（仅供参考）：{overlap_units}\n\n"
        "units 列表：\n"
        + "\n".join(unit_lines)
    )

    return system_prompt, user_prompt


def validate_segments(segments: List[Dict[str, Any]], max_unit_id: int) -> None:
    if not segments:
        raise ValueError("segments is empty")

    # sort by segment_index then start
    segs = sorted(segments, key=lambda x: (int(x.get("segment_index", 0)), int(x.get("start_unit_id", 0))))

    expect_start = 1
    for s in segs:
        a = int(s["start_unit_id"])
        b = int(s["end_unit_id"])
        if a != expect_start:
            raise ValueError(f"segments not contiguous: expect start {expect_start}, got {a}")
        if b < a:
            raise ValueError(f"invalid segment range: {a}-{b}")
        expect_start = b + 1

    if expect_start != max_unit_id + 1:
        raise ValueError(f"segments do not cover all units: ended at {expect_start-1}, max={max_unit_id}")


def render_segment_text(units: List[Unit], start_id: int, end_id: int, overlap_units: int) -> Tuple[str, Dict[str, Any]]:
    # 1-based ids
    start_idx = start_id - 1
    end_idx = end_id - 1

    ov_start_idx = max(0, start_idx - overlap_units)

    overlap_text = "".join(u.text for u in units[ov_start_idx:start_idx])
    body_text = "".join(u.text for u in units[start_idx : end_idx + 1])

    meta = {
        "overlap_units": overlap_units,
        "overlap_range": [ov_start_idx + 1, start_idx] if start_idx > ov_start_idx else None,
        "body_range": [start_id, end_id],
    }
    return overlap_text + body_text, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to the source .md file")
    ap.add_argument("--out-dir", default=None, help="Output directory (default: <input_dir>/03_split_md_<ts>)")
    ap.add_argument(
        "--chapter-mode",
        default="auto",
        choices=["auto", "none"],
        help="Chapter detection mode: auto=match headings; none=treat whole doc as a single chapter",
    )
    ap.add_argument("--stage", default="chapter", choices=["chapter", "chapter+llm"], help="Split stage")
    ap.add_argument("--apply", action="store_true", help="Write output files (default is dry-run)")
    ap.add_argument("--keep-empty-prelude", action="store_true", help="Write 000_前置内容.md even if empty")

    # LLM options
    ap.add_argument("--env-file", default=str(PROJECT_ROOT / "env" / "default.env"), help="dotenv env file")
    ap.add_argument("--model-type", default="gemini", help="Model type for chat_with_model")
    ap.add_argument("--model", default="gemini-3-flash-preview", help="Model name")
    ap.add_argument("--api-key-env", default="GEMINI_API_KEY", help="Env var name for API key")
    ap.add_argument("--overlap-units", type=int, default=1, help="How many previous paragraph units to prepend")

    args = ap.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.exists() or not input_path.is_file():
        print(f"ERROR: input must be an existing file: {input_path}", file=sys.stderr)
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else default_out_dir_for(input_path, ts=ts)

    text = input_path.read_text(encoding="utf-8")
    all_lines = text.splitlines(keepends=True)

    if args.chapter_mode == "none":
        prelude = []
        chapters = [Chapter(title="整篇", start_line_no=1, lines=all_lines)]
    else:
        prelude, chapters = split_into_chapters(all_lines)

    if not chapters:
        print("ERROR: no chapters matched. Expected headings like: 第四回 ...", file=sys.stderr)
        print("Hint: try --chapter-mode none for documents without chapter headings.", file=sys.stderr)
        return 3

    outputs: List[Tuple[Path, str]] = []

    prelude_text = "".join(prelude)
    if prelude_text.strip() or args.keep_empty_prelude:
        outputs.append((out_dir / "000_前置内容.md", prelude_text))

    # Always write chapter files (stage 1)
    chapter_paths: List[Path] = []
    for i, ch in enumerate(chapters, start=1):
        name = safe_filename(ch.title)
        p = out_dir / f"{i:03d}_{name}.md"
        chapter_paths.append(p)
        outputs.append((p, "".join(ch.lines)))

    # LLM stage
    split_all: Dict[str, Any] = {
        "version": 1,
        "input": str(input_path),
        "out_dir": str(out_dir),
        "ts": ts,
        "stage": args.stage,
        "chapters": [],
    }

    chapter_metas: List[Optional[Dict[str, Any]]] = [None] * len(chapters)

    if args.stage == "chapter+llm":
        env_file = Path(args.env_file).expanduser()
        logger, chat_with_model_fn = llm_init(env_file)

        api_key = os.getenv(args.api_key_env, "")
        if not api_key:
            raise ValueError(f"{args.api_key_env} not configured (dotenv: {env_file})")

        # 1) Chapter metas
        for i, ch in enumerate(chapters, start=1):
            full_text = "".join(ch.lines)
            sampled = sample_text_for_meta(full_text)
            sys_p, user_p = build_chapter_meta_prompt(ch.title, sampled)
            meta = llm_call_json(
                chat_with_model_fn,
                api_key=api_key,
                model_type=args.model_type,
                model=args.model,
                system_prompt=sys_p,
                user_prompt=user_p,
            )
            # ensure title is present
            meta.setdefault("chapter_title", ch.title)
            chapter_metas[i - 1] = meta
            logger.info(f"chapter meta ok: {i:03d} {ch.title}")

        # 2) Split plans + segment files
        for i, ch in enumerate(chapters, start=1):
            units = split_chapter_into_units(ch)
            if not units:
                continue

            prev_meta = chapter_metas[i - 2] if i - 2 >= 0 else None
            next_meta = chapter_metas[i] if i < len(chapters) else None
            prev_intro, next_intro = build_prev_next_intro(prev_meta, next_meta)

            sys_p, user_p = build_split_plan_prompt(
                chapter_title=ch.title,
                prev_intro=prev_intro,
                next_intro=next_intro,
                units=units,
                overlap_units=args.overlap_units,
            )
            plan = llm_call_json(
                chat_with_model_fn,
                api_key=api_key,
                model_type=args.model_type,
                model=args.model,
                system_prompt=sys_p,
                user_prompt=user_p,
            )

            plan.setdefault("chapter_title", ch.title)
            plan["overlap_units"] = args.overlap_units

            segments = plan.get("segments", [])
            if not isinstance(segments, list):
                raise ValueError("plan.segments must be a list")
            validate_segments(segments, max_unit_id=units[-1].unit_id)

            # enrich plan with chapter meta + prev/next intros + unit stats
            meta = chapter_metas[i - 1] or {"chapter_title": ch.title}
            plan_enriched: Dict[str, Any] = {
                "version": 1,
                "chapter_index": i,
                "chapter_title": ch.title,
                "chapter_meta": meta,
                "prev_chapter_intro": prev_intro,
                "next_chapter_intro": next_intro,
                "overlap_units": args.overlap_units,
                "units": [
                    {
                        "unit_id": u.unit_id,
                        "char_len": len(u.text.strip()),
                        "preview": (u.text.strip()[:60] + ("..." if len(u.text.strip()) > 60 else "")),
                    }
                    for u in units
                ],
                "segments": segments,
            }

            ch_name = safe_filename(ch.title)
            plan_path = out_dir / f"{i:03d}_{ch_name}__split_plan.json"
            outputs.append((plan_path, json_dumps(plan_enriched)))

            # segment md files
            for s in sorted(segments, key=lambda x: int(x.get("segment_index", 0))):
                seg_idx = int(s["segment_index"])
                a = int(s["start_unit_id"])
                b = int(s["end_unit_id"])
                seg_text, seg_meta = render_segment_text(units, a, b, overlap_units=args.overlap_units)

                # Do NOT prepend any header (even comments) to avoid influencing downstream script generation.
                seg_path = out_dir / f"{i:03d}_{ch_name}__seg{seg_idx:03d}.md"
                outputs.append((seg_path, seg_text))

            split_all["chapters"].append(
                {
                    "chapter_index": i,
                    "chapter_title": ch.title,
                    "chapter_meta": meta,
                    "prev_chapter_intro": prev_intro,
                    "next_chapter_intro": next_intro,
                    "split_plan_file": plan_path.name,
                    "segment_count": len(segments),
                }
            )

        outputs.append((out_dir / "split_all.json", json_dumps(split_all)))

    # Report
    report_lines: List[str] = []
    report_lines.append(f"INPUT: {input_path}\n")
    report_lines.append(f"OUT_DIR: {out_dir}\n")
    report_lines.append(f"CHAPTER_MODE: {args.chapter_mode}\n")
    report_lines.append(f"STAGE: {args.stage}\n")
    report_lines.append(f"CHAPTERS: {len(chapters)}\n")
    report_lines.append("\n")
    for i, ch in enumerate(chapters, start=1):
        report_lines.append(f"{i:03d}  line {ch.start_line_no}: {ch.title}\n")
    outputs.append((out_dir / "split_report.txt", "".join(report_lines)))

    if not args.apply:
        print("DRY-RUN (no files written). Use --apply to write outputs.")
        print(f"Would write to: {out_dir}")
        for p, content in outputs:
            approx_lines = content.count("\n") + (0 if content.endswith("\n") or content == "" else 1)
            print(f"  - {p.name}  (approx lines: {approx_lines})")
        if args.stage == "chapter+llm":
            print("NOTE: In dry-run, LLM calls were executed (plan computed) but files were not written.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for p, content in outputs:
        write_text(p, content)

    print(f"OK. Wrote {len(outputs)} files to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
