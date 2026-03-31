"""Profile: cabian_001

约定：
- 本文件只维护“差异/默认值”，不包含流程逻辑。
- 所有字段必须给出具体值（不允许 None）。
"""

from __future__ import annotations

from data import test_prompt_script as tps


PROFILE: dict = {
    # ===== meta =====
    "name": "cabian_001",  # profile 名称（用于输出/日志标识）
    "style": "cabian",  # 风格标签（仅用于人类识别；流程逻辑不应依赖它）

    # ===== spoken（Call#1：从 raw_text 生成口播稿） =====
    "spoken_system_1": tps.CABIAN_SYS_PROMPT_001_01,  # system prompt（字符串）
    "spoken_user_1_template": "{raw_text}",  # user prompt 模板：必须包含 {raw_text}

    # ===== image prompt sync（Step5：scene -> 每幕生图 JSON prompt） =====
    "img_prompt_system": tps.CABIAN_IMAGE_PROMPT_SYNC_PROMPT_002,  # system prompt
    "img_prompt_user_template": (
        # user prompt 模板：必须包含 {num_images} 与 {text}
        "你将收到按时间轴聚合的多个 scene（每个 scene 对应一张图）。\n"
        "请为每个 scene 生成 1 条生图提示词，总计 {num_images} 条。\n"
        "要求：只输出 JSON 数组（不要 markdown 代码块，不要解释），数组长度必须等于 {num_images}。\n\n"
        "Scenes:\n{text}\n"
    ),
    "img_prompt_base": tps.CABIAN_IMAGE_PROMPT_BASE_001,  # base JSON（dict）：用于补齐缺失字段/统一风格字段
    "img_prompt_batch_size": 8,  # 单次请求生成多少条 prompt（整数，建议 4~12）

    # ===== image generation（Step6：实际生图） =====
    "aspect_ratio": "9:16",  # 出图比例（字符串：如 "9:16"）
    "ref_image": (
        # 参考图（字符串路径）：用于锁定人物/画风（实现依赖具体生图脚本）
        # 约定：放到本项目内，便于分发
        "assets/ref_images/cabian_ref.png"
    ),

    # ===== tts（Step2：口播稿 -> wav + srt） =====
    "tts_model": "cosyvoice-v3-flash",  # TTS 模型名（字符串）
    "use_cloned_voice": True,  # 是否使用克隆音色（bool）
    "cloned_voice_id": "cosyvoice-v3-flash-gualiu002-c0d8bae2fe1342e0a2df480501e75921",  # 克隆音色 ID（字符串）
    "speech_rate": 1.0,  # 语速（float，1.0 为默认）
    "pitch_rate": 1.0,  # 音高（float，1.0 为默认）
    "no_break": False,  # 是否减少停顿（bool；不同 TTS 后端含义可能不同）
    "instruction": "我想体验一下自然的语气。",  # 口播风格指令（字符串）

    # ===== video（Step7：按 storyboard 合成视频） =====
    "video_width": 1080,  # 视频宽（int）
    "video_height": 1920,  # 视频高（int）
    "video_fps": 30,  # FPS（int）
    "zoom_end": 1.25,  # Ken Burns 缩放终值（float；1.0=不缩放；建议 1.10~1.35）
    "ffmpeg_bin": "ffmpeg",  # ffmpeg 可执行文件名或绝对路径（字符串）
}
