"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 用户消息
Output: AI回复
Pos: 基础聊天功能实现

更新记录:
- 2026-02-10: 集成 Gemini 3（model_type="gemini"），使用 google-genai SDK
"""

# file: /Users/thomaschan/Code/Python/AI_vedio_demo/pythonProject/component/chat.py
import os
import json
import time
import sys
import random
from typing import Optional, List, Dict, Any

from openai import OpenAI
from dotenv import load_dotenv
from config.logging_config import get_logger

# 项目启动时初始化日志
logger = get_logger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))



def _messages_to_plaintext(messages: List[Dict[str, str]]) -> str:
    """将 OpenAI 风格 messages 转为最简纯文本（用于非 OpenAI-compat SDK，如 Gemini）。"""
    parts: List[str] = []
    for m in messages or []:
        role = (m or {}).get("role", "user")
        content = (m or {}).get("content", "")
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _sleep_with_jitter(seconds: float) -> None:
    """带少量抖动的 sleep，避免并发重试同时撞车。"""
    jitter = random.uniform(0, 0.25 * seconds) if seconds > 0 else 0
    time.sleep(seconds + jitter)


class ChatModelClient:
    """聊天模型客户端基类"""

    def __init__(self, api_key: str, base_url: str):
        """
        初始化聊天模型客户端

        Args:
            api_key (str): API密钥
            base_url (str): API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_completion(self, _model: str, _messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[Any, Any]]:
        """
        聊天补全接口

        Args:
            _model (str): 模型名称
           _messages (List[Dict[str, str]]): 消息列表
            **kwargs: 其他参数

        Returns:
            Optional[Dict[Any, Any]]: 响应数据，失败时返回None
        """
        max_attempts = int(kwargs.pop("retry_max_attempts", 5))
        base_sleep = float(kwargs.pop("retry_base_sleep", 1.0))
        max_sleep = float(kwargs.pop("retry_max_sleep", 16.0))

        last_err: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=_model,
                    messages=_messages,
                    **kwargs,
                )
                return completion.model_dump()
            except Exception as e:
                last_err = e

                # 最简可恢复判断：根据异常信息里是否包含 429/5xx
                err_str = str(e)
                retryable = any(code in err_str for code in ["429", "500", "502", "503", "504"])
                if not retryable or attempt == max_attempts:
                    logger.error(f"聊天补全请求异常: {e}", exc_info=True)
                    return None

                sleep_s = min(max_sleep, base_sleep * (2 ** (attempt - 1)))
                logger.warning(
                    "聊天补全临时失败，准备重试 %s/%s，等待 %.2fs。错误: %s",
                    attempt,
                    max_attempts,
                    sleep_s,
                    e,
                )
                _sleep_with_jitter(sleep_s)

        # 理论不可达
        if last_err:
            logger.error(f"聊天补全请求异常: {last_err}", exc_info=True)
        return None


