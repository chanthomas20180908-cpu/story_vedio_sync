"""md(纯文本) -> 有声书 audio + srt（时间戳模式） + 可选声音复刻（clone）

目标
- 不影响现有脚本：debug/story_audio/run_md_to_story_audio_with_timestamps.py
- 新增一个“合并入口”：可选先用参考音频复刻音色得到 voice_id，再用该 voice_id 合成 md 并生成 wav+srt

用法示例
1) 仅使用已有 voice_id（不复刻）：
python3 debug/story_audio/run_md_to_story_audio_with_clone.py \
  --input "debug/story_audio/input_tmp.md" \
  --model "cosyvoice-v3-plus" \
  --voice "cosyvoice-..." \
  --speech_rate 1.3 \
  --pitch_rate 1.0

2) 复刻 + 直接使用复刻音色合成：
python3 debug/story_audio/run_md_to_story_audio_with_clone.py \
  --input "debug/story_audio/input_tmp.md" \
  --model "cosyvoice-v3-plus" \
  --use_cloned_voice \
  --clone_ref_mp3 "/path/to/ref.mp3" \
  --clone_prefix "man_story_001" \
  --clone_voice_name "jianying_man_story_voice_001" \
  --speech_rate 1.3 \
  --pitch_rate 1.0

3) 不复刻，但显式指定“克隆 voice_id”并使用它：
python3 debug/story_audio/run_md_to_story_audio_with_clone.py \
  --input "debug/story_audio/input_tmp.md" \
  --model "cosyvoice-v3-plus" \
  --use_cloned_voice \
  --cloned_voice_id "cosyvoice-..." \
  --speech_rate 1.3 \
  --pitch_rate 1.0
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

# 允许直接运行该脚本：把项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService

from util.util_url import upload_file_to_oss_dedup_with_meta

# 复用原脚本的“合成 + 时间戳 + 分块”实现，避免复制逻辑
from debug.story_audio import run_md_to_story_audio_with_timestamps as ts


# 固定落盘：克隆音色注册表（写死路径，按 voice_id 作为唯一标识）
VOICE_REGISTRY_PATH = PROJECT_ROOT / "debug" / "story_audio" / "cosy_voices_clone.json"


T = TypeVar("T")


def _try_get_status_code(e: BaseException) -> Optional[int]:
    # best-effort extraction across various client libs
    for attr in ("status_code", "status", "http_status"):
        v = getattr(e, attr, None)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)

    resp = getattr(e, "response", None)
    if resp is not None:
        v = getattr(resp, "status_code", None)
        if isinstance(v, int):
            return v
    return None


def _is_retryable_error(e: BaseException) -> bool:
    # OSError / socket errors on macOS: 54 = Connection reset by peer
    if isinstance(e, OSError):
        if getattr(e, "errno", None) in {54, 104, 110, 111, 113}:  # common network errnos
            return True

    sc = _try_get_status_code(e)
    if sc in {408, 409, 425, 429, 500, 502, 503, 504}:
        return True

    msg = (str(e) or "").lower()
    transient_markers = [
        "503",
        "service unavailable",
        "too many requests",
        "429",
        "bad gateway",
        "502",
        "gateway timeout",
        "504",
        "connection reset",
        "reset by peer",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "remote end closed connection",
        "connection aborted",
        "connection refused",
    ]
    return any(m in msg for m in transient_markers)


def _call_with_retry(
    fn: Callable[[], T],
    *,
    what: str,
    max_retries: int = 5,
    base_sleep_seconds: float = 1.0,
    max_sleep_seconds: float = 30.0,
) -> T:
    """Retry transient network/API errors with exponential backoff + jitter."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:
            attempt += 1
            if attempt > max_retries or not _is_retryable_error(e):
                raise

            sc = _try_get_status_code(e)
            # exponential backoff with jitter
            sleep_s = min(max_sleep_seconds, base_sleep_seconds * (2 ** (attempt - 1)))
            sleep_s = sleep_s * (0.8 + random.random() * 0.4)
            hint = f"status_code={sc}" if sc is not None else ""
            print(
                f"[retry] {what}: attempt {attempt}/{max_retries} failed ({type(e).__name__}: {e}) {hint}; "
                f"sleep {sleep_s:.1f}s"
            )
            time.sleep(sleep_s)


