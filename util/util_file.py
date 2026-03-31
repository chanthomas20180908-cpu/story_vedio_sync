#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 测试数据或模块
Output: 测试结果
Pos: 测试文件：util_file.py
"""

"""
文件处理工具模块

包含视频/音频下载、处理、转换等工具函数：
- 文件下载（支持重试、断点续传）
- 音频拆分与合并
- 视频拆分与合并
- 视频抽帧
- 音频转录（Whisper）
- SRT字幕解析与处理
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import requests
from urllib.parse import urlparse

# Heavy/optional deps:
# - Keep util_file importable in "base" environments (no moviepy/faster_whisper).
# - Functions that require these deps will raise a clear error at runtime if missing.
try:
    from pydub import AudioSegment  # type: ignore
except Exception:  # pragma: no cover
    AudioSegment = None  # type: ignore

try:
    from moviepy import VideoFileClip, concatenate_videoclips  # type: ignore
except Exception:  # pragma: no cover
    VideoFileClip = None  # type: ignore
    concatenate_videoclips = None  # type: ignore

try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover
    WhisperModel = None  # type: ignore

import config.config as config
from config.logging_config import get_logger, setup_logging


# 项目启动时初始化日志
logger = get_logger(__name__)


def download_file_from_url(
        file_url: str,
        save_dir: Union[str, Path] = "downloads",
        filename: Optional[str] = None,
        chunk_size: int = 8192,
        timeout: int = 30,
        max_retries: int = 3
) -> str:
    """
    从url下载文件到指定目录

    Args:
        file_url: 要下载的文件URL
        save_dir: 保存目录，默认为当前脚本目录下的downloads文件夹
        filename: 自定义文件名，如果为None则从URL中提取
        chunk_size: 每次读取的字节数，默认8192
        timeout: 请求超时时间（秒），默认30秒
        max_retries: 最大重试次数，默认3次

    Returns:
        str: 保存文件的完整路径
    """

    # 输入验证
    if not file_url or not isinstance(file_url, str):
        raise ValueError("file_url 必须是非空字符串")

    # 处理文件名和扩展名
    if filename is None:
        parsed_url = urlparse(file_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = "downloaded_file"

    # # 关键修复：自动添加视频扩展名
    # filename = _ensure_video_extension(filename, file_url)

    # 确保save_dir是Path对象
    if isinstance(save_dir, str):
        save_dir = Path(save_dir)

    save_dir.mkdir(parents=True, exist_ok=True)
    final_path = save_dir / filename

    # 如果文件已存在，生成新名称
    if final_path.exists():
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while final_path.exists():
            new_filename = f"{base_name}_{counter}{ext}"
            final_path = save_dir / new_filename
            counter += 1

    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'video/mp4,video/*,*/*;q=0.8'
    }

    # 重试机制
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

                logger.info(f"🔄 开始下载文件: {filename} (尝试 {attempt + 1}/{max_retries + 1})")

                # 下载文件（不依赖HEAD请求的大小）
                with requests.get(file_url, headers=headers, stream=True, timeout=timeout) as resp:
                    resp.raise_for_status()

                    # 尝试从响应头获取实际文件大小
                    total_size = int(resp.headers.get('content-length', 0))
                    if total_size > 0:
                        logger.info(f"📁 文件大小: {total_size / (1024 * 1024):.2f} MB")

                    downloaded_size = 0
                    last_progress = 0

                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded_size += len(chunk)

                            # 优化进度显示：只在有总大小且合理时显示百分比
                            if total_size > 0 and total_size > downloaded_size:
                                progress = (downloaded_size / total_size) * 100
                                # 每10%显示一次
                                if progress - last_progress >= 10:
                                    logger.info(
                                        f"📥 下载进度: {progress:.1f}% ({downloaded_size / (1024 * 1024):.2f}MB)")
                                    last_progress = progress
                            else:
                                # 没有总大小时，每5MB显示一次
                                current_mb = downloaded_size // (5 * 1024 * 1024)
                                if current_mb > last_progress:
                                    logger.info(f"📥 已下载: {downloaded_size / (1024 * 1024):.2f}MB")
                                    last_progress = current_mb

                logger.info(f"📦 下载完成，总大小: {downloaded_size / (1024 * 1024):.2f}MB")

                # 验证文件不为空
                if downloaded_size == 0:
                    raise Exception("下载的文件为空")

                # 验证文件是否为视频文件（简单检查）
                if not _is_valid_video_file(temp_path, downloaded_size):
                    logger.warning("⚠️  文件可能不是有效的视频文件")

                # 原子性移动文件到目标位置
                shutil.move(temp_path, final_path)

                logger.info(f"✅ 视频文件已成功保存到: {final_path}")
                return str(final_path)

        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.error(f"❌ 网络请求失败 (尝试 {attempt + 1}): {e}")

        except Exception as e:
            last_exception = e
            logger.error(f"❌ 下载失败 (尝试 {attempt + 1}): {e}")

        finally:
            # 清理临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries:
            wait_time = 2 ** attempt
            logger.warning(f"⏳ {wait_time} 秒后重试...")
            time.sleep(wait_time)

    # 所有重试都失败
    raise Exception(f"下载失败，已尝试 {max_retries + 1} 次。最后错误: {last_exception}")


