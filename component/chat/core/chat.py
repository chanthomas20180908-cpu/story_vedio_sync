"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 消息、会话上下文
Output: 响应结果
Pos: 聊天核心逻辑
"""

# file: /Users/thomaschan/Code/Python/AI_vedio_demo/pythonProject/component/chat.py
import sys
import os

import json
import time
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from config.logging_config import get_logger

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 项目启动时初始化日志
logger = get_logger(__name__)


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
            Optional[Dict[Any, Any]]: 响应数据，失败时返回包含错误信息的字典
        """
        try:
            # # 添加默认参数
            # extra_body = kwargs.get("extra_body", {})

            completion = self.client.chat.completions.create(
                model=_model,
                messages=_messages,
                # extra_body=extra_body,
                **kwargs
            )

            return completion.model_dump()
        except Exception as e:
            logger.error(f"聊天补全请求异常: {e}", exc_info=True)
            
            # 返回错误信息而不是 None
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 特殊处理内容审查错误
            if 'data_inspection_failed' in error_msg or 'inappropriate content' in error_msg.lower():
                return {
                    "error": {
                        "type": "content_inspection_failed",
                        "message": "输入内容包含不适当的内容，已被阻止。请修改您的输入后重试。",
                        "original_error": error_msg
                    }
                }
            
            # 其他错误
            return {
                "error": {
                    "type": error_type,
                    "message": error_msg,
                    "original_error": error_msg
                }
            }


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


class OpenAIClient(ChatModelClient):
    """OpenAI模型客户端"""

    def __init__(self, api_key: str):
        """
        初始化OpenAI模型客户端

        Args:
            api_key (str): OpenAI API密钥
        """
        super().__init__(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )

    def chat(self, _model: str, _messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[Any, Any]]:
        """
        OpenAI模型聊天

        Args:
            _model (str): 模型名称
            _messages (List[Dict[str, str]]): 消息列表
            **kwargs: 其他参数

        Returns:
            Optional[Dict[Any, Any]]: 响应数据，失败时返回None
        """
        logger.info(f"使用OpenAI模型进行聊天: {_model}")

        return self.chat_completion(_model, _messages, **kwargs)


def chat_with_model(api_key: str, model_type: str, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
    """
    通用聊天函数

    Args:
        api_key (str): API密钥
        model_type (str): 模型类型 ('qwen', 'deepseek', 'deepseek_direct', 'openai')
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
    elif model_type == "openai":
        client = OpenAIClient(api_key)
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
        logger.info(f"模型回答: {answer_content}")

        # Debug打印原始JSON结构
        logger.debug(f"原始响应JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")

        return answer_content
    else:
        logger.error(f"{model}任务失败 - 耗时: {duration:.2f}秒")
        return None


if __name__ == "__main__":
    from config.logging_config import setup_logging
    import data.test_prompt as prompt

    # 项目启动时初始化日志
    setup_logging()

    logger.info("📋 初始化配置参数")
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))

    # 测试Qwen模型
    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    # dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")

    messages = [
        {
            "role": "system",
            "content": prompt.TEST_PROMPT_SYSTEM_001,
        },
        {
            "role": "system",
            "content": prompt.TEST_PROMPT_SYSTEM_008,
        },
        {
            "role": "user",
            "content": prompt.TEST_PROMPT_USER_001,
        }
    ]

    res = chat_with_model(
        api_key=dashscope_api_key,
        messages=messages,
        model_type="qwen",
        model="qwen-plus",
        # extra_body={"enable_thinking": True},
    )
    # res = chat_with_model(
    #     api_key=dashscope_api_key,
    #     messages=messages,
    #     model_type="deepseek",
    #     model="deepseek-r1",
    # )
    time.sleep(5)
    print(f"模型答案:{res}")

