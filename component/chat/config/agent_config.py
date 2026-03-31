#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 无
Output: Agent配置参数
Pos: Agent配置中心
"""

"""
Agent 配置文件
统一管理 Agent 的各项配置
"""
from enum import Enum
from pathlib import Path


class ToolProtocol(Enum):
    """工具协议类型"""
    FUNCTION_CALL = "function_call"  # OpenAI Function Calling
    MCP = "mcp"  # Model Context Protocol


class AgentMode(Enum):
    """Agent 工作模式"""
    PURE = "pure"        # 纯对话，不使用任何工具
    KB_ONLY = "kb"       # 仅知识库
    WEB_ONLY = "web"     # 仅网络访问
    FULL = "full"        # 全功能（知识库+网络）


class AgentConfig:
    """Agent 配置类"""
    
    # ========== 工具协议配置 ==========
    TOOL_PROTOCOL = ToolProtocol.FUNCTION_CALL  # 当前使用的协议
    
    # ========== 默认模式 ==========
    DEFAULT_MODE = AgentMode.FULL  # 默认启用全功能
    
    # ========== 系统提示词配置 ==========
    DEFAULT_SYSTEM_PROMPT_TYPE = "product_expert"  # 默认使用产品专家提示词
    ENABLE_SYSTEM_PROMPT = True  # 是否启用系统提示词
    
    # ========== 模型配置 ==========
    DEFAULT_MODEL_TYPE = "qwen"
    DEFAULT_MODEL = "qwen-plus"
    
    # 支持的模型列表
    SUPPORTED_MODELS = {
        "qwen": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-flash"],
        "deepseek": ["deepseek-v3", "deepseek-v3.1", "deepseek-v3.2-exp", "deepseek-r1"],
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    }
    
    # ========== 工具配置 ==========
    # Function Calling 工具最大调用轮数
    MAX_TOOL_ITERATIONS = 20
    
    # ========== MCP 配置（预留） ==========
    MCP_SERVERS = {
        "knowledge_base": {
            "command": "python",
            "args": ["-m", "component.chat.tools.kb_mcp_server"],
            "env": {}
        },
        "web_access": {
            "command": "python",
            "args": ["-m", "component.chat.tools.web_mcp_server"],
            "env": {}
        }
    }
    
    # ========== 知识库配置 ==========
    # 知识库根目录（使用规则中定义的路径）
    KNOWLEDGE_BASE_ROOT = Path("/Users/test/Code/Python/AI_vedio_demo/pythonProject/data/knowledge_base")
    
    # 支持的文件扩展名
    SUPPORTED_FILE_EXTENSIONS = [".txt", ".md", ".json", ".csv", ".log"]
    
    # ========== 网络访问配置 ==========
    WEB_REQUEST_TIMEOUT = 10  # 网络请求超时时间（秒）
    WEB_MAX_CONTENT_LENGTH = 50000  # 网页内容最大长度
    
    # 默认网络查询模式
    DEFAULT_WEB_SEARCH_MODE = "technical"  # technical/product/ai_news/comprehensive
    
    # 是否强制使用配置的模式（不允许LLM覆盖）
    FORCE_WEB_SEARCH_MODE = True  # True=强制使用配置模式, False=允许LLM智能选择
    
    # 支持的网络查询模式
    SUPPORTED_WEB_MODES = {
        "technical": "技术文档和开源项目（GitHub、HuggingFace、arXiv）",
        "product": "产品理论和方法论（人人都是产品经理、36氪、知乎）",
        "ai_news": "AI行业资讯和研究（机器之心、量子位、AIbase）",
        "comprehensive": "综合查询（包含所有类型）",
        "auto": "LLM智能选择（根据问题自动匹配最佳模式）"
    }
    
    # ========== 交互界面配置 ==========
    # 是否显示工具调用摘要
    SHOW_TOOL_SUMMARY = True
    
    # 是否显示思考过程（仅支持 DeepSeek R1 等模型）
    SHOW_THINKING = True
    
    # 是否显示 Token 使用统计
    SHOW_TOKEN_STATS = True
    
    # ========== 会话管理配置 ==========
    # 会话数据库路径
    SESSION_DB_PATH = Path("data/Data_results/chat_sessions.db")
    
    # 自动保存间隔（秒）
    AUTO_SAVE_INTERVAL = 60
    
    # 上下文窗口大小（tokens）
    CONTEXT_WINDOW_SIZE = 8000
    
    # ========== 辅助方法 ==========
    @classmethod
    def get_mode_config(cls, mode: AgentMode) -> dict:
        """
        根据模式获取工具启用配置
        
        Args:
            mode: Agent 工作模式
            
        Returns:
            工具配置字典 {enable_kb: bool, enable_web: bool}
        """
        config_map = {
            AgentMode.PURE: {"enable_kb": False, "enable_web": False},
            AgentMode.KB_ONLY: {"enable_kb": True, "enable_web": False},
            AgentMode.WEB_ONLY: {"enable_kb": False, "enable_web": True},
            AgentMode.FULL: {"enable_kb": True, "enable_web": True},
        }
        return config_map.get(mode, {"enable_kb": True, "enable_web": True})
    
    @classmethod
    def is_mcp_enabled(cls) -> bool:
        """检查是否启用 MCP 协议"""
        return cls.TOOL_PROTOCOL == ToolProtocol.MCP
    
    @classmethod
    def validate_model(cls, model_type: str, model: str) -> bool:
        """
        验证模型配置是否有效
        
        Args:
            model_type: 模型类型
            model: 模型名称
            
        Returns:
            是否有效
        """
        if model_type not in cls.SUPPORTED_MODELS:
            return False
        return model in cls.SUPPORTED_MODELS[model_type]


# 导出常用配置
DEFAULT_MODE = AgentConfig.DEFAULT_MODE
DEFAULT_MODEL_TYPE = AgentConfig.DEFAULT_MODEL_TYPE
DEFAULT_MODEL = AgentConfig.DEFAULT_MODEL
KNOWLEDGE_BASE_ROOT = AgentConfig.KNOWLEDGE_BASE_ROOT
