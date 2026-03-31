"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 一个 .md 文件（纯文字）
Output: 最终 mp3 + srt（基于 DashScope 返回的时间戳，时间轴更精准）
Pos: debug/story_audio/run_md_to_story_audio_with_timestamps.py

说明
- 这是“新增的方法”，不会影响原来的 run_md_to_story_audio.py。
- 该实现使用 dashscope.audio.tts_v2 的 callback + additional_params={'word_timestamp_enabled': True} 获取时间戳。
- 为了保持实现简单：本脚本不做自动 SSML break（如需 break 请使用原脚本）。
"""

import argparse
import json
import os
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Optional


def _is_punct_break_token(token: str) -> bool:
    """Return True if this token should end a subtitle segment.

    用户确认：引号/括号/书名号不切。
    这里只切“停顿类标点”和换行。
    """
    if not token:
        return False

    # normalize whitespace-only
    if token.strip() == "":
        return False

    # newline forces break
    if "\n" in token or "\r" in token:
        return True

    # pause punctuation set (Chinese + English)
    pause_punct = set(
        [
            "。",
            "！",
            "？",
            "!",
            "?",
            "，",
            ",",
            "、",
            "；",
            ";",
            "：",
            ":",
        ]
    )

    # token may be multi-char (e.g. "……" or "——")
    if token in ("……", "——"):
        return True

    # single-char punctuation
    if len(token) == 1 and token in pause_punct:
        return True

    return False


def _split_words_to_srt_entries(
    words: list[dict],
    *,
    max_chars_per_entry: int = 24,
) -> list[tuple[int, int, str]]:
    """Split DashScope word-timestamp words into multiple subtitle entries.

    - 逗号等所有“停顿标点”都切分
    - 不在引号/括号/书名号处切分（按用户要求）
    - 额外加一个长度阈值，避免无标点时字幕过长

    words item schema: {'text': str, 'begin_time': int/float, 'end_time': int/float, ...}
    """

    def flush(cur_text: list[str], begin_ms: Optional[int], end_ms: Optional[int]) -> Optional[tuple[int, int, str]]:
        if not cur_text or begin_ms is None or end_ms is None:
            return None
        text = "".join(cur_text).strip()
        if not text:
            return None
        return (int(begin_ms), int(end_ms), text)

    out: list[tuple[int, int, str]] = []

    cur_text: list[str] = []
    cur_begin: Optional[int] = None
    cur_end: Optional[int] = None

    for w in words:
        t = w.get("text")
        bt = w.get("begin_time")
        et = w.get("end_time")

        # Skip if no timestamps; keep behavior simple
        if not isinstance(bt, (int, float)) or not isinstance(et, (int, float)):
            continue
        if not t:
            continue

        if cur_begin is None:
            cur_begin = int(bt)
        cur_end = int(et)

        cur_text.append(str(t))

        # 1) punctuation/newline ends segment
        if _is_punct_break_token(str(t)):
            seg = flush(cur_text, cur_begin, cur_end)
            if seg:
                out.append(seg)
            cur_text = []
            cur_begin = None
            cur_end = None
            continue

        # 2) length threshold ends segment (insurance)
        if max_chars_per_entry > 0 and sum(len(x) for x in cur_text) >= int(max_chars_per_entry):
            seg = flush(cur_text, cur_begin, cur_end)
            if seg:
                out.append(seg)
            cur_text = []
            cur_begin = None
            cur_end = None
            continue

    # tail
    seg = flush(cur_text, cur_begin, cur_end)
    if seg:
        out.append(seg)

    return out


def _xml_escape_text(s: str) -> str:
    # Escape plain text for SSML XML
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

# 允许直接运行该脚本：把项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from config.logging_config import setup_logging

import dashscope
from dashscope.audio.tts_v2 import AudioFormat, ResultCallback, SpeechSynthesizer


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _count_cosyvoice_chars(text: str) -> int:
    """Approximate CosyVoice character counting rule.

    官方规则：汉字(含日文汉字/韩文汉字)按2个字符，其它按1个字符。
    这里用 Unicode 区段做近似：CJK Unified Ideographs + Extension A。
    """
    n = 0
    for ch in text:
        code = ord(ch)
        is_cjk = (
            0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
            or 0x3400 <= code <= 0x4DBF  # CJK Unified Ideographs Extension A
        )
        n += 2 if is_cjk else 1
    return n


def _split_raw_text_blocks(raw_text: str, max_chars: int = 20000, safety_margin: int = 1500) -> list[str]:
    """Split raw text into blocks that satisfy CosyVoice length limit.

    为了简单和稳：
    - 按官方计数规则近似计数（汉字2，其它1）
    - 加 safety_margin 保守切分，避免边界误差导致服务端仍报超限
    - 优先在段落/换行/强标点处截断
    """
    t = _normalize_text(raw_text).strip()
    if not t:
        return []

    limit = max(1000, int(max_chars) - int(safety_margin))

    blocks: list[str] = []
    start = 0
    n = len(t)

    break_chars = set(["。", "！", "？", "!", "?", "\n"])

    while start < n:
        # 如果剩余直接满足
        if _count_cosyvoice_chars(t[start:]) <= limit:
            blocks.append(t[start:])
            break

        cur = 0
        end = start
        last_good_break = None
        last_good_end = start

        while end < n:
            ch = t[end]
            code = ord(ch)
            is_cjk = (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF)
            add = 2 if is_cjk else 1

            # 特殊双字符标点：…… / ——
            if t.startswith("……", end):
                add = 2  # 两个字符，都是非CJK，按1+1
            if t.startswith("——", end):
                add = 2

            if cur + add > limit:
                break

            cur += add
            end += 1
            last_good_end = end

            if ch in break_chars:
                last_good_break = end
            if t.startswith("……", end - 1) or t.startswith("——", end - 1):
                last_good_break = end

        # 优先按最近的断点切
        cut = last_good_break if (last_good_break and last_good_break > start) else last_good_end
        if cut <= start:
            cut = max(start + 1, end)

        block = t[start:cut].strip()
        if block:
            blocks.append(block)
        start = cut

    return blocks


def _break_tag(ms: int) -> str:
    return f"<break time=\"{int(ms)}ms\"/>"


def _iter_ssml_tokens(text: str) -> list[str]:
    """把纯文本转成 token 列表（已 XML escape），token 包含文字和 break 标签。"""
    t = _normalize_text(text)
    out: list[str] = []

    i = 0
    n = len(t)
    while i < n:
        # 段落空行
        if t.startswith("\n\n", i):
            out.append(_break_tag(250))
            while i < n and t[i] == "\n":
                i += 1
            continue

        # 单个换行
        if t[i] == "\n":
            out.append(_break_tag(80))
            i += 1
            continue

        # 省略号（中文）
        if t.startswith("……", i):
            out.append(_xml_escape_text("……"))
            out.append(_break_tag(500))
            i += 2
            continue

        # 连续破折号
        if t[i] == "—":
            j = i
            while j < n and t[j] == "—":
                j += 1
            dash = t[i:j]
            out.append(_xml_escape_text(dash))
            if (j - i) >= 2:
                out.append(_break_tag(300))
            i = j
            continue

        ch = t[i]

        if ch in "。！？!?":
            out.append(_xml_escape_text(ch))
            out.append(_break_tag(250))
            i += 1
            continue

        if ch in "，,、；;：:":
            out.append(_xml_escape_text(ch))
            out.append(_break_tag(120))
            i += 1
            continue

        out.append(_xml_escape_text(ch))
        i += 1

    return out


def _to_ssml_with_breaks(text: str) -> str:
    tokens = _iter_ssml_tokens(text)
    return "<speak>" + "".join(tokens) + "</speak>"


def _split_ssml_blocks(raw_text: str, max_len: int = 12000) -> list[str]:
    """Split into multiple <speak>...</speak> blocks so that each SSML string length <= max_len.

    说明：在 tts_v2 当前行为下，服务端似乎按“整段 text 字符串长度”计数（包含标签）。
    因此这里按 SSML 字符串长度做保守切分。
    """
    tokens = _iter_ssml_tokens(raw_text)
    blocks: list[str] = []

    cur: list[str] = []
    # pre-count wrapper length
    wrapper = len("<speak></speak>")
    cur_len = wrapper

    for tok in tokens:
        tok_len = len(tok)
        if cur and (cur_len + tok_len) > max_len:
            blocks.append("<speak>" + "".join(cur) + "</speak>")
            cur = []
            cur_len = wrapper

        cur.append(tok)
        cur_len += tok_len

    if cur:
        blocks.append("<speak>" + "".join(cur) + "</speak>")

    return blocks


def _build_tts_blocks_and_debug_ssml(
    *,
    raw_text: str,
    no_break: bool,
    audio_max_chars: int = 20000,
    audio_safety_margin: int = 1500,
    ssml_max_len: int = 12000,
) -> tuple[list[str], Optional[str]]:
    """Build tts blocks and (optional) merged debug SSML text.

    约定：
    - no_break=True：直接按官方计数规则切 raw text，不生成 ssml。
    - no_break=False：生成 ssml token + 分块，并返回一个合并后的 ssml（仅用于写出检查文件）。

    ⚠️ 停顿规则固定在 _iter_ssml_tokens 里；这里不做参数化。
    """
    t = _normalize_text(raw_text).strip()
    if not t:
        return [], None

    if no_break:
        blocks = _split_raw_text_blocks(t, max_chars=audio_max_chars, safety_margin=audio_safety_margin)
        return blocks, None

    ssml_blocks = _split_ssml_blocks(t, max_len=ssml_max_len)

    # 生成一份“检查用”的合并 ssml：把每个 block 的 <speak>...</speak> 去壳后拼起来，块间插入固定 break
    inner: list[str] = []
    for s in ssml_blocks:
        if s.startswith("<speak>"):
            s = s[len("<speak>"):]
        if s.endswith("</speak>"):
            s = s[: -len("</speak>")]
        inner.append(s)
        inner.append(_break_tag(250))

    debug_ssml = "<speak>" + "".join(inner).rstrip() + "</speak>"
    return ssml_blocks, debug_ssml


def run_generation(
    *,
    input_path: Path,
    model: str,
    voice: str,
    speech_rate: float,
    pitch_rate: float,
    volume: int,
    no_break: bool,
    dump_events: int,
    out_dir: Path,
    instruction: Optional[str] = None,
    run_ts: Optional[str] = None,
) -> tuple[Path, Path, Optional[Path]]:
    """Reusable entrypoint: md(纯文本) -> wav + srt (+ optional ssml debug file)."""
    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not run_ts:
        run_ts = time.strftime("%Y%m%d_%H%M%S")

    base_name = input_path.stem
    out_audio = out_dir / f"{base_name}_{run_ts}.wav"
    out_srt = out_dir / f"{base_name}_{run_ts}.srt"

    raw_text = _read_text_file(input_path).strip()
    if not raw_text:
        raise ValueError("输入文件为空")

    tts_blocks, debug_ssml_text = _build_tts_blocks_and_debug_ssml(
        raw_text=raw_text,
        no_break=bool(no_break),
        audio_max_chars=20000,
        audio_safety_margin=1500,
        ssml_max_len=12000,
    )
    if not tts_blocks:
        raise RuntimeError("无法切分出有效文本块")

    out_ssml: Optional[Path] = None
    if debug_ssml_text:
        out_ssml = out_dir / f"{base_name}_{run_ts}.ssml"
        out_ssml.write_text(debug_ssml_text, encoding="utf-8")

    # PCM/WAV 输出
    sample_rate = 22050
    channels = 1
    sampwidth = 2

    pcm_all = bytearray()
    entries_all: list[tuple[int, int, str]] = []
    offset_ms = 0

    audio_format = AudioFormat.PCM_22050HZ_MONO_16BIT

    for bi, tts_text in enumerate(tts_blocks):
        cb = TimestampCallback(dump_events=int(dump_events) if bi == 0 else 0)
        synthesizer = SpeechSynthesizer(
            model=model,
            voice=voice,
            format=audio_format,
            speech_rate=float(speech_rate),
            volume=int(volume),
            pitch_rate=float(pitch_rate),
            instruction=(instruction if instruction else None),
            callback=cb,
            additional_params={"word_timestamp_enabled": True},
        )

        synthesizer.call(tts_text)
        cb.wait_done(timeout_s=600)

        if not cb.pcm:
            raise RuntimeError(f"第{bi}块未接收到 PCM 音频数据")

        pcm_all.extend(cb.pcm)

        block_ms = int(len(cb.pcm) / (sample_rate * channels * sampwidth) * 1000)

        # Assemble entries.
        # Some backends/models may return word timestamps relative to each sentence (reset to 0).
        # If we detect that, we rebuild a monotonic global timeline by concatenating sentences
        # and scaling to match block_ms.
        entries: list[tuple[int, int, str]] = []

        def _detect_sentence_relative() -> bool:
            if not cb._entries_by_index:
                return False
            mins: list[int] = []
            max_end = 0
            for segs in cb._entries_by_index.values():
                if not segs:
                    continue
                mb = min(int(b) for b, _, _ in segs)
                me = max(int(e) for _, e, _ in segs)
                mins.append(mb)
                max_end = max(max_end, me)
            if len(mins) < 2:
                return False
            zeros = sum(1 for x in mins if x == 0)
            # heuristics: most sentences start at 0 AND max_end is far smaller than block length
            return zeros >= max(2, int(len(mins) * 0.6)) and max_end < int(block_ms * 0.5)

        if _detect_sentence_relative():
            # sentence-relative mode
            order = cb._sentence_order or sorted(cb._entries_by_index.keys())
            # Ensure stable unique order
            seen = set()
            order2: list[int] = []
            for idx in order:
                if idx in seen:
                    continue
                seen.add(idx)
                order2.append(idx)

            def _est_span(text: str) -> int:
                t = (text or "").strip()
                if not t:
                    return 800
                # proportional weight; actual scale will be fitted to block_ms
                return max(800, _count_cosyvoice_chars(t) * 60)

            items: list[tuple[int, list[tuple[int, int, str]] | None, int, int, str]] = []
            # (idx, segs|None, min_begin, span_raw, fallback_text)
            for idx in order2:
                segs = cb._entries_by_index.get(idx)
                if segs:
                    mb = min(int(b) for b, _, _ in segs)
                    me = max(int(e) for _, e, _ in segs)
                    span = max(1, me - mb)
                    items.append((idx, segs, mb, span, ""))
                else:
                    txt = cb._sentence_text.get(idx, "")
                    items.append((idx, None, 0, _est_span(txt), txt))

            total_raw = sum(span for _, _, _, span, _ in items)
            if total_raw <= 0:
                total_raw = 1
            scale = float(block_ms) / float(total_raw)

            cur_off = 0
            for _, segs, mb, span_raw, fb_text in items:
                seg_len = int(round(span_raw * scale))
                if seg_len <= 0:
                    seg_len = 1

                if segs:
                    for b, e, t in segs:
                        b2 = cur_off + int(round((int(b) - int(mb)) * scale))
                        e2 = cur_off + int(round((int(e) - int(mb)) * scale))
                        entries.append((b2, e2, t))
                else:
                    if fb_text.strip():
                        entries.append((cur_off, cur_off + seg_len, fb_text.strip()))

                cur_off += seg_len

            # also include no-index fallback entries (best-effort): place them at the end of the block
            for b, e, t in cb.entries:
                # clamp into [0, block_ms]
                b2 = max(0, min(int(block_ms - 1), int(b)))
                e2 = max(b2 + 1, min(int(block_ms), int(e)))
                entries.append((b2, e2, t))

            # Ensure last entry does not exceed block_ms too much (rounding)
            if entries:
                # shift any overflow by trimming the last cue
                entries.sort(key=lambda x: (x[0], x[1]))
                lb, le, lt = entries[-1]
                if le > block_ms:
                    entries[-1] = (lb, max(lb + 1, int(block_ms)), lt)
        else:
            # global-timestamp mode (old behavior)
            for segs in cb._entries_by_index.values():
                entries.extend(segs)
            entries.extend(cb.entries)

        for b, e, t in entries:
            entries_all.append((int(b) + offset_ms, int(e) + offset_ms, t))

        offset_ms += block_ms

    # 写标准 WAV（头信息正确）
    with wave.open(str(out_audio), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm_all))

    if not entries_all:
        raise RuntimeError("未获取到时间戳 entries（请检查音色是否支持时间戳）")

    _write_srt(out_srt, entries_all)

    return out_audio, out_srt, out_ssml


def _format_srt_time(ms: int) -> str:
    if ms < 0:
        ms = 0
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _normalize_entries(entries: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Sort by begin_time and clamp to non-overlapping, monotonic timeline.

    注意：这里不做“按音频总时长缩放/截断”，只负责排序与去重。
    """
    entries = [(b, e, t) for (b, e, t) in entries if t.strip()]
    entries.sort(key=lambda x: (x[0], x[1]))

    out: list[tuple[int, int, str]] = []
    for b, e, t in entries:
        b = int(b)
        e = int(e)
        if e <= b:
            e = b + 1

        if not out:
            out.append((b, e, t))
            continue

        pb, pe, pt = out[-1]

        # 若发生重叠：优先“回缩上一条的 end”来消除重叠，避免把当前 begin 往后推导致累计变慢。
        if b < pe:
            # 能正常回缩
            if b > pb:
                new_pe = min(pe, b)
                if new_pe <= pb:
                    new_pe = pb + 1
                out[-1] = (pb, new_pe, pt)
                pb, pe, pt = out[-1]
            else:
                # 极端乱序：当前 begin 早于上一条 begin，无法回缩上一条
                # 这里保守处理：把当前 begin 推到上一条 end（这类情况应很少，不会形成大规模累计）
                b = pe

        # 经过上面的处理后，确保单调不重叠
        if b < out[-1][1]:
            b = out[-1][1]
        if e <= b:
            e = b + 1

        # 去重：连续相同文本，合并到上一条
        if out and out[-1][2] == t:
            out[-1] = (out[-1][0], max(out[-1][1], e), t)
            continue

        out.append((b, e, t))

    return out


