"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: storyboard（scene 列表，含 start/end 与 image_path）、音频 wav
Output: mp4 视频（不烧字幕），可用于后续剪映导入
Pos: 工作流 - 图片+音频合成视频（xfade 交叉溶解版本）

设计目标（保持简单 & 可控）：
- 仍然按 scene 渲染独立 seg（方便替换图片/重渲染）
- 但拼接时使用 ffmpeg filter_complex 的 xfade 做“相邻片段真正融合”的转场
- 最终整体会重编码（xfade 无法 -c copy）

注意：
- xfade 的 offset 需要基于累计时长计算。
- 为避免卡住，仍然采用“固定输出帧数（-frames:v）”来保证每段时长可控。
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ComposeVideoParams:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    zoom_start: float = 1.0
    # 项目默认：缩放幅度要足够明显（可在 activity/CLI 覆盖）
    zoom_end: float = 1.25


def _run(cmd: list[str], *, cwd: Optional[Path] = None) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if p.returncode != 0:
        stdout_head = (p.stdout or "").splitlines()[:30]
        stderr_head = (p.stderr or "").splitlines()[:80]
        raise RuntimeError(
            "Command failed:\n"
            f"cmd={' '.join(cmd)}\n"
            f"returncode={p.returncode}\n"
            f"stdout(head)=\n" + "\n".join(stdout_head) + "\n\n"
            f"stderr(head)=\n" + "\n".join(stderr_head) + "\n"
        )
    return p.stdout


