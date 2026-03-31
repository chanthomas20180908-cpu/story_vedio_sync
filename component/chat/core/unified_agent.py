#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 用户请求、工具集
Output: Agent执行结果
Pos: 统一Agent核心实现
"""

"""
统一 Agent - 集成知识库和网络访问功能
支持 Function Calling 协议，预留 MCP 扩展接口
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from component.chat.core.chat import QwenClient, DeepSeekClient, OpenAIClient
from component.chat.tools.kb_tools import KnowledgeBaseTools
from component.chat.tools.web_tools import WebTools
from component.chat.config.agent_config import AgentConfig, AgentMode
from component.chat.config.system_prompts import SystemPrompts
from config.logging_config import get_logger

logger = get_logger(__name__)


class UnifiedAgent:
    """
    统一 Agent - 业务逻辑层
    
    职责:
    - AI 模型调用
    - Function Calling 处理
    - 工具编排与执行
    - 多轮工具调用逻辑
    - Token 计数与统计
    """
    
    # 知识库工具定义
    KB_TOOL_DEFINITIONS = [
        {
            "type": "function",
            "function": {
                "name": "list_documents",
                "description": "列出知识库中的文档。\n\n使用场景：\n1. 探索目录结构，了解有哪些文档\n2. 根据用户说的关键词（如'淘宝'、'京东'），使用pattern过滤文件\n3. 先列出文件，再决定读取哪个\n\n智能提示：\n- 如果用户问'淘宝XXX的文档'，应该使用 pattern='*淘宝*' 来过滤\n- 如果用户问'竞品分析'，应该先 list_documents(directory='avater/竞品分析')\n- 支持递归搜索，会自动查找子目录",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "子目录路径，如 'avater/竞品分析'。留空表示根目录。支持递归搜索子目录。"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回文档数量上限，默认 50"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "文件名匹配模式，如 '*.md' 或 '*淘宝*' 或 '*竞品*'。默认 '*' （匹配所有文件）。可使用中文关键词过滤。"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_document",
                "description": "读取知识库中的文档内容。支持文本文件和PDF文件（自动OCR识别）。\n\n智能提示：\n- 支持模糊匹配：如果只知道文件名部分，直接使用部分名称即可\n- 例如：'淘宝竞品报告' 会自动匹配 '淘宝AI直播竞品综合分析报告_合并版.md'\n- 如果不确定完整路径，先用 list_documents 确认",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "文件路径（相对于知识库根目录）。支持完整路径和部分文件名：\n- 完整路径：'avater/竞品分析/淘宝竞品报告.md'\n- 部分名称：'淘宝竞品报告' 或 '淘宝竞品报告.md'"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "最大读取字符数，默认 10000。PDF文件建议设置为 50000。"
                        }
                    },
                    "required": ["filepath"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_document",
                "description": "在知识库中创建新文档。\n\n重要提示：\n1. filepath 是相对于知识库根目录的路径\n2. 如果用户说'同目录下'，需要先确定当前操作文档的目录，然后使用完整路径\n3. 例如：读取 'avater/doc.md' 后要在同目录创建文件，应该用 'avater/new_file.md'\n\n⚠️ 严重警告 - JSON格式问题：\n- 避免创建包含复杂Markdown表格的文档（容易导致JSON解析失败）\n- 内容超过3000字时，建议分步创建或使用简洁格式\n- 推荐格式：使用列表、标题、段落，避免多列表格\n- 如需表格，使用简单的2-3列表格，或改用列表展示\n- 建议：先创建简化版本，验证成功后再逐步丰富",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "文件路径（相对于知识库根目录），如 'avater/file.md' 或 'project/docs/readme.txt'。如果用户指定'同目录'，必须包含完整的目录路径。"
                        },
                        "content": {
                            "type": "string",
                            "description": "文档内容。注意：内容过长（>5000字）可能导致JSON解析失败，建议分步创建。"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "是否覆盖已存在的文件，默认 false"
                        }
                    },
                    "required": ["filepath", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_in_documents",
                "description": "在知识库文档中搜索关键词。返回包含该关键词的文件列表和匹配位置。\n\n注意：\n- 不支持直接搜索PDF文件（会自动跳过）\n- 如需搜索PDF内容，应先用 read_document 读取PDF，然后在返回的文本中搜索\n- 搜索文件名应使用 list_documents 的 pattern 参数",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如 '淘宝' 或 'AI直播' 或 '竞品分析'"
                        },
                        "directory": {
                            "type": "string",
                            "description": "搜索目录，如 'avater/竞品分析'。留空则搜索整个知识库。建议指定目录以提高搜索效率。"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量上限，默认 10"
                        }
                    },
                    "required": ["keyword"]
                }
            }
        },
    ]
    
    # 网络访问工具定义
    WEB_TOOL_DEFINITIONS = [
        {
            "type": "function",
            "function": {
                "name": "suggest_url",
                "description": "【必须先调用】根据关键词和查询模式智能推荐访问URL。这个工具会返回最适合的网站URL，你必须使用返回的URL进行后续访问。\n\n⚠️ 重要：必须根据用户需求选择正确的mode参数！\n\n📌 MODE选择规则（必读）：\n\n当用户提到以下关键词时，必须使用对应模式：\n\n1. **technical模式** - 技术调研\n   触发词：'技术文档'、'开源项目'、'API'、'GitHub'、'模型'、'算法'\n   平台：GitHub、HuggingFace、arXiv、Papers with Code\n   示例：'qwen3', 'langchain', 'stable-diffusion'\n\n2. **product模式** - 产品调研\n   触发词：'PRODUCT_PLATFORMS'、'产品分析'、'竞品'、'用户增长'、'商业模式'\n   平台：人人都是产品经理、36氪、PMCaff、知乎\n   示例：'用户增长', '产品设计', 'MVP方法'\n\n3. **ai_news模式** - AI资讯\n   触发词：'AI_NEWS'、'AI产品'、'AI新闻'、'行业动态'、'AI资讯'\n   平台：机器之心、量子位、AIbase、观猹、toolify.ai、ProductHunt\n   示例：'AI新闻', '大模型发展', 'AI产品调研'\n\n4. **comprehensive模式** - 全面调研\n   触发词：'全面调研'、'comprehensive'\n   包含所有平台\n\n🔴 必须遵守：\n- 用户说'PRODUCT_PLATFORMS' → mode='product'\n- 用户说'AI_NEWS' → mode='ai_news'\n- 技术问题 → mode='technical'\n- 产品/增长问题 → mode='product'\n- AI行业资讯 → mode='ai_news'\n\n✅ 正确使用流程：\n1. 调用 suggest_url(keyword, mode=<正确模式>) 获取推荐URL\n2. 使用返回的 suggested_url 字段作为下一步访问的目标\n3. 调用 fetch_dynamic_url(返回的URL) 或 fetch_url(返回的URL)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词。技术名称（'qwen3'）、产品概念（'用户增长'）、或资讯主题（'AI新闻'）"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["technical", "product", "ai_news", "comprehensive"],
                            "description": "⚠️必选！查询模式（根据用户需求选择）：\n- technical: 技术调研（GitHub、HuggingFace、arXiv）\n- product: 产品调研（人人都是产品经理、36氪、PMCaff）- 用户提到'PRODUCT_PLATFORMS'时必选\n- ai_news: AI资讯（机器之心、量子位、AIbase）- 用户提到'AI_NEWS'时必选\n- comprehensive: 综合查询"
                        }
                    },
                    "required": ["keyword", "mode"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "访问网页并获取内容。用于查询网站信息、阅读文章等。建议先使用suggest_tech_url获取推荐URL再访问。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标网页URL，如 'https://example.com'"
                        },
                        "extract_main": {
                            "type": "boolean",
                            "description": "是否只提取主要内容（去除导航、广告等），默认 true"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_page_summary",
                "description": "获取网页摘要（前几段内容）。适合快速了解网页大致内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标网页URL"
                        },
                        "max_paragraphs": {
                            "type": "integer",
                            "description": "最大段落数，默认 5"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_in_page",
                "description": "在网页中搜索关键词并返回匹配上下文。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标网页URL"
                        },
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "context_chars": {
                            "type": "integer",
                            "description": "上下文字符数，默认 200"
                        }
                    },
                    "required": ["url", "keyword"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_dynamic_url",
                "description": "访问动态网页（支持JavaScript渲染）。用于爆取需要浏览器渲染的电商页面、SPA应用等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标网页URL"
                        },
                        "wait_time": {
                            "type": "integer",
                            "description": "等待页面加载时间（秒），默认 3秒"
                        },
                        "extract_main": {
                            "type": "boolean",
                            "description": "是否只提取主要内容，默认 true"
                        },
                        "scroll_to_bottom": {
                            "type": "boolean",
                            "description": "是否滚动到页面底部（触发懒加载），默认 true"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
    ]
    
    def __init__(
        self, 
        api_key: str, 
        model_type: str = None,
        model: str = None,
        mode: AgentMode = None,
        enable_kb: bool = None,
        enable_web: bool = None,
        kb_root: Path = None,
        kb_working_dir: str = None,
        system_prompt_type: str = None,
        enable_system_prompt: bool = None,
        web_search_mode: str = None
    ):
        """
        初始化统一 Agent
        
        Args:
            api_key: API 密钥
            model_type: 模型类型 (qwen/deepseek/openai)
            model: 具体模型名称
            mode: Agent 工作模式（优先级高于 enable_kb/enable_web）
            enable_kb: 是否启用知识库工具（mode 为 None 时生效）
            enable_web: 是否启用网络工具（mode 为 None 时生效）
            kb_root: 知识库根目录
            kb_working_dir: 知识库工作目录（相对于kb_root的子目录），限制文件访问范围
            system_prompt_type: 系统提示词类型，默认 "product_expert"
            enable_system_prompt: 是否启用系统提示词，默认 True
            web_search_mode: 网络查询模式 (technical/product/ai_news/comprehensive)，默认使用配置
        """
        self.api_key = api_key
        
        # 模型配置
        self.model_type = model_type or AgentConfig.DEFAULT_MODEL_TYPE
        self.model = model or AgentConfig.DEFAULT_MODEL
        
        # 验证模型配置
        if not AgentConfig.validate_model(self.model_type, self.model):
            logger.warning(f"模型配置无效: {self.model_type}/{self.model}，使用默认配置")
            self.model_type = AgentConfig.DEFAULT_MODEL_TYPE
            self.model = AgentConfig.DEFAULT_MODEL
        
        # 工具配置
        if mode:
            # 根据模式自动配置工具
            tool_config = AgentConfig.get_mode_config(mode)
            self.enable_kb = tool_config["enable_kb"]
            self.enable_web = tool_config["enable_web"]
        else:
            # 手动配置工具
            self.enable_kb = enable_kb if enable_kb is not None else True
            self.enable_web = enable_web if enable_web is not None else True
        
        # 初始化 AI 客户端
        if self.model_type == "qwen":
            self.client = QwenClient(api_key)
        elif self.model_type == "deepseek":
            self.client = DeepSeekClient(api_key)
        elif self.model_type == "openai":
            self.client = OpenAIClient(api_key)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
        
        # 系统提示词配置
        self.enable_system_prompt = enable_system_prompt if enable_system_prompt is not None else AgentConfig.ENABLE_SYSTEM_PROMPT
        self.system_prompt_type = system_prompt_type or AgentConfig.DEFAULT_SYSTEM_PROMPT_TYPE
        self.system_prompt = SystemPrompts.get_prompt(self.system_prompt_type) if self.enable_system_prompt else None
        
        # 初始化工具
        self.kb_working_dir = kb_working_dir  # 保存以便后续使用
        self.kb_tools = KnowledgeBaseTools(kb_root, kb_working_dir) if self.enable_kb else None
        self.web_tools = WebTools() if self.enable_web else None
        
        # 网络查询模式配置
        self.web_search_mode = web_search_mode or AgentConfig.DEFAULT_WEB_SEARCH_MODE
        if self.web_search_mode not in AgentConfig.SUPPORTED_WEB_MODES:
            logger.warning(f"不支持的网络查询模式: {self.web_search_mode}，使用默认模式")
            self.web_search_mode = AgentConfig.DEFAULT_WEB_SEARCH_MODE
        
        # 日志信息
        kb_info = ''
        if self.enable_kb:
            if kb_working_dir:
                kb_info = f"✓ (限制: {kb_working_dir})"
            else:
                kb_info = '✓'
        else:
            kb_info = '✗'
        
        logger.info(f"统一 Agent 初始化 - 模型: {self.model_type}/{self.model}, "
                   f"知识库: {kb_info}, "
                   f"网络: {'✓' if self.enable_web else '✗'}, "
                   f"网络查询模式: {self.web_search_mode if self.enable_web else 'N/A'}, "
                   f"系统提示词: {self.system_prompt_type if self.enable_system_prompt else '无'}")
    
    def _get_available_tools(self) -> List[Dict]:
        """
        获取当前可用的工具列表
        
        Returns:
            工具定义列表
        """
        tools = []
        
        if self.enable_kb:
            # 如果设置了工作目录，需要调整工具描述
            kb_tools = []
            for tool_def in self.KB_TOOL_DEFINITIONS:
                tool_copy = json.loads(json.dumps(tool_def))  # 深复制
                
                if self.kb_working_dir:
                    # 添加工作目录提示到描述中
                    func_name = tool_copy["function"]["name"]
                    original_desc = tool_copy["function"]["description"]
                    
                    # 在描述开头添加工作目录提示
                    prefix = f"⚠️ 当前工作目录: '{self.kb_working_dir}'\n所有文件路径都是相对于工作目录的。\n\n❗ 重要：\n- 不需要在路径前加 '{self.kb_working_dir}/' 前缀\n- 例如：直接使用 'medeo_锐评版.md' 而不是 '{self.kb_working_dir}/medeo_锐评版.md'\n- 如果有子目录，使用 'AI产品体验/medeo/medeo_draft.md'\n\n"
                    tool_copy["function"]["description"] = prefix + original_desc
                    
                    # 更新 filepath 参数的描述
                    if func_name in ["read_document", "create_document"]:
                        if "filepath" in tool_copy["function"]["parameters"]["properties"]:
                            tool_copy["function"]["parameters"]["properties"]["filepath"]["description"] = f"文件路径（相对于工作目录 '{self.kb_working_dir}'）。\n- 直接使用: 'file.md' 或 'subdir/file.md'\n- 不要加前缀: '{self.kb_working_dir}/file.md' ❌"
                    
                    # 更新 directory 参数的描述
                    if func_name in ["list_documents", "search_in_documents"]:
                        if "directory" in tool_copy["function"]["parameters"]["properties"]:
                            tool_copy["function"]["parameters"]["properties"]["directory"]["description"] = f"子目录路径（相对于工作目录 '{self.kb_working_dir}'）。留空表示工作目录根部。"
                
                kb_tools.append(tool_copy)
            
            tools.extend(kb_tools)
        
        if self.enable_web:
            tools.extend(self.WEB_TOOL_DEFINITIONS)
        
        return tools
    
    def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        执行工具函数
        
        Args:
            function_name: 函数名
            arguments: 函数参数
            
        Returns:
            执行结果
        """
        # suggest_url模式处理
        if function_name == "suggest_url":
            # 情凵1: 强制模式 - 始终使用配置的模式，忽略LLM的选择
            if AgentConfig.FORCE_WEB_SEARCH_MODE and self.web_search_mode != "auto":
                if "mode" in arguments and arguments["mode"] != self.web_search_mode:
                    logger.info(f"强制模式已启用，将LLM选择的'{arguments['mode']}'覆盖为'{self.web_search_mode}'")
                arguments["mode"] = self.web_search_mode
            # 情凵2: auto模式 - 允许LLM智能选择，但如果LLM没指定则使用technical作为默认
            elif self.web_search_mode == "auto":
                if "mode" not in arguments:
                    arguments["mode"] = "technical"  # 默认值
                    logger.info(f"auto模式：LLM未指定mode，使用默认值'technical'")
                else:
                    logger.info(f"auto模式：使用LLM选择的模式'{arguments['mode']}'")
            # 情凵3: 非强制且非auto - 仅在LLM未指定时注入
            elif "mode" not in arguments:
                arguments["mode"] = self.web_search_mode
                logger.info(f"自动注入网络查询模式: {self.web_search_mode}")
        
        logger.info(f"执行工具: {function_name}, 参数: {arguments}")
        
        # 知识库工具
        if self.kb_tools and hasattr(self.kb_tools, function_name):
            method = getattr(self.kb_tools, function_name)
            result = method(**arguments)
            logger.info(f"知识库工具执行完成: {result.get('success', False)}")
            return result
        
        # 网络工具
        elif self.web_tools and hasattr(self.web_tools, function_name):
            method = getattr(self.web_tools, function_name)
            result = method(**arguments)
            logger.info(f"网络工具执行完成: {result.get('success', False)}")
            return result
        
        else:
            error_msg = f"未知的工具函数: {function_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def chat(
        self, 
        user_input: str, 
        conversation_history: List[Dict] = None,
        max_iterations: int = None,
        interactive: bool = False,
        on_max_iterations: callable = None
    ) -> Dict[str, Any]:
        """
        处理用户输入（带 Function Calling，支持多轮工具调用）
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            max_iterations: 最大工具调用轮数
            interactive: 是否启用交互模式（达到 max_iterations 时询问用户）
            on_max_iterations: 达到 max_iterations 时的回调函数，返回 True 继续执行
            
        Returns:
            {
                "answer": str,           # 最终回答
                "tool_called": bool,     # 是否调用了工具
                "tool_calls": List[Dict],# 所有工具调用记录
                "iterations": int,       # 实际迭代次数
                "usage": Dict,           # Token 使用统计
                "response": Dict,        # 原始 API 响应
                "continued": bool        # 是否在达到限制后继续执行
            }
        """
        if conversation_history is None:
            conversation_history = []
        
        if max_iterations is None:
            max_iterations = AgentConfig.MAX_TOOL_ITERATIONS
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示词（如果启用）
        if self.system_prompt:
            system_content = self.system_prompt
            
            # 如果设置了工作目录，添加特别说明
            if self.kb_working_dir and self.enable_kb:
                kb_instruction = f"\n\n📌 重要提示 - 知识库工作目录：\n当前你只能访问 '{self.kb_working_dir}' 目录下的文件。\n所有知识库工具的文件路径都是相对于这个目录的。\n\n⚠️ 注意：\n- 不要在路径前加 '{self.kb_working_dir}/' 前缀\n- 直接使用: 'file.md' 或 'subdir/file.md'\n- 错误示例: '{self.kb_working_dir}/file.md' ❌"
                system_content += kb_instruction
            
            messages.append({"role": "system", "content": system_content})
        
        # 添加对话历史和用户输入
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        
        # 获取可用工具
        available_tools = self._get_available_tools()
        
        # 记录所有工具调用
        all_tool_calls = []
        
        try:
            iteration = 0
            
            # 如果没有工具，直接调用模型
            if not available_tools:
                response = self.client.chat(
                    _model=self.model,
                    _messages=messages
                )
                
                # 检查响应是否包含错误
                if response is None or "error" in response:
                    error_info = response.get("error", {}) if response else {"message": "API 调用失败"}
                    error_type = error_info.get("type", "unknown")
                    error_message = error_info.get("message", "未知错误")
                    
                    logger.error(f"API 调用错误: {error_type} - {error_message}")
                    
                    # 返回用户友好的错误信息
                    if error_type == "content_inspection_failed":
                        return {
                            "answer": "⚠️ 您的输入包含敏感内容，已被安全审查系统阻止。\n\n请修改您的问题，避免包含：\n- 违法违规内容\n- 暴力、色情等不适当内容\n- 政治敏感话题\n\n然后重新提问。",
                            "tool_called": False,
                            "tool_calls": [],
                            "iterations": 1,
                            "usage": {},
                            "error": error_message
                        }
                    else:
                        return {
                            "answer": f"❌ 处理您的请求时发生错误: {error_message}\n\n请稍后重试或联系管理员。",
                            "tool_called": False,
                            "tool_calls": [],
                            "iterations": 1,
                            "usage": {},
                            "error": error_message
                        }
                
                assistant_message = response.get("choices", [{}])[0].get("message", {})
                return {
                    "answer": assistant_message.get("content", ""),
                    "tool_called": False,
                    "tool_calls": [],
                    "iterations": 1,
                    "usage": response.get("usage", {}),
                    "response": response
                }
            
            # 带工具的多轮调用
            continued_execution = False
            original_max_iterations = max_iterations
            
            while True:
                # 检查是否达到当前限制
                if iteration >= max_iterations:
                    logger.warning(f"达到最大迭代次数 {max_iterations}")
                    
                    # 交互模式：询问用户是否继续
                    if interactive or on_max_iterations:
                        should_continue = False
                        
                        if on_max_iterations:
                            # 使用回调函数
                            should_continue = on_max_iterations({
                                "iterations": iteration,
                                "max_iterations": max_iterations,
                                "tool_calls": all_tool_calls,
                                "messages": messages
                            })
                        elif interactive:
                            # 默认交互：询问用户
                            print(f"\n⚠️  已达到最大迭代次数 {max_iterations}")
                            print(f"已执行 {len(all_tool_calls)} 个工具调用，任务尚未完成。")
                            print("\n选项:")
                            print("  1. 继续执行 (增加 10 次迭代)")
                            print("  2. 继续执行 (增加 20 次迭代)")
                            print("  3. 取消限制，完全执行")
                            print("  4. 停止执行，返回当前结果")
                            
                            choice = input("\n请选择 (1-4, 默认4): ").strip() or "4"
                            
                            if choice == "1":
                                max_iterations += 10
                                should_continue = True
                                print(f"✅ 继续执行，新限制: {max_iterations} 次\n")
                            elif choice == "2":
                                max_iterations += 20
                                should_continue = True
                                print(f"✅ 继续执行，新限制: {max_iterations} 次\n")
                            elif choice == "3":
                                max_iterations = float('inf')
                                should_continue = True
                                print("✅ 已取消限制，将完全执行任务\n")
                            else:
                                should_continue = False
                                print("❌ 停止执行\n")
                        
                        if should_continue:
                            continued_execution = True
                            # 继续循环
                        else:
                            # 停止执行，但让LLM基于已收集的信息生成总结
                            logger.info(f"用户选择停止执行，已收集 {len(all_tool_calls)} 个工具调用结果，让LLM生成总结")
                            
                            # 添加一个特殊指令，让LLM基于当前信息生成回答
                            summary_instruction = {
                                "role": "user",
                                "content": f"请基于已收集的信息（{len(all_tool_calls)}个工具调用结果）生成一个总结性回答。\n\n即使信息不完整，也请尽量基于现有数据给出有价值的分析和建议。\n\n请直接给出答案，不要再调用工具。"
                            }
                            messages.append(summary_instruction)
                            
                            # 让LLM生成最终总结
                            try:
                                final_response = self.client.chat(
                                    _model=self.model,
                                    _messages=messages,
                                    tools=None  # 不提供工具，强制生成文本回答
                                )
                                
                                final_answer = final_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                                
                                if not final_answer:
                                    final_answer = f"基于已收集的 {len(all_tool_calls)} 个调查结果，任务因复杂度过高未能完成。请简化问题或分步提问。"
                                
                                # 添加提示信息
                                final_answer = f"⚠️  注意：已达到迭代限制，以下是基于 {len(all_tool_calls)} 次查询结果的总结：\n\n" + final_answer
                                
                                return {
                                    "answer": final_answer,
                                    "tool_called": len(all_tool_calls) > 0,
                                    "tool_calls": all_tool_calls,
                                    "iterations": iteration,
                                    "usage": final_response.get("usage", {}),
                                    "warning": "达到最大迭代次数，已生成部分总结",
                                    "continued": False,
                                    "partial_result": True
                                }
                            except Exception as e:
                                logger.error(f"生成总结失败: {e}")
                                return {
                                    "answer": f"已执行 {len(all_tool_calls)} 次查询，但生成总结时出错。请查看工具调用记录或简化任务。",
                                    "tool_called": len(all_tool_calls) > 0,
                                    "tool_calls": all_tool_calls,
                                    "iterations": iteration,
                                    "usage": {},
                                    "warning": "达到最大迭代次数",
                                    "continued": False,
                                    "error": str(e)
                                }
                    else:
                        # 非交互模式：生成总结
                        logger.info(f"非交互模式达到限制，已收集 {len(all_tool_calls)} 个工具调用结果，生成总结")
                        
                        summary_instruction = {
                            "role": "user",
                            "content": f"请基于已收集的信息（{len(all_tool_calls)}个工具调用结果）生成一个总结性回答。\n\n即使信息不完整，也请尽量基于现有数据给出有价值的分析和建议。\n\n请直接给出答案，不要再调用工具。"
                        }
                        messages.append(summary_instruction)
                        
                        try:
                            final_response = self.client.chat(
                                _model=self.model,
                                _messages=messages,
                                tools=None
                            )
                            
                            final_answer = final_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if not final_answer:
                                final_answer = f"基于已收集的 {len(all_tool_calls)} 个调查结果，任务因复杂度过高未能完成。"
                            
                            final_answer = f"⚠️  注意：已达到迭代限制，以下是基于 {len(all_tool_calls)} 次查询结果的总结：\n\n" + final_answer
                            
                            return {
                                "answer": final_answer,
                                "tool_called": len(all_tool_calls) > 0,
                                "tool_calls": all_tool_calls,
                                "iterations": iteration,
                                "usage": final_response.get("usage", {}),
                                "warning": "达到最大迭代次数，已生成部分总结",
                                "continued": False,
                                "partial_result": True
                            }
                        except Exception as e:
                            logger.error(f"生成总结失败: {e}")
                            return {
                                "answer": f"已执行 {len(all_tool_calls)} 次查询，但生成总结时出错。",
                                "tool_called": len(all_tool_calls) > 0,
                                "tool_calls": all_tool_calls,
                                "iterations": iteration,
                                "usage": {},
                                "warning": "达到最大迭代次数",
                                "continued": False,
                                "error": str(e)
                            }
                
                iteration += 1
                
                # 调用 AI（可能触发工具调用）
                response = self.client.chat(
                    _model=self.model,
                    _messages=messages,
                    tools=available_tools,
                    tool_choice="auto"
                )
                
                # 检查响应是否包含错误
                if response is None or "error" in response:
                    error_info = response.get("error", {}) if response else {"message": "API 调用失败"}
                    error_type = error_info.get("type", "unknown")
                    error_message = error_info.get("message", "未知错误")
                    
                    logger.error(f"API 调用错误: {error_type} - {error_message}")
                    
                    # 返回用户友好的错误信息
                    if error_type == "content_inspection_failed":
                        return {
                            "answer": "⚠️ 您的输入包含敏感内容，已被安全审查系统阻止。\n\n请修改您的问题，避免包含：\n- 违法违规内容\n- 暴力、色情等不适当内容\n- 政治敏感话题\n\n然后重新提问。",
                            "tool_called": False,
                            "tool_calls": [],
                            "iterations": iteration,
                            "usage": {},
                            "error": error_message
                        }
                    else:
                        return {
                            "answer": f"❌ 处理您的请求时发生错误: {error_message}\n\n请稍后重试或联系管理员。",
                            "tool_called": False,
                            "tool_calls": [],
                            "iterations": iteration,
                            "usage": {},
                            "error": error_message
                        }
                
                # 检查是否需要调用工具
                assistant_message = response.get("choices", [{}])[0].get("message", {})
                tool_calls = assistant_message.get("tool_calls")
                
                if not tool_calls:
                    # 不需要调用工具，返回最终回答
                    answer = assistant_message.get("content", "")
                    return {
                        "answer": answer,
                        "tool_called": len(all_tool_calls) > 0,
                        "tool_calls": all_tool_calls,
                        "iterations": iteration,
                        "usage": response.get("usage", {}),
                        "response": response,
                        "continued": continued_execution
                    }
                
                # 需要调用工具
                messages.append(assistant_message)
                
                # 执行所有工具调用
                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                    
                    try:
                        # 处理参数：如果已经是字典则直接使用，否则尝试解析JSON
                        if isinstance(arguments_str, dict):
                            arguments = arguments_str
                        elif isinstance(arguments_str, str):
                            # 处理特别长的JSON字符串，可能包含Markdown内容
                            try:
                                arguments = json.loads(arguments_str)
                            except json.JSONDecodeError as e:
                                # 记录错误位置附近的内容
                                error_pos = e.pos
                                context_start = max(0, error_pos - 50)
                                context_end = min(len(arguments_str), error_pos + 50)
                                error_context = arguments_str[context_start:context_end]
                                
                                logger.error(f"解析工具参数失败: {e}")
                                logger.error(f"错误位置 {error_pos} 附近内容: ...{error_context}...")
                                
                                # 尝试修复常见问题：未转义的换行符和引号
                                try:
                                    # 尝试简单修复：移除实际换行符，保留转义的\n
                                    fixed_str = arguments_str.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
                                    # 尝试修复未转义的引号（简单策略）
                                    arguments = json.loads(fixed_str)
                                    logger.info("成功修复 JSON 格式问题")
                                except:
                                    # 修复失败，返回错误并提供明确指导
                                    tool_result = {
                                        "success": False,
                                        "error": f"JSON解析失败: {str(e)}。内容包含未正确转义的特殊字符。",
                                        "hint": "请使用更简洁的内容格式，避免复杂的Markdown表格和大量换行。建议：1) 简化内容结构 2) 使用列表代替表格 3) 分多次创建而不是一次创建超长文档"
                                    }
                                    
                                    # 记录工具调用
                                    all_tool_calls.append({
                                        "name": function_name,
                                        "arguments": {},
                                        "result": tool_result
                                    })
                                    
                                    # 将错误结果添加到消息历史
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.get("id"),
                                        "name": function_name,
                                        "content": json.dumps(tool_result, ensure_ascii=False)
                                    })
                                    
                                    continue  # 跳过这次工具调用
                        else:
                            logger.warning(f"未知的参数类型: {type(arguments_str)}, 值: {arguments_str}")
                            arguments = {}
                    except Exception as e:
                        logger.error(f"处理工具参数异常: {e}")
                        # 返回错误
                        tool_result = {
                            "success": False,
                            "error": f"参数处理失败: {str(e)}"
                        }
                        all_tool_calls.append({
                            "name": function_name,
                            "arguments": {},
                            "result": tool_result
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id"),
                            "name": function_name,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                        continue
                    
                    # 执行工具
                    tool_result = self._execute_tool(function_name, arguments)
                    
                    # 记录工具调用
                    all_tool_calls.append({
                        "name": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    })
                    
                    # 将工具结果添加到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "name": function_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
            
        except Exception as e:
            logger.error(f"处理对话失败: {e}", exc_info=True)
            return {
                "error": str(e),
                "answer": f"抱歉，处理您的请求时出现错误: {e}",
                "tool_called": len(all_tool_calls) > 0,
                "tool_calls": all_tool_calls,
                "iterations": iteration,
                "usage": {}
            }
    
    def set_mode(self, mode: AgentMode):
        """
        动态切换 Agent 工作模式
        
        Args:
            mode: 新的工作模式
        """
        tool_config = AgentConfig.get_mode_config(mode)
        self.enable_kb = tool_config["enable_kb"]
        self.enable_web = tool_config["enable_web"]
        
        # 初始化或清理工具
        if self.enable_kb and not self.kb_tools:
            self.kb_tools = KnowledgeBaseTools()
        elif not self.enable_kb:
            self.kb_tools = None
        
        if self.enable_web and not self.web_tools:
            self.web_tools = WebTools()
        elif not self.enable_web:
            self.web_tools = None
        
        logger.info(f"Agent 模式切换到: {mode.value}, "
                   f"知识库: {'✓' if self.enable_kb else '✗'}, "
                   f"网络: {'✓' if self.enable_web else '✗'}")
    
    def set_model(self, model_type: str, model: str):
        """
        动态切换 AI 模型
        
        Args:
            model_type: 模型类型 (qwen/deepseek/openai)
            model: 模型名称
        """
        # 验证模型配置
        if not AgentConfig.validate_model(model_type, model):
            logger.error(f"无效的模型配置: {model_type}/{model}")
            raise ValueError(f"不支持的模型: {model_type}/{model}")
        
        # 更新模型配置
        self.model_type = model_type
        self.model = model
        
        # 重新初始化客户端
        if model_type == "qwen":
            self.client = QwenClient(self.api_key)
        elif model_type == "deepseek":
            self.client = DeepSeekClient(self.api_key)
        elif model_type == "openai":
            self.client = OpenAIClient(self.api_key)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        logger.info(f"Agent 模型切换到: {model_type}/{model}")
    
    def set_web_search_mode(self, mode: str):
        """
        动态切换网络查询模式
        
        Args:
            mode: 网络查询模式 (technical/product/ai_news/comprehensive)
            
        Raises:
            ValueError: 如果模式不支持
        """
        if mode not in AgentConfig.SUPPORTED_WEB_MODES:
            supported_modes = ', '.join(AgentConfig.SUPPORTED_WEB_MODES.keys())
            raise ValueError(f"不支持的模式: {mode}。支持的模式: {supported_modes}")
        
        old_mode = self.web_search_mode
        self.web_search_mode = mode
        mode_desc = AgentConfig.SUPPORTED_WEB_MODES[mode]
        
        logger.info(f"网络查询模式已切换: {old_mode} → {mode}")
        logger.info(f"模式说明: {mode_desc}")


# ========== MCP 扩展接口（预留） ==========
# TODO: 未来支持 MCP 协议时，可以创建 MCPAgentMixin 并继承
