#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 用户消息、对话模式
Output: AI回复
Pos: 统一聊天接口
"""

"""
统一交互式 Chat - 交互表现层
整合知识库、网络访问、多轮对话功能，使用 prompt_toolkit 提供优秀的交互体验
"""
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # 如果没有 colorama，使用 ANSI 颜色码
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        RESET_ALL = '\033[0m'
    
    HAS_COLOR = True

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from component.chat.core.unified_agent import UnifiedAgent
from component.chat.core.session_manager import SessionManager
from component.chat.config.agent_config import AgentConfig, AgentMode
from component.chat.config.system_prompts import SystemPrompts
from config.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class UnifiedChat:
    """
    统一交互式 Chat - 交互控制器
    
    职责:
    - prompt_toolkit 交互界面
    - 命令解析与路由
    - 会话生命周期管理
    - 显示格式化输出
    - 用户配置管理
    """
    
    def __init__(
        self,
        api_key: str,
        model_type: str = None,
        model: str = None,
        mode: AgentMode = None,
        system_prompt: str = None,
        kb_working_dir: str = None,
        web_search_mode: str = None
    ):
        """
        初始化统一交互式 Chat
        
        Args:
            api_key: API 密钥
            model_type: 模型类型
            model: 模型名称
            mode: Agent 工作模式
            system_prompt: 系统提示词
            kb_working_dir: 知识库工作目录（限制访问范围）
        """
        self.api_key = api_key
        self.kb_working_dir = kb_working_dir
        
        # 模型配置
        self.model_type = model_type or AgentConfig.DEFAULT_MODEL_TYPE
        self.model = model or AgentConfig.DEFAULT_MODEL
        
        # Agent 模式
        self.current_mode = mode or AgentConfig.DEFAULT_MODE
        
        # 初始化 Agent
        self.agent = UnifiedAgent(
            api_key=api_key,
            model_type=self.model_type,
            model=self.model,
            mode=self.current_mode,
            kb_working_dir=self.kb_working_dir,
            web_search_mode=web_search_mode
        )
        
        # 初始化会话管理器
        self.session_manager = SessionManager()
        
        # 创建初始会话
        self.system_prompt = system_prompt or "你是一个有用的AI助手，擅长回答各种问题。"
        session_id = self.session_manager.create_session(
            model=self.model,
            model_type=self.model_type,
            system_prompt=self.system_prompt
        )
        
        # 初始化 prompt_toolkit 会话
        self.prompt_session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
        )
        
        # 显示配置
        self.show_tool_summary = AgentConfig.SHOW_TOOL_SUMMARY
        self.show_token_stats = AgentConfig.SHOW_TOKEN_STATS
        
        logger.info(f"统一 Chat 初始化完成 - 模型: {self.model_type}/{self.model}, "
                   f"模式: {self.current_mode.value}")
    
    def _print_welcome(self):
        """打印欢迎信息"""
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 统一 AI 助手{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}👨 模型: {Fore.GREEN}{self.model_type}/{self.model}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}🔧 模式: {Fore.YELLOW}{self.current_mode.value.upper()}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}📝 系统提示词: {Fore.CYAN}{self.agent.system_prompt_type if self.agent.enable_system_prompt else '无'}{Style.RESET_ALL}")
        
        # 显示功能状态
        tool_config = AgentConfig.get_mode_config(self.current_mode)
        kb_status = f"{Fore.GREEN}✅ 启用" if tool_config['enable_kb'] else f"{Fore.RED}❌ 禁用"
        web_status = f"{Fore.GREEN}✅ 启用" if tool_config['enable_web'] else f"{Fore.RED}❌ 禁用"
        print(f"{Fore.WHITE}📚 知识库: {kb_status}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}🌐 网络访问: {web_status}{Style.RESET_ALL}")
        
        # 显示网络查询模式（当网络启用时）
        if tool_config['enable_web']:
            web_mode = self.agent.web_search_mode
            mode_desc = AgentConfig.SUPPORTED_WEB_MODES.get(web_mode, web_mode)
            print(f"{Fore.WHITE}📡 网络查询模式: {Fore.YELLOW}{web_mode}{Style.RESET_ALL} {Fore.CYAN}({mode_desc}){Style.RESET_ALL}")
        
        if tool_config['enable_kb']:
            if self.kb_working_dir:
                kb_path = f"{AgentConfig.KNOWLEDGE_BASE_ROOT}/{self.kb_working_dir}"
                print(f"{Fore.WHITE}📂 知识库路径: {Fore.BLUE}{kb_path} {Fore.YELLOW}(限制访问){Style.RESET_ALL}")
            else:
                print(f"{Fore.WHITE}📂 知识库路径: {Fore.BLUE}{AgentConfig.KNOWLEDGE_BASE_ROOT} {Fore.GREEN}(不限制){Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 基本命令:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  exit/quit        退出程序{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  clear            清空当前会话历史{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  history          查看对话历史{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  sessions         列出所有会话{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  help             显示帮助信息{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  model            显示当前模型{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}🔧 模式切换:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  mode pure        纯对话模式（无工具）{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  mode kb          仅知识库模式{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  mode web         仅网络访问模式{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  mode full        全功能模式（默认）{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}👨 模型切换:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  switch qwen      切换到 Qwen 模型{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  switch deepseek  切换到 DeepSeek 模型{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  switch openai    切换到 OpenAI 模型{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}📝 系统提示词:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  prompt           查看当前系统提示词{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  prompt list      查看所有可用提示词{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  prompt <type>    切换到指定类型的提示词{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}📡 网络查询模式:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  /webmode            查看当前网络查询模式{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  /webmode:technical  切换到技术模式{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  /webmode:product    切换到产品模式{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  /webmode:ai_news    切换到AI资讯模式{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}⚙️  设置:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  toggle_summary   切换工具调用摘要显示{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  toggle_stats     切换 Token 统计显示{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    def _print_tool_summary(self, tool_calls: list):
        """打印工具调用摘要"""
        if not self.show_tool_summary or not tool_calls:
            return
        
        print(f"\n{Fore.MAGENTA}🔧 调用了 {len(tool_calls)} 个工具:{Style.RESET_ALL}")
        for i, call in enumerate(tool_calls, 1):
            tool_name = call.get('name', '')
            tool_result = call.get('result', {})
            success = tool_result.get('success', False)
            
            # 工具图标
            if tool_name in ['fetch_url', 'get_page_summary', 'search_in_page']:
                icon = "🌐"
            else:
                icon = "📁"
            
            status = f"{Fore.GREEN}✅" if success else f"{Fore.RED}❌"
            print(f"{Fore.MAGENTA}   {i}. {icon} {tool_name} - {status}{Style.RESET_ALL}")
            
            # 显示简要信息
            if success:
                if 'documents' in tool_result:
                    print(f"{Fore.MAGENTA}      找到 {len(tool_result['documents'])} 个文档{Style.RESET_ALL}")
                elif 'content_length' in tool_result:
                    print(f"{Fore.MAGENTA}      内容长度: {tool_result['content_length']} 字符{Style.RESET_ALL}")
                elif 'url' in tool_result:
                    url = tool_result['url']
                    print(f"{Fore.MAGENTA}      URL: {url[:60]}{'...' if len(url) > 60 else ''}{Style.RESET_ALL}")
    
    def _print_token_stats(self, usage: dict, elapsed_time: float = None):
        """
        打印 Token 统计和耗时
        
        Args:
            usage: Token使用情况
            elapsed_time: 耗时（秒）
        """
        if not self.show_token_stats:
            return
        
        # Token统计
        if usage:
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            
            token_info = f"{Fore.YELLOW}提示词 {prompt_tokens}{Fore.CYAN} + {Fore.YELLOW}回复 {completion_tokens}{Fore.CYAN} = {Fore.GREEN}总计 {total_tokens}{Style.RESET_ALL}"
        else:
            token_info = f"{Fore.YELLOW}无Token数据{Style.RESET_ALL}"
        
        # 耗时统计
        if elapsed_time is not None:
            time_info = f"{Fore.CYAN} | ⏱️  耗时: {Fore.MAGENTA}{elapsed_time:.2f}秒{Style.RESET_ALL}"
        else:
            time_info = ""
        
        print(f"\n{Fore.CYAN}📊 Token 统计: {token_info}{time_info}")
    
    def _handle_command(self, user_input: str) -> bool:
        """
        处理特殊命令
        
        Args:
            user_input: 用户输入
            
        Returns:
            True 表示命令已处理，False 表示正常对话
        """
        cmd = user_input.lower().strip()
        
        # 退出命令
        if cmd in ['exit', 'quit']:
            self.session_manager.auto_save()
            print(f"\n{Fore.GREEN}👋 再见！会话已自动保存。{Style.RESET_ALL}")
            return True
        
        # 清空历史
        if cmd == 'clear':
            session = self.session_manager.get_session()
            if session:
                session.clear_history(keep_system=True)
                self.session_manager.save_current_session()
                print(f"{Fore.GREEN}✅ 当前会话历史已清空（保留系统消息）{Style.RESET_ALL}\n")
            return True
        
        # 查看历史
        if cmd == 'history':
            session = self.session_manager.get_session()
            if session:
                print(f"\n{Fore.CYAN}📜 对话历史:{Style.RESET_ALL}")
                for i, msg in enumerate(session.conversation_history):
                    role_icon = {"system": "⚙️", "user": "👤", "assistant": "🤖"}.get(msg['role'], "❓")
                    content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    role_color = {"system": Fore.YELLOW, "user": Fore.BLUE, "assistant": Fore.GREEN}.get(msg['role'], Fore.WHITE)
                    print(f"{Fore.WHITE}  [{i}] {role_icon} {role_color}{msg['role']}: {content}{Style.RESET_ALL}")
            print()
            return True
        
        # 列出会话
        if cmd == 'sessions':
            sessions = self.session_manager.list_sessions()
            print(f"\n{Fore.CYAN}📋 所有会话:{Style.RESET_ALL}")
            for s in sessions:
                current = "✓" if s['is_current'] else " "
                marker_color = Fore.GREEN if s['is_current'] else Fore.WHITE
                print(f"{marker_color}  [{current}] {s['session_id']} - {s['model']} - {s['messages']} 条消息{Style.RESET_ALL}")
            print()
            return True
        
        # 帮助命令
        if cmd == 'help':
            self._print_welcome()
            return True
        
        # 显示当前模型
        if cmd == 'model':
            print(f"\n{Fore.CYAN}🤖 当前模型: {Fore.GREEN}{self.agent.model_type}/{self.agent.model}{Style.RESET_ALL}")
            print()
            return True
        
        # 模式切换
        if cmd.startswith('mode '):
            mode_str = cmd.split(' ', 1)[1].strip()
            mode_map = {
                'pure': AgentMode.PURE,
                'kb': AgentMode.KB_ONLY,
                'web': AgentMode.WEB_ONLY,
                'full': AgentMode.FULL
            }
            
            if mode_str in mode_map:
                self.current_mode = mode_map[mode_str]
                self.agent.set_mode(self.current_mode)
                print(f"{Fore.GREEN}✅ 已切换到 {mode_str.upper()} 模式{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.RED}❌ 未知模式: {mode_str}，可用: pure, kb, web, full{Style.RESET_ALL}\n")
            return True
        
        # 切换工具摘要
        if cmd == 'toggle_summary':
            self.show_tool_summary = not self.show_tool_summary
            status = f"{Fore.GREEN}开启" if self.show_tool_summary else f"{Fore.YELLOW}关闭"
            print(f"{Fore.CYAN}⚙️  工具摘要显示已{status}{Style.RESET_ALL}\n")
            return True
        
        # 切换 Token 统计
        if cmd == 'toggle_stats':
            self.show_token_stats = not self.show_token_stats
            status = f"{Fore.GREEN}开启" if self.show_token_stats else f"{Fore.YELLOW}关闭"
            print(f"{Fore.CYAN}⚙️  Token 统计显示已{status}{Style.RESET_ALL}\n")
            return True
        
        # 模型切换
        if cmd.startswith('switch '):
            model_type_input = cmd.split(' ', 1)[1].strip().lower()
            
            # 模型类型映射
            model_type_map = {
                'qwen': 'qwen',
                'deepseek': 'deepseek',
                'openai': 'openai',
                'ds': 'deepseek',  # 简写
                'oai': 'openai'     # 简写
            }
            
            if model_type_input not in model_type_map:
                print(f"{Fore.RED}❌ 未知模型类型: {model_type_input}，可用: qwen, deepseek, openai{Style.RESET_ALL}\n")
                return True
            
            model_type = model_type_map[model_type_input]
            
            # 显示该类型可用的模型
            print(f"\n{Fore.CYAN}可用的 {model_type.upper()} 模型:{Style.RESET_ALL}")
            available_models = AgentConfig.SUPPORTED_MODELS.get(model_type, [])
            for i, m in enumerate(available_models, 1):
                print(f"{Fore.WHITE}  {i}. {m}{Style.RESET_ALL}")
            
            # 获取用户选择
            try:
                choice = input(f"\n{Fore.YELLOW}请选择模型编号 (1-{len(available_models)}, 直接回车取消): {Style.RESET_ALL}").strip()
                
                if not choice:
                    print(f"{Fore.YELLOW}已取消切换{Style.RESET_ALL}\n")
                    return True
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(available_models):
                    new_model = available_models[choice_idx]
                    
                    # 执行切换
                    try:
                        self.agent.set_model(model_type, new_model)
                        self.model_type = model_type
                        self.model = new_model
                        
                        # 更新会话管理器的模型信息
                        session = self.session_manager.get_session()
                        if session:
                            session.model = new_model
                            session.model_type = model_type
                            self.session_manager.save_current_session()
                        
                        print(f"{Fore.GREEN}✅ 已切换到模型: {model_type}/{new_model}{Style.RESET_ALL}\n")
                    except Exception as e:
                        logger.error(f"模型切换失败: {e}", exc_info=True)
                        print(f"{Fore.RED}❌ 模型切换失败: {e}{Style.RESET_ALL}\n")
                else:
                    print(f"{Fore.RED}❌ 无效的选项{Style.RESET_ALL}\n")
            except ValueError:
                print(f"{Fore.RED}❌ 请输入有效的数字{Style.RESET_ALL}\n")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}已取消切换{Style.RESET_ALL}\n")
            
            return True
        
        # 系统提示词切换
        if cmd.startswith('prompt'):
            parts = cmd.split()
            
            # 查看当前提示词
            if len(parts) == 1:
                if self.agent.enable_system_prompt:
                    prompt_info = SystemPrompts.PROMPTS.get(self.agent.system_prompt_type, {})
                    print(f"\n{Fore.CYAN}📝 当前系统提示词:{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}类型: {Fore.GREEN}{self.agent.system_prompt_type}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}名称: {Fore.GREEN}{prompt_info.get('name', '')}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}描述: {Fore.YELLOW}{prompt_info.get('description', '')}{Style.RESET_ALL}")
                    if self.agent.system_prompt:
                        print(f"\n{Fore.CYAN}内容预览:{Style.RESET_ALL}")
                        preview = self.agent.system_prompt[:300] + "..." if len(self.agent.system_prompt) > 300 else self.agent.system_prompt
                        print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.YELLOW}⚠️  当前未启用系统提示词{Style.RESET_ALL}")
                print()
                return True
            
            # 列出所有可用提示词
            elif len(parts) == 2 and parts[1] == 'list':
                print(f"\n{Fore.CYAN}📝 所有可用的系统提示词:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'=' * 70}{Style.RESET_ALL}")
                for key, info in SystemPrompts.list_prompts().items():
                    current = " (当前)" if key == self.agent.system_prompt_type else ""
                    marker = f"{Fore.GREEN}✓" if key == self.agent.system_prompt_type else f"{Fore.WHITE} "
                    print(f"{marker} {Fore.CYAN}{key}{Fore.WHITE}: {info['name']}{Fore.YELLOW}{current}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}  → {info['description']}{Style.RESET_ALL}")
                    print()
                return True
            
            # 切换到指定提示词
            elif len(parts) == 2:
                prompt_type = parts[1]
                
                if prompt_type not in SystemPrompts.get_prompt_names():
                    print(f"{Fore.RED}❌ 未知提示词类型: {prompt_type}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}可用类型: {', '.join(SystemPrompts.get_prompt_names())}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}使用 'prompt list' 查看详情{Style.RESET_ALL}\n")
                    return True
                
                # 执行切换
                new_prompt = SystemPrompts.get_prompt(prompt_type)
                
                if prompt_type == 'none':
                    self.agent.enable_system_prompt = False
                    self.agent.system_prompt = None
                    print(f"{Fore.GREEN}✅ 已禁用系统提示词{Style.RESET_ALL}\n")
                else:
                    self.agent.enable_system_prompt = True
                    self.agent.system_prompt = new_prompt
                    self.agent.system_prompt_type = prompt_type
                    
                    prompt_info = SystemPrompts.PROMPTS.get(prompt_type, {})
                    print(f"{Fore.GREEN}✅ 已切换到: {prompt_info.get('name', prompt_type)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}描述: {prompt_info.get('description', '')}{Style.RESET_ALL}")
                    
                    # 显示提示：清空对话以应用新提示词
                    print(f"{Fore.CYAN}💡 提示: 建议使用 'clear' 命令清空对话历史，以应用新提示词{Style.RESET_ALL}\n")
                
                return True
            
            else:
                print(f"{Fore.RED}❌ 无效的 prompt 命令格式{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}用法:{Style.RESET_ALL}")
                print(f"{Fore.WHITE}  prompt         - 查看当前提示词{Style.RESET_ALL}")
                print(f"{Fore.WHITE}  prompt list    - 列出所有提示词{Style.RESET_ALL}")
                print(f"{Fore.WHITE}  prompt <type>  - 切换到指定提示词{Style.RESET_ALL}\n")
            return True
        
        # 网络查询模式命令
        if cmd == 'webmode' or cmd == 'webmode:show':
            # 显示当前模式
            current_mode = self.agent.web_search_mode
            mode_desc = AgentConfig.SUPPORTED_WEB_MODES.get(current_mode, "未知")
            print(f"\n{Fore.CYAN}📡 当前网络查询模式: {Fore.GREEN}{current_mode}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}说明: {mode_desc}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}可用模式:{Style.RESET_ALL}")
            for mode, desc in AgentConfig.SUPPORTED_WEB_MODES.items():
                marker = f"{Fore.GREEN}✓" if mode == current_mode else f"{Fore.WHITE} "
                print(f"  [{marker}{Style.RESET_ALL}] {Fore.YELLOW}{mode}{Style.RESET_ALL}: {desc}")
            print(f"\n{Fore.CYAN}切换方式:{Style.RESET_ALL} /webmode:<模式名>")
            print(f"{Fore.CYAN}示例:{Style.RESET_ALL} /webmode:product, /webmode:ai_news\n")
            return True
        
        if cmd.startswith('webmode:'):
            # 切换模式
            mode = cmd.split(':', 1)[1].strip()
            try:
                old_mode = self.agent.web_search_mode
                self.agent.set_web_search_mode(mode)
                mode_desc = AgentConfig.SUPPORTED_WEB_MODES[mode]
                print(f"\n{Fore.GREEN}✅ 已切换到 {Fore.YELLOW}{mode}{Fore.GREEN} 模式{Style.RESET_ALL}")
                print(f"{Fore.WHITE}   {mode_desc}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}   原模式: {old_mode}{Style.RESET_ALL}\n")
            except ValueError as e:
                print(f"\n{Fore.RED}❌ {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}支持的模式: {', '.join(AgentConfig.SUPPORTED_WEB_MODES.keys())}{Style.RESET_ALL}\n")
            return True
        
        # 未识别的命令
        return False
    def _handle_chat(self, user_input: str):
        """
        处理正常对话
        
        Args:
            user_input: 用户输入
        """
        import time
        
        session = self.session_manager.get_session()
        if not session:
            print(f"{Fore.RED}❌ 没有活动会话{Style.RESET_ALL}\n")
            return
        
        # 获取对话历史
        conversation_history = session.get_messages_for_api()
        
        # 记录开始时间
        start_time = time.time()
        
        # 调用 Agent（启用交互模式）
        print(f"{Fore.YELLOW}🤔 思考中...{Style.RESET_ALL}")
        result = self.agent.chat(
            user_input=user_input,
            conversation_history=conversation_history,
            interactive=True  # 启用交互模式，达到限制时询问用户
        )
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 处理结果
        if result.get('error'):
            print(f"\n{Fore.RED}❌ 错误: {result.get('answer', result.get('error'))}{Style.RESET_ALL}\n")
        else:
            answer = result.get('answer', '')
            print(f"\n{Fore.GREEN}{Style.BRIGHT}🤖 助手: {Style.RESET_ALL}{Fore.WHITE}{answer}{Style.RESET_ALL}")
            
            # 显示工具调用摘要
            if result.get('tool_called'):
                self._print_tool_summary(result.get('tool_calls', []))
            
            # 显示 Token 统计和耗时
            self._print_token_stats(result.get('usage', {}), elapsed_time)
            
            print()
            
            # 将对话添加到会话历史
            session.add_message("user", user_input)
            
            # 构建完整的助手回复（包含工具调用上下文）
            full_answer = answer
            if result.get('tool_called') and result.get('tool_calls'):
                # 添加工具调用上下文摘要
                tool_context = "\n\n[\u5de5\u5177调用\u4e0a\u4e0b\u6587]\n"
                for i, tool_call in enumerate(result.get('tool_calls', []), 1):
                    tool_name = tool_call.get('name')
                    tool_result = tool_call.get('result', {})
                    
                    # 根据工具类型添加摘要
                    if tool_name == 'read_document':
                        if tool_result.get('success'):
                            content = tool_result.get('content', '')
                            # 保留前5000字符作为上下文
                            summary = content[:5000] + '...' if len(content) > 5000 else content
                            tool_context += f"{i}. 读取文档: {tool_result.get('filename')}\n{summary}\n\n"
                    elif tool_name == 'search_in_documents':
                        if tool_result.get('success'):
                            results = tool_result.get('results', [])
                            tool_context += f"{i}. 搜索结果: 找到 {len(results)} 个匹配\n"
                    elif tool_name == 'list_documents':
                        if tool_result.get('success'):
                            docs = tool_result.get('documents', [])
                            tool_context += f"{i}. 文档列表: {len(docs)} 个文档\n"
                    elif tool_name in ['fetch_url', 'fetch_dynamic_url']:
                        if tool_result.get('success'):
                            url = tool_result.get('url')
                            content = tool_result.get('content', '')
                            summary = content[:3000] + '...' if len(content) > 3000 else content
                            tool_context += f"{i}. 访问网页: {url}\n{summary}\n\n"
                    elif tool_name == 'suggest_tech_url':
                        if tool_result.get('success'):
                            suggested_url = tool_result.get('suggested_url')
                            tool_context += f"{i}. 推荐URL: {suggested_url}\n"
                
                full_answer = answer + tool_context
            
            session.add_message("assistant", full_answer)
            self.session_manager.save_current_session()
    
    def run(self):
        """运行交互式对话主循环"""
        self._print_welcome()
        
        while True:
            try:
                # 使用 prompt_toolkit 获取输入
                user_input = self.prompt_session.prompt("👤 你: ")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if self._handle_command(user_input):
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    continue
                
                # 处理对话
                self._handle_chat(user_input)
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 再见！{Style.RESET_ALL}")
                self.session_manager.auto_save()
                break
            except EOFError:
                print(f"\n\n{Fore.GREEN}👋 再见！{Style.RESET_ALL}")
                self.session_manager.auto_save()
                break
            except Exception as e:
                logger.error(f"交互异常: {e}", exc_info=True)
                print(f"\n{Fore.RED}❌ 发生错误: {e}{Style.RESET_ALL}\n")


def select_model():
    """交互式模型选择"""
    print("\n" + "=" * 50)
    print("请选择模型类型:")
    print("1. Qwen (通义千问)")
    print("2. DeepSeek")
    print("3. OpenAI")
    print("=" * 50)
    
    model_choice = input("请输入选项 (1-3, 默认1): ").strip() or "1"
    
    if model_choice == "1":
        model_type = "qwen"
        print("\n可用的 Qwen 模型:")
        print("1. qwen-turbo")
        print("2. qwen-plus (推荐)")
        print("3. qwen-max")
        print("4. qwen-flash")
        model_num = input("请输入选项 (1-4, 默认2): ").strip() or "2"
        models = {"1": "qwen-turbo", "2": "qwen-plus", "3": "qwen-max", "4": "qwen-flash"}
        model = models.get(model_num, "qwen-plus")
    elif model_choice == "2":
        model_type = "deepseek"
        print("\n可用的 DeepSeek 模型:")
        print("1. deepseek-v3")
        print("2. deepseek-v3.1")
        print("3. deepseek-v3.2-exp")
        print("4. deepseek-r1 (推荐)")
        model_num = input("请输入选项 (1-4, 默认4): ").strip() or "4"
        models = {"1": "deepseek-v3", "2": "deepseek-v3.1", "3": "deepseek-v3.2-exp", "4": "deepseek-r1"}
        model = models.get(model_num, "deepseek-r1")
    elif model_choice == "3":
        model_type = "openai"
        print("\n可用的 OpenAI 模型:")
        print("1. gpt-3.5-turbo")
        print("2. gpt-4")
        print("3. gpt-4-turbo")
        model_num = input("请输入选项 (1-3, 默认2): ").strip() or "2"
        models = {"1": "gpt-3.5-turbo", "2": "gpt-4", "3": "gpt-4-turbo"}
        model = models.get(model_num, "gpt-4")
    else:
        print("无效选项，使用默认模型 qwen-plus")
        model_type = "qwen"
        model = "qwen-plus"
    
    return model_type, model


def select_mode():
    """交互式模式选择"""
    print("\n" + "=" * 50)
    print("请选择工作模式:")
    print("1. 纯对话模式 (无工具)")
    print("2. 知识库模式 (仅知识库)")
    print("3. 网络访问模式 (仅网络)")
    print("4. 全功能模式 (知识库+网络) [推荐]")
    print("=" * 50)
    
    mode_choice = input("请输入选项 (1-4, 默认4): ").strip() or "4"
    
    mode_map = {
        "1": AgentMode.PURE,
        "2": AgentMode.KB_ONLY,
        "3": AgentMode.WEB_ONLY,
        "4": AgentMode.FULL
    }
    
    return mode_map.get(mode_choice, AgentMode.FULL)


def select_system_prompt():
    """交互式系统提示词选择"""
    print("\n" + "=" * 50)
    print("请选择系统提示词:")
    print()
    
    # 获取所有提示词
    prompts = SystemPrompts.list_prompts()
    prompt_list = list(prompts.items())
    
    # 显示选项
    for i, (key, info) in enumerate(prompt_list, 1):
        name = info['name']
        desc = info['description']
        print(f"{i}. {name}")
        print(f"   {desc}")
        print()
    
    print("=" * 50)
    
    # 默认选项：产品专家（第1个）
    default_choice = "1"
    choice = input(f"请输入选项 (1-{len(prompt_list)}, 默认{default_choice}): ").strip() or default_choice
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(prompt_list):
            prompt_type = prompt_list[index][0]
            return prompt_type
        else:
            print(f"无效选项，使用默认提示词")
            return "product_expert"
    except ValueError:
        print(f"无效输入，使用默认提示词")
        return "product_expert"


def select_web_search_mode():
    """交互式网络查询模式选择"""
    print("\n" + "=" * 50)
    print("📡 请选择网络查询模式:")
    print()
    print("1. technical - 技术文档和开源项目（GitHub、HuggingFace、arXiv）")
    print("2. product - 产品理论和方法论（人人都是产品经理、36氪、知乎）")
    print("3. ai_news - AI行业资讯和研究（机器之心、量子位、AIbase）")
    print("4. comprehensive - 综合查询（包含所有类型）")
    print("5. auto - LLM智能选择（根据问题自动匹配最佳模式） [推荐]")
    print("6. 使用默认配置 (technical)")
    print("=" * 50)
    
    mode_choice = input("请选择 (1-6，默认5): ").strip() or "5"
    
    mode_map = {
        "1": "technical",
        "2": "product",
        "3": "ai_news",
        "4": "comprehensive",
        "5": "auto",
        "6": None  # 使用默认配置
    }
    
    selected_mode = mode_map.get(mode_choice, None)
    
    if selected_mode:
        mode_desc = AgentConfig.SUPPORTED_WEB_MODES.get(selected_mode, selected_mode)
        print(f"✅ 已选择网络查询模式: {selected_mode}")
        print(f"   {mode_desc}")
    else:
        print(f"✅ 使用默认配置: technical")
    
    return selected_mode


def select_knowledge_base():
    """交互式知识库目录选择"""
    from component.chat.config.agent_config import AgentConfig
    
    kb_root = AgentConfig.KNOWLEDGE_BASE_ROOT
    
    # 获取所有子目录
    try:
        subdirs = [d for d in kb_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        subdirs = sorted(subdirs, key=lambda x: x.name)
    except Exception as e:
        print(f"❌ 无法读取知识库目录: {e}")
        return None
    
    if not subdirs:
        print(f"⚠️  知识库目录为空: {kb_root}")
        return None
    
    print("\n" + "=" * 50)
    print("📚 请选择知识库目录:")
    print()
    print("0. 不限制（访问所有知识库）")
    for i, subdir in enumerate(subdirs, 1):
        # 统计目录下的文件数量
        try:
            file_count = sum(1 for f in subdir.rglob('*') if f.is_file() and not f.name.startswith('.'))
            print(f"{i}. {subdir.name} ({file_count} 个文件)")
        except:
            print(f"{i}. {subdir.name}")
    
    print("=" * 50)
    
    choice = input(f"请输入选项 (0-{len(subdirs)}, 默认0): ").strip() or "0"
    
    try:
        index = int(choice)
        if index == 0:
            print("✅ 已选择：不限制访问范围")
            return None
        elif 1 <= index <= len(subdirs):
            selected = subdirs[index - 1]
            print(f"✅ 已选择知识库: {selected.name}")
            print(f"⚠️  提示: 本次会话只能访问该目录下的文件")
            return selected.name  # 返回相对路径名称
        else:
            print(f"无效选项，默认不限制访问")
            return None
    except ValueError:
        print(f"无效输入，默认不限制访问")
        return None


def main():
    """主函数"""
    # 初始化日志
    setup_logging()
    
    logger.info("📋 初始化统一 AI 助手")
    
    # 加载环境变量
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
    
    api_key = os.getenv("DASHSCOPE_API_KEY")

    
    if not api_key:
        print("❌ 未找到 API 密钥，请检查环境变量 DASHSCOPE_API_KEY")
        sys.exit(1)
    
    # 交互式选择配置
    model_type, model = select_model()
    mode = select_mode()
    prompt_type = select_system_prompt()
    kb_working_dir = select_knowledge_base()  # 选择知识库目录
    web_search_mode = select_web_search_mode()  # 选择网络查询模式
    
    # 创建并运行 Chat
    chat = UnifiedChat(
        api_key=api_key,
        model_type=model_type,
        model=model,
        mode=mode,
        system_prompt=SystemPrompts.get_prompt(prompt_type),
        kb_working_dir=kb_working_dir,
        web_search_mode=web_search_mode
    )
    
    chat.run()


if __name__ == "__main__":
    main()
