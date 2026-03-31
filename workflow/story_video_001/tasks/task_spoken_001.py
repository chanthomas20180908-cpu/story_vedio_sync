"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 原文文本
Output: 口播稿（最终输出为 TTS 可直接输入的纯口播文字）
Pos: story_video_001 - task_spoken_001

说明（保持最简单）：
- 两次模型调用：
  1) Call#1：根据 profile 提供的 system_prompt_1/user_prompt_1_template 生成口播稿初稿
  2) Call#3：用 data/test_prompt_script.py 中的“清洗提示词”清洗为纯口播文字
- 不提供/不支持第二轮（Call#2）
- 差异只来自 Call#1 提示词（由 profile 管理）
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv

from component.chat.chat import chat_with_model
from data import test_prompt_script

DEFAULT_MODEL_TYPE = "gemini"
DEFAULT_MODEL = "gemini-3-flash-preview"


def _format_template(template: str, params: Dict[str, str]) -> str:
    return template.format(**params)


def task_spoken_001(
    raw_text: str,
    *,
    system_prompt_1: str,
    user_prompt_1_template: str,
    api_key: Optional[str] = None,
    model_type: str = DEFAULT_MODEL_TYPE,
    model: str = DEFAULT_MODEL,
    thinking_level: Optional[str] = None,
) -> str:
    if not system_prompt_1.strip() or not user_prompt_1_template.strip():
        raise RuntimeError("spoken 提示词为空：system_prompt_1/user_prompt_1_template 不能为空")

    # load api key
    # - gemini: official google-genai key
    # - gemini_cloubic: cloubic proxy key
    if api_key is None:
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../env/default.env"))
        if str(model_type).strip() == "gemini_cloubic":
            api_key = os.getenv("CLOUBIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "未找到 CLOUBIC_API_KEY（请在 env/default.env 或环境变量中配置，或显式传 api_key）"
                )
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "未找到 GEMINI_API_KEY（请在 env/default.env 或环境变量中配置，或显式传 api_key）"
                )
    if not api_key:
        raise RuntimeError("api_key 为空（请检查环境变量或显式传 api_key）")

    # -------- Call #1 --------
    user_prompt_1 = _format_template(user_prompt_1_template, {"raw_text": raw_text})
    mid = chat_with_model(
        api_key=api_key,
        model_type=model_type,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt_1},
            {"role": "user", "content": user_prompt_1},
        ],
        thinking_level=thinking_level,
    )
    if not mid:
        raise RuntimeError("第一次模型调用失败：未返回内容")

    final_script = mid

    # -------- Call #3（TTS清洗） --------
    system_prompt_3 = getattr(test_prompt_script, "SPOKEN_CLEAN_SYSTEM_PROMPT_001", "").strip()
    user_prompt_3_template = getattr(test_prompt_script, "SPOKEN_CLEAN_USER_PROMPT_TEMPLATE_001", "").strip()
    if not system_prompt_3 or not user_prompt_3_template:
        raise RuntimeError(
            "缺少 spoken 清洗提示词：请在 data/test_prompt_script.py 中定义 "
            "SPOKEN_CLEAN_SYSTEM_PROMPT_001 与 SPOKEN_CLEAN_USER_PROMPT_TEMPLATE_001"
        )

    user_prompt_3 = _format_template(
        user_prompt_3_template,
        {"raw_text": raw_text, "mid": mid, "final_script": final_script},
    )

    tts_script = chat_with_model(
        api_key=api_key,
        model_type=model_type,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt_3},
            {"role": "user", "content": user_prompt_3},
        ],
        thinking_level=thinking_level,
    )
    if not tts_script:
        raise RuntimeError("第三次模型调用失败：未返回内容")

    return tts_script