def _ensure_video_extension(filename: str, file_url: str) -> str:
    """
    确保文件有正确的视频扩展名
    
    Args:
        filename: 原始文件名
        file_url: 文件源URL，用于推断扩展名
        
    Returns:
        str: 带有正确扩展名的文件名
    """
    # 如果文件名已经有扩展名，直接返回
    if '.' in filename and filename.split('.')[-1].lower() in ['mp4', 'avi', 'mov', 'mkv', 'flv', 'webm']:
        return filename

    # 根据URL或Content-Type判断扩展名
    video_extensions = {
        'mp4': '.mp4',
        'avi': '.avi',
        'mov': '.mov',
        'mkv': '.mkv',
        'webm': '.webm'
    }

    # 从URL中检查
    url_lower = file_url.lower()
    for ext_key, ext_value in video_extensions.items():
        if ext_key in url_lower:
            return f"{filename}{ext_value}"

    # 默认使用mp4扩展名
    return f"{filename}.mp4"


def _is_valid_video_file(file_path: str, file_size: int) -> bool:
    """
    简单验证是否为有效的视频文件
    
    Args:
        file_path: 文件路径
        file_size: 文件大小（字节）
        
    Returns:
        bool: True 表示可能是有效视频，False 表示很可能不是
    """
    # 大小检查：视频文件通常大于1KB
    if file_size < 1024:
        return False

    # 读取文件头部分，检查视频文件的魔术字节
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        # MP4文件头检查
        if b'ftyp' in header[:12]:
            return True

        # AVI文件头检查
        if header[:4] == b'RIFF' and header[8:12] == b'AVI ':
            return True

        # WebM文件头检查
        if header[:4] == b'\x1a\x45\xdf\xa3':
            return True

        # MOV文件通常也有ftyp
        if b'moov' in header or b'mdat' in header:
            return True

    except Exception:
        pass

    # 如果无法确定，但文件大小合理，就认为有效
    return file_size > 10 * 1024  # 大于10KB


# 针对你的使用场景的专用函数
def download_video_file(video_url: str, save_dir: Union[str, Path], task_id: str) -> str:
    """
    专门下载视频文件的函数（对 download_file_from_url 的封装）
    
    Args:
        video_url: 视频文件URL
        save_dir: 保存目录
        task_id: 任务ID，用于生成文件名
        
    Returns:
        str: 保存的文件完整路径
        
    Raises:
        Exception: 下载失败时抛出
    """
    filename = f"my_video_{task_id}.mp4"  # 明确指定mp4扩展名

    return download_file_from_url(
        file_url=video_url,
        save_dir=save_dir,
        filename=filename,
        chunk_size=16384,  # 增大chunk_size提高视频下载速度
        timeout=60,  # 视频文件通常较大，增加超时时间
        max_retries=3
    )