def _load_storyboard(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def compose_video_from_storyboard_002(
    *,
    storyboard_json: str | Path,
    audio_path: str | Path,
    out_mp4: str | Path,
    tmp_dir: str | Path,
    params: ComposeVideoParams = ComposeVideoParams(),
    ffmpeg_bin: str = "ffmpeg",
    crf: int = 18,
    preset: str = "medium",
    # 项目默认：转场稍慢一点，不那么“割裂”
    xfade_s: float = 0.80,
    xfade_transition: str = "fade",
    max_scenes: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> Path:
    """逐段渲染 seg，然后用 xfade 融合转场，最后 mux 音频。"""

    storyboard_json = Path(storyboard_json)
    audio_path = Path(audio_path)
    out_mp4 = Path(out_mp4)
    tmp_dir = Path(tmp_dir)

    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    sb = _load_storyboard(storyboard_json)
    scenes = sb.get("scenes") or []
    if not scenes:
        raise ValueError(f"storyboard scenes 为空: {storyboard_json}")

    if max_scenes is not None:
        if max_scenes <= 0:
            raise ValueError(f"max_scenes 必须 > 0: {max_scenes}")
        scenes = scenes[: int(max_scenes)]

    if len(scenes) == 1:
        # 单 scene：不需要 xfade
        xfade_s = 0.0

    xfade_s = max(0.0, float(xfade_s))

    if logger:
        logger.info(
            "compose_video_002: start "
            f"scenes={len(scenes)} xfade_s={xfade_s} transition={xfade_transition} "
            f"audio={audio_path} storyboard={storyboard_json} out={out_mp4} tmp_dir={tmp_dir}"
        )

    seg_paths: list[Path] = []
    durations: list[float] = []

    # 1) render each segment as mp4 (frame-limited)
    # NOTE:
    # - We use xfade (overlap) later, which would otherwise shorten the final video by (N-1)*xfade_s.
    # - To keep the final duration aligned with storyboard/audio, we reserve xfade time by extending
    #   every segment except the last by +xfade_s. The overlap then cancels out.
    for i, sc in enumerate(scenes, start=1):
        sid = int(sc.get("scene_id"))
        start_s = _safe_float(sc.get("start_s", 0.0))
        end_s = _safe_float(sc.get("end_s", 0.0))

        is_last = i == len(scenes)
        duration = max(0.05, end_s - start_s)
        if not is_last and xfade_s > 0:
            duration += float(xfade_s)

        img = sc.get("image_override") or sc.get("image_path")
        if not img:
            raise ValueError(f"scene_{sid:03d} 缺少 image_path/image_override")
        img_path = Path(img)
        if not img_path.exists():
            raise FileNotFoundError(str(img_path))

        frames = int(round(duration * params.fps))
        if frames < 2:
            frames = 2

        # ping-pong zoom (in then out) + smoothstep
        z0 = float(params.zoom_start)
        z1 = float(params.zoom_end)
        half = max(1.0, (frames - 1) / 2.0)
        u = f"if(lte(on,{half:.6f}), on/{half:.6f}, ({(frames - 1):.6f}-on)/{half:.6f})"
        ease = f"({u})*({u})*(3-2*({u}))"
        zoom_expr = f"min({max(z0, z1)},{z0}+({z1}-{z0})*({ease}))"

        vf = (
            f"scale={params.width}:{params.height}:force_original_aspect_ratio=decrease,"
            f"pad={params.width}:{params.height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"zoompan=z='{zoom_expr}':x='(iw-ow)/2':y='(ih-oh)/2':d=1:s={params.width}x{params.height},"
            f"fps={params.fps}"
        )

        seg_out = tmp_dir / f"seg_{sid:03d}.mp4"
        seg_paths.append(seg_out)
        durations.append(duration)

        if logger:
            logger.info(
                f"compose_video_002: render seg {i}/{len(scenes)} scene_id={sid} "
                f"duration={duration:.3f}s frames={frames} img={img_path.name} -> {seg_out.name}"
            )

        cmd = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img_path),
            "-vf",
            vf,
            "-frames:v",
            str(frames),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            str(crf),
            "-preset",
            preset,
            str(seg_out),
        ]
        _run(cmd)

    # 2) xfade chain to produce video_no_audio
    video_no_audio = tmp_dir / "video_no_audio_xfade.mp4"

    if len(seg_paths) == 1:
        # just re-use the rendered segment as base video (copy)
        cmd_copy = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(seg_paths[0]),
            "-c",
            "copy",
            str(video_no_audio),
        ]
        _run(cmd_copy)
    else:
        # offsets: crossfade starts at (sum(prev_durations) - i*xfade_s)
        # ensure non-negative and monotonic.
        offsets: list[float] = []
        acc = 0.0
        for i in range(1, len(durations)):
            acc += durations[i - 1]
            off = acc - (i * xfade_s)
            offsets.append(max(0.0, off))

        # Build filter_complex:
        # [0:v][1:v]xfade=transition=fade:duration=...:offset=... [v01];
        # [v01][2:v]xfade=... [v012]; ...
        parts: list[str] = []
        cur = "[0:v]"
        for i in range(1, len(seg_paths)):
            nxt = f"[{i}:v]"
            out = f"[v{i}]"  # intermediate label
            off = offsets[i - 1]
            parts.append(
                f"{cur}{nxt}xfade=transition={xfade_transition}:duration={xfade_s:.3f}:offset={off:.3f}{out}"
            )
            cur = out
        filter_complex = ";".join(parts)

        cmd_xfade = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
        ]
        for p in seg_paths:
            cmd_xfade.extend(["-i", str(p)])
        cmd_xfade.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                cur,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                str(crf),
                "-preset",
                preset,
                str(video_no_audio),
            ]
        )

        if logger:
            logger.info(
                f"compose_video_002: xfade {len(seg_paths)} segs -> {video_no_audio.name} "
                f"xfade_s={xfade_s}"
            )
        _run(cmd_xfade)

    # 3) mux audio
    cmd_mux = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_no_audio),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(out_mp4),
    ]
    if logger:
        logger.info(f"compose_video_002: mux audio -> {out_mp4.name}")
    _run(cmd_mux)

    if logger:
        logger.info(f"compose_video_002: DONE out={out_mp4}")

    return out_mp4
