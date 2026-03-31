"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 知识库路径配置
Output: 知识库配置对象
Pos: 知识库配置管理
"""

# file: component/chat/knowledge_base/kb_config.py
"""
知识库配置文件
"""
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 知识库根目录
KNOWLEDGE_BASE_ROOT = PROJECT_ROOT / "data" / "knowledge_base"

# 支持的文件格式
SUPPORTED_FILE_EXTENSIONS = [
    '.txt',      # 纯文本
    '.md',       # Markdown
    '.json',     # JSON
    '.opml',     # OPML（大纲）
    '.xml',      # XML
    '.csv',      # CSV
    '.yaml',     # YAML
    '.yml',      # YAML
    '.log',      # 日志文件
]

# 安全配置
SECURITY_CONFIG = {
    "allow_delete": True,           # 是否允许删除操作
    "max_file_size_mb": 10,        # 最大文件大小（MB）
    "allow_subdirectories": True,  # 是否允许操作子目录
    "backup_before_update": False, # 更新前是否备份（暂不启用）
}

# RAG 配置（预留）
RAG_CONFIG = {
    "enabled": False,              # 是否启用 RAG
    "vector_db_path": None,        # 向量数据库路径（预留）
    "embedding_model": None,       # 嵌入模型（预留）
    "chunk_size": 512,            # 文本分块大小（预留）
    "chunk_overlap": 50,          # 分块重叠大小（预留）
}

# 工具默认配置
DEFAULT_LIST_LIMIT = 50            # 列表操作默认返回数量上限
DEFAULT_READ_MAX_LENGTH = 10000    # 读取操作默认最大字符数
DEFAULT_SEARCH_LIMIT = 10          # 搜索结果默认数量上限