def split_mp3(input_path: Union[str, Path], segment_length: int, output_dir: Union[str, Path] = "split_results") -> List[str]:
    """
    将MP3音频按指定时长拆分为多个文件

    Args:
        input_path: 原始MP3文件路径
        segment_length: 每段音频的时长（单位：秒）
        output_dir: 拆分后的文件保存目录（默认：split_results）

    Returns:
        List[str]: 拆分后的文件路径列表
        
    Raises:
        FileNotFoundError: 输入文件不存在
    """
    # 转换为 Path 对象
    input_path = Path(input_path) if isinstance(input_path, str) else input_path
    output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    if AudioSegment is None:
        raise ModuleNotFoundError(
            "缺少依赖: pydub。请安装 requirements.heavy.txt（或单独安装 pydub）后再使用 split_mp3。"
        )

    # 读取音频文件
    audio = AudioSegment.from_mp3(str(input_path))
    total_duration = len(audio) / 1000  # 毫秒转秒
    logger.info(f"原始音频时长: {total_duration:.2f} 秒")

    # 拆分音频
    segment_files = []
    segment_ms = segment_length * 1000  # 转换为毫秒
    for i, start in enumerate(range(0, len(audio), segment_ms)):
        end = min(start + segment_ms, len(audio))
        segment = audio[start:end]

        # 生成文件名
        base_name = input_path.stem
        output_file = output_dir / f"{base_name}_part{i+1}.mp3"

        # 导出音频
        segment.export(str(output_file), format="mp3")
        segment_files.append(str(output_file))
        logger.info(f"已生成: {output_file} （时长 {len(segment)/1000:.2f}s）")

    logger.info(f"拆分完成，共 {len(segment_files)} 段")
    return segment_files


def merge_videos(video_list: List[Union[str, Path]], output_path: Union[str, Path] = "merged_video.mp4") -> str:
    """
    将多个视频片段拼接成一个完整视频

    Args:
        video_list: 视频文件路径列表
        output_path: 输出文件路径（默认 merged_video.mp4）

    Returns:
        str: 合并后的视频文件路径
        
    Raises:
        ValueError: video_list 为空
        RuntimeError: 没有有效的视频片段
    """
    if not video_list:
        raise ValueError("video_list 不能为空")

    # 转换为 Path 对象
    output_path = Path(output_path) if isinstance(output_path, str) else output_path
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if VideoFileClip is None or concatenate_videoclips is None:
        raise ModuleNotFoundError(
            "缺少依赖: moviepy。请安装 requirements.heavy.txt（或单独安装 moviepy）后再使用 merge_videos。"
        )

    clips = []
    for path in video_list:
        path = Path(path) if isinstance(path, str) else path
        if not path.exists():
            logger.warning(f"找不到文件: {path}，跳过")
            continue
        clip = VideoFileClip(str(path))
        clips.append(clip)

    if not clips:
        raise RuntimeError("没有有效的视频片段可以拼接")

    # 拼接视频（按时间顺序）
    final_clip = concatenate_videoclips(clips, method="compose")

    # 导出视频
    final_clip.write_videofile(str(output_path), codec="libx264", audio_codec="aac")

    # 释放资源
    for clip in clips:
        clip.close()
    final_clip.close()

    logger.info(f"视频拼接完成: {output_path}")
    return str(output_path)


