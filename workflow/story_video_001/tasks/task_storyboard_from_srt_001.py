"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: SRT 字幕文件
Output: storyboard（按字幕边界聚合的场景列表，可序列化为 JSON）
Pos: 工作流 - 基于字幕时间轴生成分镜（taskgroup，可复用）

设计目标（越简单越好）：
- 场景切分一定发生在“字幕条目之间”，不在单条字幕内部换图
- 通过 target/min/max 时长窗口控制“长镜头”（例如 15-22 秒一张图）
- 允许后续扩展 anchor / prompt_override / locked 等字段（第一版仅保留字段，不做复杂交互）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from util.util_file import parse_srt_into_list


@dataclass
class StoryboardScene:
    scene_id: int
    start_s: float
    end_s: float
    text: str

    # extension points (optional)
    notes: str = ""
    locked: bool = False
    prompt: str = ""
    prompt_override: str = ""
    image_path: str = ""
    image_override: str = ""


def _sec_to_timestamp(s: float) -> str:
    if s < 0:
        s = 0.0
    ms = int(round((s - int(s)) * 1000))
    total = int(s)
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"


_SENTENCE_END_RE = re.compile(
    r"(?:\.{3,}|…{1,}|[。！？!?])\s*[”’」』）》】\]\)]*\s*$"
)


def _is_sentence_boundary(text: str) -> bool:
    """Very lightweight 'semantic' boundary check.

    保守策略：只把明显句尾当作可切分点，避免半句断开。
    """

    t = (text or "").strip()
    if not t:
        return False

    # Normalize common ellipsis forms
    t = t.replace("……", "…")

    # If ends with comma-like punctuation, treat as not-a-boundary
    if t.endswith(("，", ",", "、", "：", ":", "；", ";")):
        return False

    return bool(_SENTENCE_END_RE.search(t))


def build_storyboard_from_srt_001(
    srt_path: str | Path,
    *,
    target_sec: float = 15.0,
    min_sec: float = 10.0,
    max_sec: float = 22.0,
    gap_sec: float = 0.8,
) -> list[StoryboardScene]:
    """将 SRT cues 聚合为较长的 scene（严格字幕边界切割）。

    Args:
        srt_path: srt 路径
        target_sec: 目标时长（达到后倾向切分）
        min_sec: 最短时长（未达到前尽量不切）
        max_sec: 最长时长（超过必切）
        gap_sec: cue 间隙大于该值，且已 >= min_sec，则优先切分

    Returns:
        scenes: 1-based scene list
    """

    srt_path = Path(srt_path).expanduser().resolve()
    cues = parse_srt_into_list(srt_path)
    # cues: list[(start_s, end_s, text)]
    cues = [(float(a), float(b), (t or "").strip()) for a, b, t in cues if (t or "").strip()]
    if not cues:
        return []

    scenes: list[StoryboardScene] = []

    scene_id = 0
    cur_start = cues[0][0]
    cur_end = cues[0][1]
    cur_texts: list[str] = [cues[0][2]]

    def flush_scene(*, end_s: Optional[float] = None) -> None:
        nonlocal scene_id, cur_start, cur_end, cur_texts
        if not cur_texts:
            return
        scene_id += 1
        scenes.append(
            StoryboardScene(
                scene_id=scene_id,
                start_s=cur_start,
                end_s=float(cur_end if end_s is None else end_s),
                text="\n".join([x for x in cur_texts if x]).strip(),
            )
        )

    for i in range(1, len(cues)):
        start_s, end_s, text = cues[i]
        prev_end = cur_end

        # 先把 cue 并入当前 scene（因为不允许在 cue 内切）
        cur_end = max(cur_end, end_s)
        cur_texts.append(text)

        dur = cur_end - cur_start
        gap = start_s - prev_end

        # 切分判定：只在 cue 之间切（当前 cue 已被并入；切分意味着从下一个 cue 开始新 scene）
        hard_cut = dur >= max_sec

        soft_cut = False
        if dur >= target_sec and dur >= min_sec:
            soft_cut = True
        elif gap >= gap_sec and dur >= min_sec:
            soft_cut = True

        # 保守语义：软切分必须发生在句尾，避免半句断开。
        is_boundary = _is_sentence_boundary(text)
        should_cut = hard_cut or (soft_cut and is_boundary)

        if should_cut and i < len(cues) - 1:
            # 关键：场景切换时间点对齐到“下一句开始”（下一条 cue 的 start）
            nxt_start = float(cues[i + 1][0])
            flush_scene(end_s=nxt_start)
            cur_start = nxt_start
            cur_end = nxt_start
            cur_texts = []

    # flush last
    flush_scene()

    # 修正：如果最后一个 scene 为空或过短导致 0 duration，至少保证 end >= start
    for sc in scenes:
        if sc.end_s < sc.start_s:
            sc.end_s = sc.start_s

    return scenes


def storyboard_to_dict(
    scenes: list[StoryboardScene],
    *,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "meta": meta or {},
        "scenes": [asdict(s) for s in scenes],
    }
    # add readable timestamps
    for s in payload["scenes"]:
        s["start_ts"] = _sec_to_timestamp(float(s["start_s"]))
        s["end_ts"] = _sec_to_timestamp(float(s["end_s"]))
        s["duration_s"] = round(float(s["end_s"]) - float(s["start_s"]), 3)
    return payload


def write_storyboard_json(out_path: str | Path, payload: dict[str, Any]) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