def _write_srt(srt_path: Path, entries: list[tuple[int, int, str]]) -> None:
    entries = _normalize_entries(entries)

    lines: list[str] = []
    for idx, (begin, end, text) in enumerate(entries, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_srt_time(begin)} --> {_format_srt_time(end)}")
        lines.append(text)
        lines.append("")
    srt_path.write_text("\n".join(lines), encoding="utf-8")


class TimestampCallback(ResultCallback):
    def __init__(self, dump_events: int = 0):
        self._done = threading.Event()
        self._error: Optional[str] = None

        self._dump_events = max(0, int(dump_events))
        self._dumped = 0

        # PCM buffer (16-bit mono)
        self.pcm = bytearray()

        # collect sentence entries by sentence index (stable, allows overwrite)
        # 一个 sentence 可能会被切成多条字幕，因此 value 是 list
        self._entries_by_index: dict[int, list[tuple[int, int, str]]] = {}
        # sentence order + original_text (best-effort)
        self._sentence_order: list[int] = []
        self._sentence_text: dict[int, str] = {}
        # fallback entries if index is missing
        self.entries: list[tuple[int, int, str]] = []

    def on_open(self) -> None:
        # PCM 模式下无需预先打开文件，直接缓存 bytes
        pass

    def on_complete(self) -> None:
        self._done.set()

    def on_error(self, message) -> None:
        self._error = str(message)
        self._done.set()

    def on_close(self) -> None:
        pass

    def on_data(self, data: bytes) -> None:
        # PCM: 直接追加到 buffer
        self.pcm.extend(data)

    def on_event(self, message: str) -> None:
        # 需要示例时：原样输出部分 message
        if self._dumped < self._dump_events:
            print(message)
            self._dumped += 1

        # message 是 JSON 字符串
        try:
            obj = json.loads(message)
        except Exception:
            return

        output = obj.get("payload", {}).get("output", {})
        sentence = output.get("sentence")
        if not sentence:
            return

        # Track sentence order/text even when no words present.
        idx = sentence.get("index")
        if isinstance(idx, int):
            if not self._sentence_order or self._sentence_order[-1] != idx:
                # sentence index is monotonic in practice; keep first-seen order
                if idx not in self._sentence_order:
                    self._sentence_order.append(idx)

            ot = output.get("original_text")
            if isinstance(ot, str) and ot.strip():
                # keep the longest non-empty original_text
                prev = self._sentence_text.get(idx, "")
                if len(ot.strip()) >= len(prev.strip()):
                    self._sentence_text[idx] = ot.strip()

        words = sentence.get("words") or []
        if not words:
            return

        # 把 words 按标点（含逗号）切成多个字幕片段
        seg_entries = _split_words_to_srt_entries(words, max_chars_per_entry=24)
        if not seg_entries:
            return

        def _score(segs: list[tuple[int, int, str]]) -> tuple[int, int, int]:
            # Prefer entries that cover larger time span and contain more text.
            # Note: begin/end are ms within current block.
            if not segs:
                return (0, 0, 0)
            b0 = int(segs[0][0])
            e1 = int(segs[-1][1])
            span = max(0, e1 - b0)
            chars = sum(len(str(t)) for _, _, t in segs)
            n = len(segs)
            return (span, chars, n)

        idx2 = sentence.get("index")
        if isinstance(idx2, int):
            # 同一个 sentence index 的 event 可能到达多次：有时后到的反而更不完整。
            # 为避免“覆盖导致丢块”，这里保留 score 更高（更完整）的那份。
            prev = self._entries_by_index.get(idx2)
            if prev is None or _score(seg_entries) >= _score(prev):
                self._entries_by_index[idx2] = seg_entries
        else:
            # 没有 index 的兜底
            self.entries.extend(seg_entries)

    def wait_done(self, timeout_s: Optional[float] = None) -> None:
        self._done.wait(timeout=timeout_s)
        if self._error:
            raise RuntimeError(self._error)


