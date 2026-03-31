"""\
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 原文文本
Output: 口播稿（最终输出为 TTS 可直接输入的纯口播文字）
Pos: story_video_001 - task_spoken_cabian_001

说明（保持最简单，且与 kesulu 对齐）：
- 仅保留两次模型调用：Call#1 生成口播稿初稿；Call#3 清洗为纯口播文字（TTS 可直接输入）
- 不提供/不支持第二轮（Call#2）
- system_prompt_3/user_prompt_3_template 写死在代码内部（从外部入参移除）
- 对外统一导出 task_spoken_001(raw_text, system_prompt_1, user_prompt_1_template, ...) 作为最小接口
- 默认使用 Gemini Flash: gemini-3-flash-preview
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv

from component.chat.chat import chat_with_model
from config.logging_config import setup_logging
from data import test_prompt_script

DEFAULT_MODEL_TYPE = "gemini"
DEFAULT_MODEL = "gemini-3-flash-preview"


def _format_template(template: str, params: Dict[str, str]) -> str:
    """最简模板替换：使用 str.format(**params)。"""
    return template.format(**params)


SYSTEM_PROMPT_3 = "你是TTS口播文本清洗器。只输出可直接朗读的口播文字正文。".strip()
USER_PROMPT_3_TEMPLATE = "{final_script}"  # 最简：第三轮直接清洗 final_script


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
    """统一口播入口（与 kesulu 对齐）。

    仅使用：
    - system_prompt_1 / user_prompt_1_template（Call#1）
    - 固定的 system_prompt_3 / user_prompt_3_template（Call#3）

    不提供第二轮。
    """

    return spoken_script_workflow_two_calls(
        raw_text,
        api_key=api_key,
        model_type=model_type,
        model=model,
        thinking_level=thinking_level,
        system_prompt_1=system_prompt_1,
        user_prompt_1_template=user_prompt_1_template,
        system_prompt_2="",
        user_prompt_2_template="{mid}",
        system_prompt_3=SYSTEM_PROMPT_3,
        user_prompt_3_template=USER_PROMPT_3_TEMPLATE,
    )


# 兼容旧命名（若未来你希望直接调用）
spoken_script_cabian_001 = task_spoken_001


def spoken_script_workflow_two_calls(
    raw_text: str,
    *,
    # 模型/鉴权
    api_key: Optional[str] = None,
    model_type: str = DEFAULT_MODEL_TYPE,
    model: str = DEFAULT_MODEL,
    thinking_level: Optional[str] = None,
    # 第一次调用提示词
    system_prompt_1: str,
    user_prompt_1_template: str,
    user_params_1: Optional[Dict[str, str]] = None,
    # 第二次调用提示词
    system_prompt_2: str = "",
    user_prompt_2_template: str = "{mid}",
    user_params_2: Optional[Dict[str, str]] = None,
    # 第三次调用提示词（TTS清洗）
    system_prompt_3: str = "",
    user_prompt_3_template: str = "{final_script}",
    user_params_3: Optional[Dict[str, str]] = None,
) -> str:
    """三次模型调用：raw_text -> (mid) -> (final_script) -> (tts_script)。

    注意：cabian 版本的提示词默认留空；若完全留空则抛错，避免误跑。
    """

    if not system_prompt_1.strip() or not user_prompt_1_template.strip():
        raise RuntimeError(
            "cabian 口播提示词为空：请在 data/test_prompt_script.py 填写 CABIAN_SYS_PROMPT_001_01，"
            "或在调用 spoken_script_cabian_001 时传入 system_prompt_1/user_prompt_1_template。"
        )

    if api_key is None:
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("未找到 GEMINI_API_KEY（请在 env/default.env 或环境变量中配置，或显式传 api_key）")

    # -------- Call #1 --------
    params1 = {"raw_text": raw_text}
    if user_params_1:
        params1.update(user_params_1)

    user_prompt_1 = _format_template(user_prompt_1_template, params1)

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

    # 与 kesulu 对齐：暂时跳过第二轮
    final_script = mid

    # -------- Call #3（TTS清洗） --------
    if not system_prompt_3:
        # cabian 默认也允许留空，但建议用户填；这里给一个最小兜底
        system_prompt_3 = "你是TTS口播文本清洗器。只输出可直接朗读的口播文字正文。"

    params3 = {"raw_text": raw_text, "mid": mid, "final_script": final_script}
    if user_params_3:
        params3.update(user_params_3)

    user_prompt_3 = _format_template(user_prompt_3_template, params3)

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


if __name__ == "__main__":
    # cd /Users/test/code/Python/AI_vedio_demo/pythonProject && source .venv/bin/activate && PYTHONPATH=. python3 workflow/taskgroup/spoken_script_cabian_001.py

    setup_logging()

    raw_text = "测试输入：这里放一段原文"
    out = spoken_script_cabian_001(
        raw_text,
        system_prompt_1="（TODO）在这里填写 cabian 的 system prompt",
        user_prompt_1_template="（TODO）根据下面原文生成口播稿：\n\n{raw_text}",
    )
    print(out)