def _load_api_key() -> str:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 未配置")
    return api_key


def _load_voice_registry() -> dict:
    if not VOICE_REGISTRY_PATH.exists():
        return {"by_id": {}}
    try:
        data = json.loads(VOICE_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"by_id": {}}

    if not isinstance(data, dict):
        return {"by_id": {}}

    by_id = data.get("by_id")
    if not isinstance(by_id, dict):
        data["by_id"] = {}
    return data


def _save_voice_registry(data: dict) -> None:
    VOICE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = VOICE_REGISTRY_PATH.with_suffix(VOICE_REGISTRY_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(VOICE_REGISTRY_PATH)


def _register_cloned_voice(*, voice_id: str, record: dict) -> None:
    reg = _load_voice_registry()
    reg.setdefault("by_id", {})
    reg["by_id"][voice_id] = record
    _save_voice_registry(reg)


def _get_voice_record(voice_id: str) -> Optional[dict]:
    reg = _load_voice_registry()
    rec = reg.get("by_id", {}).get(voice_id)
    return rec if isinstance(rec, dict) else None


def _poll_voice_ready(
    service: VoiceEnrollmentService,
    voice_id: str,
    poll_interval_seconds: int,
    max_attempts: int,
    *,
    retry_max_retries: int = 5,
    retry_base_sleep_seconds: float = 1.0,
    retry_max_sleep_seconds: float = 30.0,
) -> None:
    last_status = None
    for attempt in range(max_attempts):
        info = _call_with_retry(
            lambda: service.query_voice(voice_id=voice_id),
            what=f"query_voice(voice_id={voice_id})",
            max_retries=retry_max_retries,
            base_sleep_seconds=retry_base_sleep_seconds,
            max_sleep_seconds=retry_max_sleep_seconds,
        )
        status = info.get("status")
        last_status = status
        print(f"poll {attempt + 1}/{max_attempts}: status={status}")

        if status == "OK":
            return
        if status == "UNDEPLOYED":
            raise RuntimeError(f"音色不可用: status={status}, info={info}")

        time.sleep(poll_interval_seconds)

    raise RuntimeError(
        f"轮询超时：音色在 {max_attempts * poll_interval_seconds}s 内未就绪，last_status={last_status}"
    )


def _maybe_clone_and_resolve_voice(
    *,
    use_cloned_voice: bool,
    model: str,
    fallback_voice: str,
    clone_ref_mp3: Optional[str],
    clone_prefix: Optional[str],
    clone_voice_name: Optional[str],
    cloned_voice_id: Optional[str],
    oss_expire_seconds: int,
    poll_interval_seconds: int,
    max_attempts: int,
    retry_max_retries: int = 5,
    retry_base_sleep_seconds: float = 1.0,
    retry_max_sleep_seconds: float = 30.0,
) -> tuple[str, dict]:
    """返回 (final_voice_id, meta)。

    规则：
    - 如果 use_cloned_voice=False：直接用 fallback_voice
    - 如果 use_cloned_voice=True：
      - 优先 clone_ref_mp3：执行复刻并返回新 voice_id
      - 否则使用 cloned_voice_id
    """

    meta: dict = {
        "use_cloned_voice": use_cloned_voice,
        "final_voice": None,
        "clone": None,
    }

    if not use_cloned_voice:
        meta["final_voice"] = fallback_voice
        return fallback_voice, meta

    # use_cloned_voice=True
    if clone_ref_mp3:
        if not clone_prefix:
            raise ValueError("使用 --clone_ref_mp3 时必须同时提供 --clone_prefix")
        if len(clone_prefix) > 10:
            raise ValueError(f"clone_prefix 长度不能超过 10：{clone_prefix} (len={len(clone_prefix)})")

        ref_path = Path(clone_ref_mp3).expanduser().resolve()
        if not ref_path.exists():
            raise FileNotFoundError(str(ref_path))

        url, up_meta = upload_file_to_oss_dedup_with_meta(str(ref_path), oss_expire_seconds)

        service = VoiceEnrollmentService()
        voice_id = _call_with_retry(
            lambda: service.create_voice(
                target_model=model,
                prefix=clone_prefix,
                url=url,
                language_hints=["zh"],
            ),
            what="create_voice",
            max_retries=retry_max_retries,
            base_sleep_seconds=retry_base_sleep_seconds,
            max_sleep_seconds=retry_max_sleep_seconds,
        )

        clone_request_id = service.get_last_request_id()
        print(f"clone_request_id={clone_request_id}")
        print(f"cloned_voice_id={voice_id}")
        if clone_voice_name:
            print(f"cloned_voice_name={clone_voice_name}")

        _poll_voice_ready(
            service=service,
            voice_id=voice_id,
            poll_interval_seconds=poll_interval_seconds,
            max_attempts=max_attempts,
            retry_max_retries=retry_max_retries,
            retry_base_sleep_seconds=retry_base_sleep_seconds,
            retry_max_sleep_seconds=retry_max_sleep_seconds,
        )

        record = {
            "voice_id": voice_id,
            "model": model,
            "clone_prefix": clone_prefix,
            "clone_voice_name": clone_voice_name,
            "ref_mp3": str(ref_path),
            "oss_url": url,
            "oss_meta": up_meta,
            "clone_request_id": clone_request_id,
            "created_at": time.strftime("%Y%m%d_%H%M%S"),
        }
        _register_cloned_voice(voice_id=voice_id, record=record)
        print(f"voice_registry={VOICE_REGISTRY_PATH}")

        meta["clone"] = record
        meta["final_voice"] = voice_id
        return voice_id, meta

    if cloned_voice_id:
        rec = _get_voice_record(cloned_voice_id)
        if rec:
            # 仅提示/对齐：避免 model 不一致导致合成失败
            if rec.get("model") and rec.get("model") != model:
                raise ValueError(
                    f"cloned_voice_id={cloned_voice_id} 注册表记录 model={rec.get('model')} 与本次 --model={model} 不一致"
                )
        meta["final_voice"] = cloned_voice_id
        meta["cloned_voice_record"] = rec
        return cloned_voice_id, meta

    raise ValueError(
        "已指定 --use_cloned_voice，但未提供 --clone_ref_mp3 或 --cloned_voice_id。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="md(纯文本) -> audio+srt（时间戳）; 可选先复刻音色"
    )

    # 合成参数（沿用原脚本）
    parser.add_argument("--input", required=False, help="输入 md 文件路径（纯文字）；--clone_only 模式下可不传")
    parser.add_argument("--model", default="cosyvoice-v2", help="DashScope CosyVoice 模型")
    parser.add_argument("--voice", default="longgaoseng", help="音色 voice id（当不使用克隆时生效）")

    parser.add_argument("--speech_rate", type=float, default=1.3, help="语速")
    parser.add_argument("--volume", type=int, default=50, help="音量")
    parser.add_argument(
        "--pitch_rate",
        "--pitch",
        "--h_rate",
        dest="pitch_rate",
        type=float,
        default=1.0,
        help="音高(pitch_rate)乘数，范围[0.5, 2.0]，默认1.0",
    )
    parser.add_argument(
        "--instruction",
        default=None,
        help="合成指令（用于方言/情感/角色等；仅对 cosyvoice-v3-flash 的复刻音色或支持 Instruct 的系统音色生效）",
    )

    parser.add_argument("--no_break", action="store_true", help="禁用自动插入 SSML <break>（默认启用）")
    parser.add_argument("--dump_events", type=int, default=0, help="打印前 N 条原始 on_event JSON（用于排查）")
    parser.add_argument("--format", choices=["wav"], default="wav", help="输出音频格式（固定 wav）")
    parser.add_argument(
        "--out_dir",
        default=str(Path(__file__).parent / "output"),
        help="最终输出目录（audio + srt）",
    )

    # 仅复刻：只保存 voice_id 到注册表，不做后续生成
    parser.add_argument(
        "--clone_only",
        action="store_true",
        help="仅执行克隆并写入注册表（debug/story_audio/cosy_voices_clone.json），不生成音频",
    )

    # 复刻/复用参数（新增）
    parser.add_argument(
        "--use_cloned_voice",
        action="store_true",
        help="开启后优先使用克隆音色（要么本次复刻，要么用 --cloned_voice_id）",
    )
    parser.add_argument("--cloned_voice_id", default=None, help="要使用的克隆 voice_id（不复刻时用）")
    parser.add_argument("--clone_ref_mp3", default=None, help="参考音频路径（传了则执行复刻）")
    parser.add_argument("--clone_prefix", default=None, help="复刻音色 prefix（与 create_voice 的 prefix 一致）")
    parser.add_argument("--clone_voice_name", default=None, help="仅用于标注/输出的人类可读名字")
    parser.add_argument("--oss_expire_seconds", type=int, default=3600, help="参考音频上传 URL 有效期（秒）")
    parser.add_argument("--clone_poll_interval", type=int, default=10, help="复刻状态轮询间隔（秒）")
    parser.add_argument("--clone_max_attempts", type=int, default=30, help="复刻状态最大轮询次数")

    # 重试参数：用于 503/54 等短暂错误恢复
    parser.add_argument("--retry_max_retries", type=int, default=5, help="遇到可重试错误时的最大重试次数")
    parser.add_argument("--retry_base_sleep", type=float, default=1.0, help="重试退避的基础睡眠秒数")
    parser.add_argument("--retry_max_sleep", type=float, default=30.0, help="单次重试最大睡眠秒数")

    args = parser.parse_args()

    # 初始化日志与 API Key
    ts.setup_logging()
    dashscope.api_key = _load_api_key()

    final_voice, meta = _maybe_clone_and_resolve_voice(
        use_cloned_voice=bool(args.use_cloned_voice),
        model=args.model,
        fallback_voice=args.voice,
        clone_ref_mp3=args.clone_ref_mp3,
        clone_prefix=args.clone_prefix,
        clone_voice_name=args.clone_voice_name,
        cloned_voice_id=args.cloned_voice_id,
        oss_expire_seconds=int(args.oss_expire_seconds),
        poll_interval_seconds=int(args.clone_poll_interval),
        max_attempts=int(args.clone_max_attempts),
        retry_max_retries=int(args.retry_max_retries),
        retry_base_sleep_seconds=float(args.retry_base_sleep),
        retry_max_sleep_seconds=float(args.retry_max_sleep),
    )

    # 只克隆：到这里已经完成 create+poll+落盘
    if args.clone_only:
        print(f"final_voice={final_voice}")
        print(f"voice_registry={VOICE_REGISTRY_PATH}")
        if meta.get("clone") and isinstance(meta["clone"], dict):
            print(f"cloned_voice_id={meta['clone'].get('voice_id')}")
            if meta["clone"].get("clone_voice_name"):
                print(f"cloned_voice_name={meta['clone'].get('clone_voice_name')}")
        return 0

    if not args.input:
        raise ValueError("缺少 --input（非 --clone_only 模式必须提供）")

    # 生成：委托给 timestamps 模块，避免复制 SSML/分块/合成逻辑
    out_audio, out_srt, out_ssml = _call_with_retry(
        lambda: ts.run_generation(
            input_path=Path(args.input),
            model=args.model,
            voice=final_voice,
            speech_rate=args.speech_rate,
            pitch_rate=args.pitch_rate,
            volume=args.volume,
            no_break=bool(args.no_break),
            dump_events=int(args.dump_events),
            out_dir=Path(args.out_dir),
            instruction=args.instruction,
        ),
        what="run_generation",
        max_retries=int(args.retry_max_retries),
        base_sleep_seconds=float(args.retry_base_sleep),
        max_sleep_seconds=float(args.retry_max_sleep),
    )

    print(f"OK: {out_audio}")
    print(f"OK: {out_srt}")
    if out_ssml:
        print(f"OK: {out_ssml}")

    # 输出 voice 相关信息（便于你后续复用）
    print(f"final_voice={final_voice}")
    print(f"voice_registry={VOICE_REGISTRY_PATH}")

    if meta.get("clone") and isinstance(meta["clone"], dict):
        print(f"cloned_voice_id={meta['clone'].get('voice_id')}")
        if meta["clone"].get("clone_voice_name"):
            print(f"cloned_voice_name={meta['clone'].get('clone_voice_name')}")

    if meta.get("cloned_voice_record"):
        # 从注册表命中时，提示一下
        print("cloned_voice_record_found=1")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