class GeminiClient:
    """Gemini 模型客户端（Gemini 3，使用 google-genai SDK）"""

    def __init__(self, api_key: str):
        """初始化 Gemini 客户端。

        说明：优先按约定使用环境变量 GEMINI_API_KEY。

        重要：增加请求超时（避免网络/代理异常导致进程卡住，进而用户误以为“终端崩溃/异常关闭”）。
        - 环境变量 GEMINI_REQUEST_TIMEOUT_SECONDS 可覆盖，默认 180 秒。
        """
        if api_key:
            # 兼容：允许通过函数入参传入 key
            os.environ["GEMINI_API_KEY"] = api_key

        try:
            from google import genai  # type: ignore
        except Exception as e:
            logger.error(
                f"Gemini SDK 未安装或导入失败，请安装 google-genai。错误: {e}",
                exc_info=True,
            )
            raise

        self._genai = genai

        # 设置硬超时，避免一直卡住。
        timeout_s = 180
        try:
            timeout_s = int(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", str(timeout_s)))
        except Exception:
            timeout_s = 180

        try:
            from google.genai import types  # type: ignore

            self.client = genai.Client(
                api_key=os.getenv("GEMINI_API_KEY"),
                # google-genai 的 HttpOptions.timeout 单位是“毫秒”
                http_options=types.HttpOptions(timeout=max(1, timeout_s) * 1000),
            )
        except Exception as e:
            # 兜底：即使 types/timeout 不可用，也要能跑起来。
            logger.warning(f"Gemini client 初始化 timeout 失败，将回退无 timeout。错误: {e}")
            self.client = genai.Client()

    def chat(
        self,
        _model: str,
        _messages: List[Dict[str, str]],
        thinking_level: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict[Any, Any]]:
        """Gemini 文本聊天。

        Args:
            _model: 模型 ID，如 gemini-3-pro-preview / gemini-3-flash-preview
            _messages: OpenAI 风格消息列表
            thinking_level: 可选，low/high（Flash 可能支持 minimal/medium）
        """
        logger.info(f"使用Gemini模型进行聊天: {_model}")

        try:
            contents = _messages_to_plaintext(_messages)

            # DEBUG: 打印请求内容（截断），便于排查提示词/输入
            try:
                _max_len = 2000
                _preview = contents if len(contents) <= _max_len else (contents[:_max_len] + "...<truncated>")
                logger.debug(
                    "Gemini request preview | model=%s | thinking_level=%s | chars=%s | contents=\n%s",
                    _model,
                    thinking_level,
                    len(contents),
                    _preview,
                )
            except Exception:
                # 日志不应影响主流程
                pass

            # 可选 thinking 配置（仅在传入时启用）
            config = None
            if thinking_level:
                try:
                    from google.genai import types  # type: ignore

                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
                    )
                except Exception as e:
                    logger.warning(
                        f"Gemini thinking_level 配置不可用（将忽略 thinking_level={thinking_level}）。错误: {e}"
                    )

            max_attempts = int(kwargs.pop("retry_max_attempts", 5))
            base_sleep = float(kwargs.pop("retry_base_sleep", 1.0))
            max_sleep = float(kwargs.pop("retry_max_sleep", 16.0))

            last_err: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    response = self.client.models.generate_content(
                        model=_model,
                        contents=contents,
                        config=config,
                    )
                    text = getattr(response, "text", "") or ""

                    # 适配为 OpenAI-like 结构，复用现有解析/日志逻辑
                    return {
                        "model": _model,
                        "choices": [{"message": {"content": text}}],
                        "usage": {},
                    }
                except Exception as e:
                    last_err = e

                    # 尽量只对临时错误重试（429/5xx/UNAVAILABLE/网络抖动）
                    err_str = str(e)
                    retryable = any(code in err_str for code in ["429", "500", "502", "503", "504", "UNAVAILABLE"])

                    # 补充：httpx 传输层异常（断连/超时/协议错误）也应重试。
                    # 例如：RemoteProtocolError("Server disconnected without sending a response")
                    if not retryable:
                        try:
                            import httpx  # type: ignore

                            if isinstance(e, httpx.TransportError):
                                retryable = True
                        except Exception:
                            # 不让导入失败影响主流程
                            pass

                    if not retryable or attempt == max_attempts:
                        logger.error(f"Gemini 请求异常: {e}", exc_info=True)
                        return None

                    sleep_s = min(max_sleep, base_sleep * (2 ** (attempt - 1)))
                    logger.warning(
                        "Gemini 临时失败，准备重试 %s/%s，等待 %.2fs。错误: %s",
                        attempt,
                        max_attempts,
                        sleep_s,
                        e,
                    )
                    _sleep_with_jitter(sleep_s)

            if last_err:
                logger.error(f"Gemini 请求异常: {last_err}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Gemini 请求异常: {e}", exc_info=True)
            return None