def extract_video_frames_by_interval(video_path: Union[str, Path], interval: float = 1, output_dir: Union[str, Path] = None) -> List[Path]:
    """
    按照指定间隔时长，从视频中抽帧

    Args:
        video_path: 视频文件路径
        interval: 抽帧间隔（秒），默认1秒
        output_dir: 输出目录（默认为视频所在目录的frames子目录）
        
    Returns:
        List[Path]: 生成的帧文件路径列表
    """
    # 转换为 Path 对象
    video_path = Path(video_path) if isinstance(video_path, str) else video_path

    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return []

    # 设置输出目录
    if output_dir is None:
        output_dir = video_path.parent / "frames"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    logger.info("=" * 80)
    logger.info("🎬 视频抽帧")
    logger.info("=" * 80)
    logger.info(f"📹 视频: {video_path.name}")
    logger.info(f"⏱️  间隔: {interval}秒")
    logger.info(f"📁 输出: {output_dir}")

    # 获取视频时长
    duration_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    try:
        result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.info(f"⏱️  视频时长: {duration:.2f}秒")

        # 计算预计帧数
        estimated_frames = int(duration // interval) + 1
        logger.info(f"📊 预计帧数: {estimated_frames}")

    except Exception as e:
        logger.warning(f"无法获取视频时长: {e}")
        duration = None

    # 输出文件模板
    output_pattern = output_dir / f"{video_path.stem}_frame_%04d.jpg"

    # ffmpeg命令：每interval秒抽一帧
    # fps=1/interval 表示每interval秒一帧
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps=1/{interval}",  # 每interval秒一帧
        "-q:v", "2",  # JPEG质量（1-31，数字越小质量越高）
        "-y",
        str(output_pattern)
    ]

    logger.info("🔄 开始抽帧...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # 统计生成的帧数
        frames = sorted(output_dir.glob(f"{video_path.stem}_frame_*.jpg"))

        logger.info(f"✅ 成功抽取 {len(frames)} 帧")
        logger.info(f"📁 输出目录: {output_dir}")

        # 显示前5帧
        logger.info("📸 抽帧预览：")
        logger.info("=" * 80)
        for i, frame in enumerate(frames[:5], 1):
            file_size = frame.stat().st_size / 1024  # KB
            logger.info(f"  [{i}] {frame.name} ({file_size:.1f} KB)")

        if len(frames) > 5:
            logger.info(f"  ... 共 {len(frames)} 帧 ...")

        logger.info("=" * 80)
        logger.info("✅ 完成")
        logger.info("=" * 80)
        
        return frames

    else:
        logger.error("抽帧失败")
        logger.error(f"错误信息: {result.stderr}")
        return []


def extract_audio_from_video(video_path: Union[str, Path]) -> Path:
    """
    从视频文件中提取音频为MP3格式
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        Path: 提取的音频文件路径（{video_stem}_temp.mp3）
        
    Raises:
        subprocess.CalledProcessError: ffmpeg执行失败
    """
    # 转换为 Path 对象
    video_path = Path(video_path) if isinstance(video_path, str) else video_path
    audio_path = video_path.parent / f"{video_path.stem}_temp.mp3"

    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame",
        "-ar", "16000", "-ac", "1",
        "-ab", "128k", "-y",
        str(audio_path)
    ]

    logger.info(f"🎬 提取音频: {video_path.name}")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info("✅ 音频已提取")

    return audio_path


