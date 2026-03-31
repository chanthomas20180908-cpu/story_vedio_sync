"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 会话ID、消息
Output: 会话上下文
Pos: 对话会话管理器
"""

# file: /Users/thomaschan/Code/Python/AI_vedio_demo/pythonProject/component/chat/session_manager.py
import os
import sys
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger

logger = get_logger(__name__)


class TokenCounter:
    """Token 计数器（简化版本，使用字符数估算）"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        估算文本的 token 数量
        简化版：中文约 1.5 字符/token，英文约 4 字符/token
        
        Args:
            text (str): 输入文本
            
        Returns:
            int: 估算的 token 数
        """
        if not text:
            return 0
        
        # 简单的中英文混合估算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        # 中文按 1.5 字符/token，英文按 4 字符/token
        estimated = int(chinese_chars / 1.5 + other_chars / 4)
        return max(estimated, 1)
    
    @staticmethod
    def count_messages_tokens(messages: List[Dict[str, str]]) -> int:
        """
        计算消息列表的总 token 数
        
        Args:
            messages (List[Dict[str, str]]): 消息列表
            
        Returns:
            int: 总 token 数
        """
        total = 0
        for msg in messages:
            # role 大约 4 tokens
            total += 4
            # content
            total += TokenCounter.estimate_tokens(msg.get("content", ""))
        
        # 每条消息的格式化开销约 3 tokens
        total += len(messages) * 3
        return total


class ContextWindowManager:
    """上下文窗口管理器"""
    
    # 模型的上下文窗口大小（tokens）
    MODEL_CONTEXT_LIMITS = {
        "qwen-turbo": 8000,
        "qwen-plus": 1000000,
        "qwen-max": 260000,
        "qwen-flash": 1000000,
        "deepseek-v3": 64000,
        "deepseek-v3.1": 64000,
        "deepseek-v3.2-exp": 64000,
        "deepseek-r1": 64000,
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
    }
    
    def __init__(self, model: str, max_ratio: float = 0.7):
        """
        初始化上下文窗口管理器
        
        Args:
            model (str): 模型名称
            max_ratio (float): 最大使用比例（预留空间给回复）
        """
        self.model = model
        self.max_ratio = max_ratio
        self.context_limit = self.MODEL_CONTEXT_LIMITS.get(model, 8000)
        self.max_tokens = int(self.context_limit * max_ratio)
        
        logger.info(f"上下文窗口管理 - 模型: {model}, 限制: {self.context_limit}, 最大使用: {self.max_tokens}")
    
    def truncate_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        截断消息列表以适应上下文窗口
        
        策略：
        1. 始终保留 system 消息
        2. 保留最近的对话
        3. 从中间开始删除旧消息
        
        Args:
            messages (List[Dict[str, str]]): 原始消息列表
            
        Returns:
            List[Dict[str, str]]: 截断后的消息列表
        """
        if not messages:
            return messages
        
        current_tokens = TokenCounter.count_messages_tokens(messages)
        
        if current_tokens <= self.max_tokens:
            logger.debug(f"Token 数 {current_tokens} 在限制内 {self.max_tokens}")
            return messages
        
        logger.warning(f"Token 数 {current_tokens} 超出限制 {self.max_tokens}，开始截断")
        
        # 分离 system 消息和对话消息
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        conversation_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # 从旧到新删除对话消息
        while conversation_messages and TokenCounter.count_messages_tokens(system_messages + conversation_messages) > self.max_tokens:
            # 每次删除一对 user-assistant 消息
            removed = conversation_messages.pop(0)
            logger.debug(f"删除旧消息: {removed['role']} - {removed['content'][:50]}...")
            
            # 如果下一条是 assistant 消息，也删除
            if conversation_messages and conversation_messages[0].get("role") == "assistant":
                removed = conversation_messages.pop(0)
                logger.debug(f"删除旧消息: {removed['role']} - {removed['content'][:50]}...")
        
        truncated = system_messages + conversation_messages
        final_tokens = TokenCounter.count_messages_tokens(truncated)
        logger.info(f"截断完成 - 原始: {len(messages)} 条 ({current_tokens} tokens), 截断后: {len(truncated)} 条 ({final_tokens} tokens)")
        
        return truncated
    
    def get_stats(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        获取上下文统计信息
        
        Args:
            messages (List[Dict[str, str]]): 消息列表
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        tokens = TokenCounter.count_messages_tokens(messages)
        return {
            "messages_count": len(messages),
            "tokens_used": tokens,
            "tokens_limit": self.max_tokens,
            "context_limit": self.context_limit,
            "usage_ratio": round(tokens / self.max_tokens * 100, 2) if self.max_tokens > 0 else 0,
            "remaining_tokens": max(0, self.max_tokens - tokens)
        }


class ChatSession:
    """单个对话会话"""
    
    def __init__(self, session_id: str, model: str, model_type: str, system_prompt: str = None):
        """
        初始化对话会话
        
        Args:
            session_id (str): 会话 ID
            model (str): 模型名称
            model_type (str): 模型类型
            system_prompt (str): 系统提示词
        """
        self.session_id = session_id
        self.model = model
        self.model_type = model_type
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []
        self.context_manager = ContextWindowManager(model)
        
        if system_prompt:
            self.add_message("system", system_prompt)
        
        logger.info(f"创建会话 - ID: {session_id}, 模型: {model_type}/{model}")
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
        logger.debug(f"[{self.session_id}] 添加消息: {role} - {content[:50]}...")
    
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """
        获取用于 API 调用的消息列表（自动截断）
        
        Returns:
            List[Dict[str, str]]: 截断后的消息列表
        """
        # 移除 timestamp 字段（API 不需要）
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history]
        return self.context_manager.truncate_messages(messages)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        messages_for_api = self.get_messages_for_api()
        context_stats = self.context_manager.get_stats(messages_for_api)
        
        return {
            "session_id": self.session_id,
            "model": f"{self.model_type}/{self.model}",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_messages": len(self.conversation_history),
            "api_messages": len(messages_for_api),
            "context_stats": context_stats
        }
    
    def clear_history(self, keep_system: bool = True):
        """清空历史"""
        if keep_system:
            self.conversation_history = [msg for msg in self.conversation_history if msg["role"] == "system"]
        else:
            self.conversation_history = []
        self.updated_at = datetime.now()
        logger.info(f"[{self.session_id}] 清空历史 (keep_system={keep_system})")
    
    def delete_message(self, index: int) -> bool:
        """
        删除指定索引的消息
        
        Args:
            index (int): 消息索引
            
        Returns:
            bool: 是否删除成功
        """
        if 0 <= index < len(self.conversation_history):
            deleted = self.conversation_history.pop(index)
            self.updated_at = datetime.now()
            logger.info(f"[{self.session_id}] 删除消息 {index}: {deleted['role']} - {deleted['content'][:50]}...")
            return True
        logger.warning(f"[{self.session_id}] 无效的消息索引: {index}")
        return False
    
    def edit_message(self, index: int, new_content: str) -> bool:
        """
        编辑指定索引的消息内容
        
        Args:
            index (int): 消息索引
            new_content (str): 新的消息内容
            
        Returns:
            bool: 是否编辑成功
        """
        if 0 <= index < len(self.conversation_history):
            old_content = self.conversation_history[index]['content']
            self.conversation_history[index]['content'] = new_content
            self.conversation_history[index]['edited_at'] = datetime.now().isoformat()
            self.updated_at = datetime.now()
            logger.info(f"[{self.session_id}] 编辑消息 {index}: '{old_content[:30]}...' -> '{new_content[:30]}...'")
            return True
        logger.warning(f"[{self.session_id}] 无效的消息索引: {index}")
        return False
    
    def rollback_to(self, index: int) -> bool:
        """
        回滚对话历史到指定索引（删除之后的所有消息）
        
        Args:
            index (int): 回滚目标索引
            
        Returns:
            bool: 是否回滚成功
        """
        if 0 <= index < len(self.conversation_history):
            deleted_count = len(self.conversation_history) - index - 1
            self.conversation_history = self.conversation_history[:index + 1]
            self.updated_at = datetime.now()
            logger.info(f"[{self.session_id}] 回滚到消息 {index}，删除了 {deleted_count} 条消息")
            return True
        logger.warning(f"[{self.session_id}] 无效的回滚索引: {index}")
        return False
    
    def get_last_user_message_index(self) -> int:
        """
        获取最后一条用户消息的索引
        
        Returns:
            int: 消息索引，未找到返回 -1
        """
        for i in range(len(self.conversation_history) - 1, -1, -1):
            if self.conversation_history[i]['role'] == 'user':
                return i
        return -1
    
    def get_message_pair(self, user_message_index: int) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        获取指定用户消息及其对应的助手回复
        
        Args:
            user_message_index (int): 用户消息索引
            
        Returns:
            Tuple[Optional[Dict], Optional[Dict]]: (用户消息, 助手消息)
        """
        if 0 <= user_message_index < len(self.conversation_history):
            user_msg = self.conversation_history[user_message_index]
            if user_msg['role'] == 'user':
                # 查找下一条 assistant 消息
                if user_message_index + 1 < len(self.conversation_history):
                    assistant_msg = self.conversation_history[user_message_index + 1]
                    if assistant_msg['role'] == 'assistant':
                        return (user_msg, assistant_msg)
                return (user_msg, None)
        return (None, None)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "model": self.model,
            "model_type": self.model_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "conversation_history": self.conversation_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """从字典创建会话"""
        session = cls(
            session_id=data["session_id"],
            model=data["model"],
            model_type=data["model_type"],
            system_prompt=None
        )
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        session.conversation_history = data["conversation_history"]
        return session


class SessionManager:
    """多会话管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化会话管理器
        
        Args:
            db_path (str): SQLite 数据库路径
        """
        if db_path is None:
            db_path = project_root / "data" / "chat_sessions.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        
        self._init_database()
        self._load_sessions()
        
        logger.info(f"会话管理器初始化 - 数据库: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    conversation_history TEXT NOT NULL
                )
            ''')
            conn.commit()
        logger.debug("数据库初始化完成")
    
    def _load_sessions(self):
        """从数据库加载会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT session_id, model, model_type, created_at, updated_at, conversation_history FROM sessions ORDER BY updated_at DESC')
            rows = cursor.fetchall()
            
            for row in rows:
                session_id, model, model_type, created_at, updated_at, history_json = row
                session = ChatSession(session_id, model, model_type)
                session.created_at = datetime.fromisoformat(created_at)
                session.updated_at = datetime.fromisoformat(updated_at)
                session.conversation_history = json.loads(history_json)
                self.sessions[session_id] = session
            
            logger.info(f"从数据库加载 {len(rows)} 个会话")
    
    def _save_session(self, session: ChatSession):
        """保存会话到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sessions (session_id, model, model_type, created_at, updated_at, conversation_history)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session.session_id,
                session.model,
                session.model_type,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                json.dumps(session.conversation_history, ensure_ascii=False)
            ))
            conn.commit()
        logger.debug(f"会话已保存: {session.session_id}")
    
    def create_session(self, model: str, model_type: str, system_prompt: str = None, session_id: str = None) -> str:
        """
        创建新会话
        
        Args:
            model (str): 模型名称
            model_type (str): 模型类型
            system_prompt (str): 系统提示词
            session_id (str): 指定会话 ID（可选）
            
        Returns:
            str: 会话 ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        
        session = ChatSession(session_id, model, model_type, system_prompt)
        self.sessions[session_id] = session
        self.current_session_id = session_id
        
        self._save_session(session)
        logger.info(f"创建新会话: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str = None) -> Optional[ChatSession]:
        """获取会话"""
        if session_id is None:
            session_id = self.current_session_id
        
        return self.sessions.get(session_id)
    
    def switch_session(self, session_id: str) -> bool:
        """切换当前会话"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            logger.info(f"切换到会话: {session_id}")
            return True
        logger.warning(f"会话不存在: {session_id}")
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        sessions_list = []
        for session_id, session in sorted(self.sessions.items(), key=lambda x: x[1].updated_at, reverse=True):
            sessions_list.append({
                "session_id": session_id,
                "model": f"{session.model_type}/{session.model}",
                "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": session.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "messages": len(session.conversation_history),
                "is_current": session_id == self.current_session_id
            })
        return sessions_list
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
            
            if self.current_session_id == session_id:
                self.current_session_id = None
            
            logger.info(f"删除会话: {session_id}")
            return True
        
        logger.warning(f"会话不存在: {session_id}")
        return False
    
    def save_current_session(self):
        """保存当前会话"""
        if self.current_session_id:
            session = self.get_session()
            if session:
                self._save_session(session)
    
    def auto_save(self):
        """自动保存所有会话"""
        for session in self.sessions.values():
            self._save_session(session)
        logger.debug("自动保存所有会话")


if __name__ == "__main__":
    from config.logging_config import setup_logging
    
    setup_logging()
    
    # 测试 Token 计数
    print("\n=== Token 计数测试 ===")
    text1 = "Hello, how are you?"
    text2 = "你好，最近怎么样？"
    text3 = "This is a mixed 中英文 text 测试"
    
    print(f"英文: '{text1}' -> {TokenCounter.estimate_tokens(text1)} tokens")
    print(f"中文: '{text2}' -> {TokenCounter.estimate_tokens(text2)} tokens")
    print(f"混合: '{text3}' -> {TokenCounter.estimate_tokens(text3)} tokens")
    
    # 测试会话管理
    print("\n=== 会话管理测试 ===")
    manager = SessionManager()
    
    # 创建会话
    sid1 = manager.create_session("qwen-plus", "qwen", "你是一个AI助手")
    print(f"创建会话: {sid1}")
    
    # 添加消息
    session = manager.get_session()
    session.add_message("user", "你好")
    session.add_message("assistant", "你好！有什么可以帮助你的吗？")
    
    # 查看统计
    stats = session.get_stats()
    print(f"\n会话统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    # 保存会话
    manager.save_current_session()
    print("\n会话已保存到数据库")
    
    # 列出会话
    print("\n所有会话:")
    for s in manager.list_sessions():
        print(f"  {'[当前]' if s['is_current'] else '      '} {s['session_id']} - {s['model']} - {s['messages']} 条消息")