class GeminiCloubicClient:
    """Gemini 第三方 REST 客户端（Cloubic 代理）。

    兼容 curl 示例：
    POST https://api.cloubic.com/v1beta/models/{model}:generateContent?key=API_KEY
    body: {"contents":[{"parts":[{"text":"..."}]}]}

    说明：只支持纯文本（把 OpenAI-style messages 压成一段文本）。
    """

    def __init__(self, api_key: str, base_url: str = "https://api.cloubic.com"):
        if not api_key:
            raise ValueError("Cloubic API key 不能为空")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

        try:
            import requests  # type: ignore

            self._requests = requests
        except Exception as e:
            logger.error(f"requests 未安装或导入失败，无法调用 Cloubic REST。错误: {e}", exc_info=True)
            raise

    def _extract_text(self, resp_json: dict) -> str:
        # Gemini REST: candidates[0].content.parts[*].text
        candidates = (resp_json or {}).get("candidates") or []
        if not candidates:
            return ""

        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        texts: list[str] = []
        for p in parts:
            t = (p or {}).get("text")
            if t:
                texts.append(str(t))
        return "".join(texts).strip()

    def chat(self, _model: str, _messages: List[Dict[str, str]], timeout_seconds: int = 120, **kwargs) -> Optional[Dict[Any, Any]]:
        logger.info(f"使用Gemini模型进行聊天(Cloubic REST): {_model}")

        contents = _messages_to_plaintext(_messages)
        if not contents.strip():
            return {
                "model": _model,
                "choices": [{"message": {"content": ""}}],
                "usage": {},
            }

        url = f"{self.base_url}/v1beta/models/{_model}:generateContent"
        params = {"key": self.api_key}
        payload = {
            "contents": [
                {
                    "parts": [{"text": contents}],
                }
            ]
        }

        # 最简单实现：不做复杂重试策略，失败直接返回 None
        try:
            resp = self._requests.post(
                url,
                params=params,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
            if resp.status_code >= 400:
                logger.error(f"Cloubic Gemini REST 请求失败: status={resp.status_code}, body={resp.text[:800]}")
                return None

            data = resp.json()
            text = self._extract_text(data)
            return {
                "model": _model,
                "choices": [{"message": {"content": text}}],
                "usage": {},
            }
        except Exception as e:
            logger.error(f"Cloubic Gemini REST 请求异常: {e}", exc_info=True)
            return None


class QwenClient(ChatModelClient):
    """Qwen模型客户端"""

    def __init__(self, api_key: str):
        """
        初始化Qwen模型客户端

        Args:
            api_key (str): DashScope API密钥
        """
        super().__init__(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def chat(self, _model: str, _messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[Any, Any]]:
        """
        Qwen模型聊天

        Args:
            _model (str): 模型名称
            _messages (List[Dict[str, str]]): 消息列表
            **kwargs: 其他参数

        Returns:
            Optional[Dict[Any, Any]]: 响应数据，失败时返回None
        """
        logger.info(f"使用Qwen模型进行聊天: {_model}")

        return self.chat_completion(_model, _messages, **kwargs)


class DeepSeekClient(ChatModelClient):
    """DeepSeek模型客户端（通过阿里云百炼调用）"""

    def __init__(self, api_key: str):
        """
        初始化DeepSeek模型客户端（使用阿里云百炼代理）

        Args:
            api_key (str): DashScope API密钥（阿里云百炼）
        """
        super().__init__(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def chat(self, _model: str, _messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[Any, Any]]:
        """
        DeepSeek模型聊天（通过阿里云百炼）

        Args:
            _model (str): 模型名称（如 deepseek-v3.2-exp, deepseek-r1）
            _messages (List[Dict[str, str]]): 消息列表
            **kwargs: 其他参数，如 extra_body={"enable_thinking": True}

        Returns:
            Optional[Dict[Any, Any]]: 响应数据，失败时返回None
        """
        logger.info(f"使用DeepSeek模型进行聊天（通过阿里云百炼）: {_model}")

        return self.chat_completion(_model, _messages, **kwargs)


def chat_with_model(api_key: str, model_type: str, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
    """
    通用聊天函数

    Args:
        api_key (str): API密钥
        model_type (str): 模型类型 ('qwen', 'deepseek', 'openai', 'gemini', 'gemini_cloubic')
        model (str): 模型名称
        messages (List[Dict[str, str]]): 消息列表
        **kwargs: 模型特定参数

    Returns:
        Optional[str]: 模型回答内容，失败时返回None
    """
    start_time = time.time()
    logger.info(f"任务开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    # 根据模型类型选择客户端
    if model_type == "qwen":
        client = QwenClient(api_key)
        result = client.chat(model, messages, **kwargs)
    elif model_type == "deepseek":
        # 通过阿里云百炼调用 DeepSeek（推荐）
        client = DeepSeekClient(api_key)
        result = client.chat(model, messages, **kwargs)
    elif model_type == "gemini":
        client = GeminiClient(api_key)
        try:
            result = client.chat(model, messages, **kwargs)
        finally:
            # google-genai 可能会启动后台线程/连接，显式 close 避免主流程结束后进程不退出
            try:
                inner = getattr(client, "client", None)
                close_fn = getattr(inner, "close", None)
                if callable(close_fn):
                    close_fn()
            except Exception:
                # close 失败不影响主流程
                pass
    elif model_type == "gemini_cloubic":
        client = GeminiCloubicClient(api_key)
        result = client.chat(model, messages, **kwargs)
    else:
        logger.error(f"不支持的模型类型: {model_type}")
        return None

    end_time = time.time()
    duration = end_time - start_time

    logger.info(f"任务结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    logger.info(f"任务总耗时: {duration:.2f}秒")

    if result:
        # 提取回答内容
        answer_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        reasoning_content = result.get("choices", [{}])[0].get("message", {}).get("reasoning_content", "")

        # 提取使用信息
        usage = result.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        # 提取模型信息
        model_used = result.get("model", "")

        # 记录详细信息
        logger.info(f"{model}任务完成 - 耗时: {duration:.2f}秒")
        logger.info(f"使用模型: {model_used}")
        logger.info(f"消耗Token - 提示词: {prompt_tokens}, 回答: {completion_tokens}, 总计: {total_tokens}")
        logger.info(f"推理过程: {reasoning_content}")
        logger.info(f"模型回答: {answer_content}")

        # Debug打印原始JSON结构
        logger.debug(f"原始响应JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")

        return answer_content
    else:
        logger.error(f"{model}任务失败 - 耗时: {duration:.2f}秒")
        return None


if __name__ == "__main__":
    from config.logging_config import setup_logging, get_logger
    import data.test_prompt as prompt

    # 项目启动时初始化日志
    setup_logging()

    # logger.info("📋 初始化配置参数")
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))

    # 测试Qwen模型
    api_key = os.getenv("GEMINI_API_KEY")  # DASHSCOPE_API_KEY
    # dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 未配置")

    messages = [
        {
            "role": "system",
            "content": prompt.test_i2v_prompt_sync_prompt_001,
        },
        {
            "role": "system",
            "content": "生成一个:从天上浇下一桶水,把角色的身上全部淋湿,角色非常狼狈的提示词",
        }
    ]

    # res = chat_with_model(
    #     api_key=api_key,
    #     messages=messages,
    #     model_type="qwen",
    #     model="qwen-max",
    #     extra_body={"enable_thinking": True},
    # )
    res = chat_with_model(
        api_key=api_key,  # 可以留空；如果 env/default.env 里有 GEMINI_API_KEY 且已 load_dotenv，就能读到
        model_type="gemini",
        model="gemini-3-pro-preview",
        messages=messages,
    )
    # res = chat_with_model(
    #     api_key=dashscope_api_key,
    #     messages=messages,
    #     model_type="deepseek",
    #     model="deepseek-r1",
    # )
    time.sleep(5)
    print(f"模型答案:{res}")