def transcribe_audio_to_srt(audio_path: Union[str, Path], output_srt: Union[str, Path], model_size: str = "small", language: str = "zh") -> dict:
    """转录音频并保存为SRT
    
    Returns:
        dict: 转录结果统计信息，包含 language, duration, segment_count
    """
    # 转换为 Path 对象
    audio_path = Path(audio_path) if isinstance(audio_path, str) else audio_path
    output_srt = Path(output_srt) if isinstance(output_srt, str) else output_srt

    def format_timestamp(seconds: float) -> str:
        """格式化时间戳为 SRT 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    if WhisperModel is None:
        raise ModuleNotFoundError(
            "缺少依赖: faster-whisper。请安装 requirements.heavy.txt（或单独安装 faster-whisper）后再使用转录功能。"
        )

    logger.info(f"⏳ 加载 Whisper 模型 ({model_size})...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    logger.info("🔄 开始转录...")
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    logger.info(f"✅ 语言: {info.language} (概率: {info.language_probability:.2f})")
    logger.info(f"✅ 时长: {info.duration:.2f} 秒")

    # 保存SRT
    all_segments = list(segments)
    with open(output_srt, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(all_segments, 1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment.text.strip()}\n\n")

    logger.info(f"✅ 字幕已保存: {output_srt}")
    logger.info(f"📊 共 {len(all_segments)} 条字幕")
    
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segment_count": len(all_segments)
    }


def parse_srt_into_list(srt_path: Union[str, Path]) -> List[Tuple[float, float, str]]:
    """
    解析SRT字幕文件
    
    Args:
        srt_path: SRT文件路径

    Returns:
        List[Tuple[float, float, str]]: 字幕列表，每项为 (start_time, end_time, text)
        
    Example:
        >>> segments = parse_srt(Path("subtitle.srt"))
        >>> for start, end, text in segments:
        ...     print(f"{start:.2f}s - {end:.2f}s: {text}")
    """
    # 转换为 Path 对象
    srt_path = Path(srt_path) if isinstance(srt_path, str) else srt_path
    segments = []

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 分割每个字幕块
    blocks = content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # 解析时间轴
        time_line = lines[1]
        match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})', time_line)

        if match:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())

            start_time = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
            end_time = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0

            text = '\n'.join(lines[2:])

            segments.append((start_time, end_time, text))

    return segments


def split_video_by_srt(video_path: Union[str, Path], srt_path: Union[str, Path], output_dir: Union[str, Path] = None, end_buffer: float = 0.5) -> List[Path]:
    """
    根据SRT字幕将视频拆分成多个片段

    Args:
        video_path: 视频文件路径
        srt_path: SRT字幕文件路径
        output_dir: 输出目录（默认为视频所在目录的segments子目录）
        end_buffer: 结束时间缓冲（秒），避免片段末尾包含下一片段开头，默认0.5秒
        
    Returns:
        List[Path]: 生成的视频片段路径列表
    """
    # 转换为 Path 对象
    video_path = Path(video_path) if isinstance(video_path, str) else video_path
    srt_path = Path(srt_path) if isinstance(srt_path, str) else srt_path

    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return []

    if not srt_path.exists():
        logger.error(f"SRT文件不存在: {srt_path}")
        return []

    # 设置输出目录
    if output_dir is None:
        output_dir = video_path.parent / "segments"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    logger.info("=" * 80)
    logger.info("✂️  视频拆分")
    logger.info("=" * 80)
    logger.info(f"📹 视频: {video_path.name}")
    logger.info(f"📝 字幕: {srt_path.name}")
    logger.info(f"📁 输出: {output_dir}")

    # 解析SRT
    logger.info("⏳ 解析SRT文件...")
    segments = parse_srt(srt_path)
    logger.info(f"✅ 找到 {len(segments)} 个片段")

    # 拆分视频
    logger.info("✂️  开始拆分视频...")

    output_files = []
    for i, (start_time, end_time, text) in enumerate(segments, 1):
        # 应用结束缓冲，避免片段末尾包含下一片段开头
        duration = end_time - start_time - end_buffer
        # 确保duration不会是负数
        if duration < 0.1:
            duration = end_time - start_time

        output_file = output_dir / f"{video_path.stem}_segment_{i:03d}.mp4"

        # ffmpeg命令：从start_time开始，持续duration秒
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:v", "libx264",  # 重新编码视频
            "-c:a", "aac",  # 重新编码音频
            "-y",  # 覆盖已存在文件
            str(output_file)
        ]

        actual_end = start_time + duration
        logger.info(f"[{i}/{len(segments)}] {start_time:.2f}s - {actual_end:.2f}s ({duration:.2f}s) [buffer: {end_buffer}s]")
        logger.info(f"    文本: {text[:50]}{'...' if len(text) > 50 else ''}")

        # 执行ffmpeg
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )

        if result.returncode == 0:
            logger.info(f"    ✅ {output_file.name}")
            output_files.append(output_file)
        else:
            logger.error(f"    ❌ 失败: {output_file.name}")

    logger.info("=" * 80)
    logger.info(f"✅ 完成！共生成 {len(output_files)} 个视频片段")
    logger.info(f"📁 输出目录: {output_dir}")
    logger.info("=" * 80)
    
    return output_files


if __name__ == "__main__":
    # 项目启动时初始化日志
    setup_logging()
    result = download_file_from_url("http://dashscope-result-hz.oss-cn-hangzhou.aliyuncs.com/1d/26/20250922/default/2ba2507671e24ad6bceaa1a1ca30292e_wologo.mp4?Expires=1758635022&OSSAccessKeyId=LTAI5tGx7yvUcG32VzcwNgQ6&Signature=y64wmDrTOZYsqjrZH5tLZ9q1lyU%3D",
                                    config.VIDEO_RESULTS_DIR,
                                    "my_video_test_001"
                                    )