def main() -> int:
    parser = argparse.ArgumentParser(description="md(纯文本) -> 有声书 audio + srt（时间戳模式/更精准）")
    parser.add_argument("--input", required=True, help="输入 md 文件路径（纯文字）")

    # 默认对齐你当前高僧音设置
    parser.add_argument("--model", default="cosyvoice-v2", help="DashScope CosyVoice 模型")
    parser.add_argument("--voice", default="longgaoseng", help="音色 voice id")

    parser.add_argument("--speech_rate", type=float, default=1.3, help="语速（默认 1.3）")
    parser.add_argument("--volume", type=int, default=50, help="音量（默认 50）")
    # 兼容：DashScope 参数名为 pitch_rate；同时保留旧的 --pitch 以及可选别名 --h_rate
    parser.add_argument(
        "--pitch_rate",
        "--pitch",
        "--h_rate",
        dest="pitch_rate",
        type=float,
        default=1.0,
        help="音高(pitch_rate)乘数，范围[0.5, 2.0]，默认1.0；<1 变低，>1 变高",
    )

    parser.add_argument("--no_break", action="store_true", help="禁用自动插入 SSML <break>（默认启用）")
    parser.add_argument("--dump_events", type=int, default=0, help="打印前 N 条原始 on_event JSON（用于排查）")
    parser.add_argument("--format", choices=["wav"], default="wav", help="输出音频格式（固定 wav：由 PCM 封装，确保时长与时间戳对齐）")

    parser.add_argument(
        "--out_dir",
        default=str(Path(__file__).parent / "output"),
        help="最终输出目录（audio + srt）",
    )

    args = parser.parse_args()

    setup_logging()
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 未配置")

    dashscope.api_key = api_key

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    run_ts = time.strftime("%Y%m%d_%H%M%S")
    base_name = input_path.stem

    out_audio = out_dir / f"{base_name}_{run_ts}.wav"
    out_srt = out_dir / f"{base_name}_{run_ts}.srt"

    raw_text = _read_text_file(input_path).strip()
    if not raw_text:
        raise ValueError("输入文件为空")

    # 分块：
    # - no_break: 按官方计数规则切
    # - break(SSML): 按 SSML 字符串长度保守切（避免服务端仍报超限）
    if args.no_break:
        blocks = _split_raw_text_blocks(raw_text, max_chars=20000, safety_margin=1500)
        if not blocks:
            raise RuntimeError("无法切分出有效文本块")
    else:
        ssml_blocks = _split_ssml_blocks(raw_text, max_len=12000)
        if not ssml_blocks:
            raise RuntimeError("无法切分出有效 SSML 文本块")

        # 写出一份合并后的 ssml（便于检查），并用 ssml_blocks 进行逐块合成
        inner = []
        for s in ssml_blocks:
            if s.startswith("<speak>"):
                s = s[len("<speak>"):]
            if s.endswith("</speak>"):
                s = s[: -len("</speak>")]
            inner.append(s)
            inner.append(_break_tag(600))
        ssml_text = "<speak>" + "".join(inner).rstrip() + "</speak>"
        ssml_path = out_dir / f"{base_name}_{run_ts}.ssml"
        ssml_path.write_text(ssml_text, encoding="utf-8")

    # PCM/WAV 输出
    sample_rate = 22050
    channels = 1
    sampwidth = 2

    pcm_all = bytearray()
    entries_all: list[tuple[int, int, str]] = []
    offset_ms = 0

    audio_format = AudioFormat.PCM_22050HZ_MONO_16BIT

    if args.no_break:
        tts_blocks = blocks
    else:
        tts_blocks = ssml_blocks

    for bi, tts_text in enumerate(tts_blocks):

        cb = TimestampCallback(dump_events=args.dump_events if bi == 0 else 0)
        synthesizer = SpeechSynthesizer(
            model=args.model,
            voice=args.voice,
            format=audio_format,
            speech_rate=args.speech_rate,
            volume=args.volume,
            pitch_rate=args.pitch_rate,
            callback=cb,
            additional_params={"word_timestamp_enabled": True},
        )

        synthesizer.call(tts_text)
        cb.wait_done(timeout_s=600)

        if not cb.pcm:
            raise RuntimeError(f"第{bi}块未接收到 PCM 音频数据")

        # 拼接 PCM
        pcm_all.extend(cb.pcm)

        # 该块时长（ms）用于累加 offset
        block_ms = int(len(cb.pcm) / (sample_rate * channels * sampwidth) * 1000)

        # 收集该块 entries，并加上 offset
        entries: list[tuple[int, int, str]] = []
        for segs in cb._entries_by_index.values():
            entries.extend(segs)
        entries.extend(cb.entries)

        for b, e, t in entries:
            entries_all.append((int(b) + offset_ms, int(e) + offset_ms, t))

        offset_ms += block_ms

    # 写标准 WAV（头信息正确）
    with wave.open(str(out_audio), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm_all))

    if not entries_all:
        raise RuntimeError("未获取到时间戳 entries（请检查音色是否支持时间戳）")

    _write_srt(out_srt, entries_all)

    print(f"OK: {out_audio}")
    print(f"OK: {out_srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
