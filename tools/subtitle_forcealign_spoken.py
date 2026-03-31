#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate SRT with spoken text as the ONLY truth.

Design goal (simple + stable):
- Timing comes from ASR word timestamps (faster-whisper).
- Subtitle text comes strictly from the provided spoken transcript.
- Do ONE pass to produce final SRT. No post split/merge chains.

Approach:
1) ASR audio -> word timestamps (we ignore ASR text for output)
2) Build an ASR "character timeline" by distributing each word's time span to its normalized characters
3) Normalize spoken text (remove whitespace & punctuation) and build norm->raw index mapping
4) Global alignment: SequenceMatcher between ASR norm string and spoken norm string
5) Map spoken norm indices to ASR timeline (anchors). Interpolate missing indices.
6) Build cues by time rules (gap/max_sec/max_chars), cut on preferred punctuation when needed.
7) Output SRT. Text slices are taken from spoken raw string to preserve punctuation naturally.

This avoids:
- drifting (only one time source)
- typos (spoken is used for text)
- weird gaps from repeated cutting/merging
"""

from __future__ import annotations

import argparse
import difflib
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


WS_RE = re.compile(r"\s+")


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _audio_duration_ms(wav_path: Path) -> int:
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate <= 0:
            return 0
        return int(frames / rate * 1000)


def _strip_ws(s: str) -> str:
    return WS_RE.sub("", s or "")


# punctuation set for normalization (kept minimal but practical)
PUNC_SET = set(
    "，。！？；：、,.!?;:"
    "“”‘’'\""
    "（）()【】[]《》<>〈〉"
    "—-…·`~"
)


def _is_punc(ch: str) -> bool:
    return ch in PUNC_SET


def _norm_chars_and_map(raw: str) -> tuple[str, list[int]]:
    """Normalize: remove whitespace & punctuation. Return (norm_string, norm2raw_index)."""
    raw = raw or ""
    norm_chars: list[str] = []
    norm2raw: list[int] = []
    for i, ch in enumerate(raw):
        if ch.isspace():
            continue
        if _is_punc(ch):
            continue
        norm_chars.append(ch)
        norm2raw.append(i)
    return "".join(norm_chars), norm2raw


def _wrap_2lines(text: str, *, max_line: int, max_lines: int) -> str:
    t = _strip_ws(text)
    if not t:
        return ""
    lines: list[str] = []
    while t and len(lines) < max_lines:
        lines.append(t[:max_line])
        t = t[max_line:]
    if t and lines:
        lines[-1] = (lines[-1] + t)[:max_line]
    return "\n".join(lines)


def _format_srt_time(ms: int) -> str:
    if ms < 0:
        ms = 0
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


@dataclass
class AsrChar:
    ch: str
    start_ms: int
    end_ms: int


def _build_asr_char_timeline(*, words: list[tuple[float, float, str]]) -> list[AsrChar]:
    """Distribute each word's time span equally to its normalized characters."""
    out: list[AsrChar] = []
    for start_s, end_s, wtxt in words:
        # normalize word text: remove whitespace & punctuation
        wtxt = _strip_ws(wtxt)
        chars = [c for c in wtxt if c and (not _is_punc(c))]
        if not chars:
            continue
        s_ms = int(round(start_s * 1000))
        e_ms = int(round(end_s * 1000))
        if e_ms <= s_ms:
            e_ms = s_ms + 1
        dur = e_ms - s_ms
        n = len(chars)
        per = max(1, dur // n)
        cur = s_ms
        for i, ch in enumerate(chars):
            nxt = e_ms if i == n - 1 else min(e_ms, cur + per)
            if nxt <= cur:
                nxt = cur + 1
            out.append(AsrChar(ch=ch, start_ms=cur, end_ms=nxt))
            cur = nxt
    return out


def _align_spoken_to_asr(
    *,
    asr_chars: list[AsrChar],
    spoken_norm: str,
) -> tuple[list[Optional[int]], dict]:
    """Return spoken_norm_mid_ms list aligned to ASR by global sequence matching.

    For indices with an aligned ASR char, mid_ms is ASR char midpoint.
    Others remain None (later interpolated).
    """
    asr_norm = "".join(x.ch for x in asr_chars)
    sm = difflib.SequenceMatcher(a=asr_norm, b=spoken_norm)

    mid: list[Optional[int]] = [None] * len(spoken_norm)
    matched = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            continue
        # equal spans map 1:1
        for k in range(i2 - i1):
            ai = i1 + k
            bi = j1 + k
            if 0 <= ai < len(asr_chars) and 0 <= bi < len(mid):
                a = asr_chars[ai]
                mid[bi] = int((a.start_ms + a.end_ms) // 2)
                matched += 1

    coverage = matched / max(1, len(spoken_norm))
    meta = {
        "asr_norm_len": len(asr_norm),
        "spoken_norm_len": len(spoken_norm),
        "matched_chars": matched,
        "coverage": round(coverage, 4),
    }
    return mid, meta


def _interpolate_midpoints(mid: list[Optional[int]]) -> list[int]:
    if not mid:
        return []

    idxs = [i for i, v in enumerate(mid) if v is not None]
    if not idxs:
        # nothing matched; fallback to monotonic 0..len-1
        return list(range(len(mid)))

    # forward fill boundaries
    first_i = idxs[0]
    first_v = int(mid[first_i])
    last_i = idxs[-1]
    last_v = int(mid[last_i])

    out = [0] * len(mid)
    for i in range(0, first_i):
        out[i] = first_v
    for i in range(last_i, len(mid)):
        out[i] = last_v

    # fill known points
    for i in idxs:
        out[i] = int(mid[i])

    # linear interpolate between anchors
    for a, b in zip(idxs, idxs[1:]):
        va = out[a]
        vb = out[b]
        span = b - a
        if span <= 1:
            continue
        for k in range(1, span):
            t = k / span
            out[a + k] = int(round(va + (vb - va) * t))

    # enforce non-decreasing
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def _pick_cut_norm_index(
    *,
    spoken_raw: str,
    norm2raw: list[int],
    start_norm: int,
    end_norm: int,
) -> Optional[int]:
    """Pick a preferred cut point inside [start_norm, end_norm) using punctuation in raw text.

    Returns a norm index to cut at (exclusive end for left part), or None.
    """
    if end_norm - start_norm <= 1:
        return None
    # search backward in the raw slice
    raw_s = norm2raw[start_norm]
    raw_e = norm2raw[end_norm - 1] + 1
    seg = spoken_raw[raw_s:raw_e]

    strong = "。！？；"
    weak = "，、："

    # find last strong, else last weak
    last_pos = -1
    for ch in strong:
        p = seg.rfind(ch)
        last_pos = max(last_pos, p)
    if last_pos < 0:
        for ch in weak:
            p = seg.rfind(ch)
            last_pos = max(last_pos, p)
    if last_pos < 0:
        return None

    # convert raw position -> norm index
    cut_raw = raw_s + last_pos + 1  # include punctuation on left
    # find the first norm index whose raw index >= cut_raw
    for ni in range(start_norm + 1, end_norm):
        if norm2raw[ni] >= cut_raw:
            return ni
    return None


def generate_srt_forcealign_spoken(
    *,
    wav_path: Path,
    spoken_path: Path,
    out_srt: Path,
    model_name: str,
    language: str,
    gap_split_sec: float,
    max_cue_sec: float,
    max_line: int,
    max_lines: int,
    max_chars_per_cue: int,
    min_cue_ms: int,
    coverage_min: float,
) -> dict:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "缺少 faster-whisper 依赖。请在项目 .venv 内安装：pip install faster-whisper"
        ) from e

    spoken_raw = _read_text(spoken_path)
    spoken_display = _strip_ws(spoken_raw)
    spoken_norm, norm2raw = _norm_chars_and_map(spoken_display)
    if not spoken_norm:
        raise ValueError("spoken 文本为空或无法归一化")

    model = WhisperModel(str(model_name), device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(wav_path),
        language=str(language) if language else None,
        vad_filter=True,
        word_timestamps=True,
    )

    words: list[tuple[float, float, str]] = []
    for seg in segments:
        ws = getattr(seg, "words", None) or []
        for w in ws:
            wtxt = (getattr(w, "word", "") or "").strip()
            if not wtxt:
                continue
            words.append((float(w.start), float(w.end), wtxt))
    if not words:
        raise RuntimeError("ASR 未产出 word timestamps")

    asr_chars = _build_asr_char_timeline(words=words)
    if not asr_chars:
        raise RuntimeError("ASR 字符时间轴为空（可能是音频/模型输出异常）")

    mid_opt, align_meta = _align_spoken_to_asr(asr_chars=asr_chars, spoken_norm=spoken_norm)
    if float(align_meta["coverage"]) < float(coverage_min):
        raise RuntimeError(
            f"对齐覆盖率过低：coverage={align_meta['coverage']} < {coverage_min}。"
            "建议改用更大模型/检查音频质量。"
        )

    mid_ms = _interpolate_midpoints(mid_opt)
    audio_ms = _audio_duration_ms(wav_path)
    if audio_ms <= 0:
        audio_ms = max(1, asr_chars[-1].end_ms)

    # Build cues by time rules on spoken_norm indices
    cues: list[tuple[int, int, str]] = []
    i = 0
    prev_end = 0
    gap_ms = int(round(gap_split_sec * 1000))
    max_ms = int(round(max_cue_sec * 1000))

    def norm_range_to_text(a: int, b: int) -> str:
        if b <= a:
            return ""
        rs = norm2raw[a]
        re_ = norm2raw[b - 1] + 1
        return spoken_display[rs:re_]

    while i < len(spoken_norm):
        start_i = i
        start_t = mid_ms[i]
        last_t = start_t
        last_ok = i

        # grow until break
        j = i
        while j < len(spoken_norm):
            t = mid_ms[j]
            # gap break
            if j > start_i and (t - last_t) >= gap_ms:
                break
            # size break
            if (t - start_t) >= max_ms:
                break
            # char count break (approx on raw slice)
            if j > start_i:
                txt = norm_range_to_text(start_i, j + 1)
                if len(_strip_ws(txt)) >= max_chars_per_cue:
                    break
            last_t = t
            last_ok = j
            j += 1

        end_i = last_ok + 1

        # if we broke due to max constraints, try to cut at punctuation inside the range
        if end_i - start_i >= 6:
            cut = _pick_cut_norm_index(
                spoken_raw=spoken_display,
                norm2raw=norm2raw,
                start_norm=start_i,
                end_norm=end_i,
            )
            if cut and cut > start_i + 1:
                end_i = cut

        # compute cue start/end times
        cue_start = int(start_t)
        cue_end = int(mid_ms[end_i - 1])
        if cue_end <= cue_start:
            cue_end = cue_start + 1

        # pad end to make display stable
        cue_end += 120

        # clamp and monotonic
        if cue_start < prev_end:
            cue_start = prev_end
        if cue_end <= cue_start:
            cue_end = cue_start + 1
        if cue_end - cue_start < int(min_cue_ms):
            cue_end = cue_start + int(min_cue_ms)

        if cue_end > audio_ms:
            cue_end = audio_ms
        if cue_start >= audio_ms:
            break

        txt = norm_range_to_text(start_i, end_i)
        cues.append((cue_start, cue_end, _wrap_2lines(txt, max_line=max_line, max_lines=max_lines)))
        prev_end = cue_end
        i = end_i

    # write SRT
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for idx, (s, e, t) in enumerate(cues, 1):
        lines.append(str(idx))
        lines.append(f"{_format_srt_time(s)} --> {_format_srt_time(e)}")
        lines.append(t)
        lines.append("")
    out_srt.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "audio_ms": audio_ms,
        "cues": len(cues),
        "asr_model": str(model_name),
        "asr_lang": getattr(info, "language", None),
        "asr_lang_prob": getattr(info, "language_probability", None),
        "align": align_meta,
        "params": {
            "gap_split_sec": gap_split_sec,
            "max_cue_sec": max_cue_sec,
            "max_line": max_line,
            "max_lines": max_lines,
            "max_chars_per_cue": max_chars_per_cue,
            "min_cue_ms": min_cue_ms,
            "coverage_min": coverage_min,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="subtitle: force-align spoken transcript to audio")
    ap.add_argument("--audio", required=True, help="输入 wav 音频路径")
    ap.add_argument("--spoken", required=True, help="口播稿 txt 路径（唯一文字真值）")
    ap.add_argument("--out_srt", required=True, help="输出 srt 路径")
    ap.add_argument("--model", default="medium", help="faster-whisper 模型名（默认 medium）")
    ap.add_argument("--language", default="zh", help="语言（默认 zh）")
    ap.add_argument("--gap_split_sec", type=float, default=0.35)
    ap.add_argument("--max_cue_sec", type=float, default=3.0)
    ap.add_argument("--max_line", type=int, default=16)
    ap.add_argument("--max_lines", type=int, default=2)
    ap.add_argument("--max_chars", type=int, default=32)
    ap.add_argument("--min_cue_ms", type=int, default=250)
    ap.add_argument("--coverage_min", type=float, default=0.85)
    args = ap.parse_args()

    wav = Path(args.audio).expanduser().resolve()
    spoken = Path(args.spoken).expanduser().resolve()
    out_srt = Path(args.out_srt).expanduser().resolve()

    if not wav.exists():
        raise FileNotFoundError(str(wav))
    if not spoken.exists():
        raise FileNotFoundError(str(spoken))

    meta = generate_srt_forcealign_spoken(
        wav_path=wav,
        spoken_path=spoken,
        out_srt=out_srt,
        model_name=str(args.model),
        language=str(args.language),
        gap_split_sec=float(args.gap_split_sec),
        max_cue_sec=float(args.max_cue_sec),
        max_line=int(args.max_line),
        max_lines=int(args.max_lines),
        max_chars_per_cue=int(args.max_chars),
        min_cue_ms=int(args.min_cue_ms),
        coverage_min=float(args.coverage_min),
    )

    print(f"OK: {out_srt}")
    print(f"meta: {meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
