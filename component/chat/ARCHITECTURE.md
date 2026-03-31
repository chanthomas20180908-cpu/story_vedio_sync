# 🏗️ Unified Chat Agent 架构文档

**⚠️ 一旦我所属的文件夹有所变化，请更新我。**

## 📋 目录
- [架构概览](#架构概览)
- [分层架构](#分层架构)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [目录结构](#目录结构)
- [扩展性设计](#扩展性设计)

---

## 🎯 架构概览

`unified_chat` 是一个**多功能 AI Agent 系统**，采用**分层架构**设计，支持：
- 🤖 多模型切换（Qwen、DeepSeek、OpenAI）
- 📚 知识库访问（文档读写、搜索）
- 🔒 知识库访问隔离（可限制只访问指定子目录）
- 🌐 网络访问（网页抓取、智能推荐）
- 💬 多轮对话（会话管理、上下文保持）
- 🔧 Function Calling（工具调用）
- 🚀 可扩展至 MCP 协议（预留接口）

---

## 📚 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     交互表现层 (Presentation)                │
│  unified_chat.py - UnifiedChat                              │
│  • prompt_toolkit 交互界面                                  │
│  • 命令解析与路由                                           │
│  • 格式化输出（彩色日志、进度显示）                          │
│  • 用户配置管理（模型、模式、系统提示词）                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     业务逻辑层 (Business Logic)              │
│  core/unified_agent.py - UnifiedAgent                       │
│  • AI 模型调用（Qwen/DeepSeek/OpenAI）                      │
│  • Function Calling 处理                                    │
│  • 工具编排与执行                                           │
│  • 多轮工具调用逻辑（最多20轮）                              │
│  • Token 计数与统计                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────┬──────────────────────────────────────┐
│   工具层 (Tools)      │   会话管理 (Session)                 │
│                      │                                      │
│  tools/kb_tools.py   │  core/session_manager.py            │
│  • 文档列表          │  • 会话生命周期                      │
│  • 文档读写          │  • SQLite 持久化                     │
│  • 全文搜索          │  • 自动保存                         │
│  • 模糊匹配          │  • 上下文管理                       │
│                      │                                      │
│  tools/web_tools.py  │                                      │
│  • URL 访问          │                                      │
│  • 内容提取          │                                      │
│  • 智能推荐          │                                      │
│  • 页面搜索          │                                      │
└──────────────────────┴──────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     模型客户端层 (Model Clients)             │
│  core/chat.py                                               │
│  • QwenClient    - 阿里通义千问                             │
│  • DeepSeekClient - DeepSeek (支持思考链)                   │
│  • OpenAIClient  - OpenAI GPT                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     配置层 (Configuration)                   │
│  config/agent_config.py                                     │
│  • AgentMode (纯对话/知识库/网络/全功能)                     │
│  • 模型列表 & 默认模型                                       │
│  • 知识库路径配置                                           │
│  • 工具参数配置                                             │
│                                                             │
│  config/system_prompts.py                                   │
│  • 系统提示词库（产品专家/技术专家等）                        │
│  • 动态提示词切换                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 核心组件

### 1️⃣ **交互表现层** - `unified_chat.py::UnifiedChat`

**职责：**
- 🖥️ 提供命令行交互界面（基于 `prompt_toolkit`）
- 📝 解析用户命令（模式切换、模型切换、提示词管理等）
- 🎨 格式化输出（彩色日志、工具摘要、Token 统计）
- ⚙️ 管理用户配置

**核心方法：**
```python
class UnifiedChat:
    def __init__(api_key, model_type, model, mode, kb_working_dir, ...)
        # 初始化 Agent、会话管理器、prompt_toolkit
        # kb_working_dir: 知识库工作目录（限制访问范围）
    
    def _print_welcome()
        # 显示欢迎信息、当前配置、帮助命令
    
    def _handle_command(user_input) -> bool
        # 处理特殊命令：exit, clear, mode, switch, prompt 等
        # 返回 True 表示命令已处理
    
    def _handle_chat(user_input)
        # 处理正常对话：调用 Agent.chat()
        # 显示结果、工具摘要、Token 统计
        # 保存会话历史
    
    def run()
        # 主循环：接收输入 → 命令/对话路由 → 显示结果
```

**支持的命令：**
```bash
# 基本命令
exit/quit         退出程序
clear             清空当前会话历史
history           查看对话历史
sessions          列出所有会话
help              显示帮助信息
model             显示当前模型

# 模式切换
mode pure         纯对话模式（无工具）
mode kb           仅知识库模式
mode web          仅网络访问模式
mode full         全功能模式（默认）

# 模型切换
switch qwen       切换到 Qwen 模型
switch deepseek   切换到 DeepSeek 模型
switch openai     切换到 OpenAI 模型

# 系统提示词
prompt            查看当前系统提示词
prompt list       查看所有可用提示词
prompt <type>     切换到指定类型的提示词

# 设置
toggle_summary    切换工具调用摘要显示
toggle_stats      切换 Token 统计显示
```

---

### 2️⃣ **业务逻辑层** - `core/unified_agent.py::UnifiedAgent`

**职责：**
- 🤖 调用 AI 模型生成回复
- 🔧 处理 Function Calling（解析、执行、结果组装）
- 🔄 多轮工具调用逻辑（最多 20 轮）
- 📊 Token 计数与统计
- 🧠 上下文管理（交互式确认）

**核心方法：**
```python
class UnifiedAgent:
    def __init__(api_key, model_type, model, mode, kb_working_dir, ...)
        # 初始化模型客户端、工具实例、配置
        # kb_working_dir: 相对路径子目录名（如 'AI锐评'），限制只能访问该子目录
    
    def chat(user_input, conversation_history, interactive=False)
        # 主对话方法
        # 1. 准备消息列表
        # 2. 循环调用模型（最多20轮）
        # 3. 检测工具调用 → 执行工具 → 组装结果
        # 4. 返回最终答案、工具调用记录、Token 统计
    
    def _execute_tool_call(tool_call)
        # 执行单个工具调用
        # 根据工具名分发到 KB 工具或 Web 工具
    
    def set_mode(mode)
        # 动态切换模式（更新工具定义列表）
    
    def set_model(model_type, model)
        # 动态切换模型
    
    def _get_tool_definitions()
        # 根据当前模式返回可用工具定义
```

**工具定义（Function Calling Schema）：**

**知识库工具（4个）：**
```python
KB_TOOL_DEFINITIONS = [
    {
        "name": "list_documents",
        "description": "列出知识库中的文档",
        "parameters": {
            "directory": str,  # 子目录，如 'avater/竞品分析'
            "limit": int,      # 返回数量，默认 50
            "pattern": str     # 文件名模式，如 '*淘宝*'
        }
    },
    {
        "name": "read_document",
        "description": "读取知识库文档内容（支持 PDF OCR）",
        "parameters": {
            "filepath": str,   # 支持完整路径和部分文件名
            "max_length": int  # 最大读取字符数，默认 10000
        }
    },
    {
        "name": "create_document",
        "description": "创建新文档",
        "parameters": {
            "filepath": str,   # 相对于知识库根目录
            "content": str,    # 文档内容
            "overwrite": bool  # 是否覆盖，默认 false
        }
    },
    {
        "name": "search_in_documents",
        "description": "全文搜索关键词",
        "parameters": {
            "keyword": str,    # 搜索关键词
            "directory": str,  # 搜索目录
            "limit": int       # 返回结果数量，默认 10
        }
    }
]
```

**网络访问工具（4个）：**
```python
WEB_TOOL_DEFINITIONS = [
    {
        "name": "suggest_tech_url",
        "description": "根据技术关键词智能推荐 URL",
        "parameters": {
            "keyword": str  # 技术关键词，如 'qwen3', 'llama'
        }
    },
    {
        "name": "fetch_url",
        "description": "访问网页并获取内容",
        "parameters": {
            "url": str,           # 目标 URL
            "extract_main": bool  # 是否只提取主要内容，默认 true
        }
    },
    {
        "name": "get_page_summary",
        "description": "获取网页摘要（前几段）",
        "parameters": {
            "url": str,              # 目标 URL
            "max_paragraphs": int    # 最大段落数，默认 5
        }
    },
    {
        "name": "search_in_page",
        "description": "在网页中搜索关键词",
        "parameters": {
            "url": str,      # 目标 URL
            "keyword": str,  # 搜索关键词
            "context_size": int  # 上下文大小，默认 200
        }
    }
]
```

---

### 3️⃣ **工具层** - `tools/kb_tools.py` & `tools/web_tools.py`

#### 📚 知识库工具 - `KnowledgeBaseTools`

**特性：**
- ✅ 支持文本文件（.txt, .md, .json, .csv, .log）
- ✅ 支持 PDF 文件（自动 OCR 识别）
- ✅ 模糊文件名匹配（智能查找）
- ✅ 递归目录搜索
- ✅ 访问权限控制（可限制子目录）

**核心方法：**
```python
class KnowledgeBaseTools:
    def list_documents(directory="", limit=50, pattern="*")
        # 列出文档，支持 glob 模式匹配
        # 返回: {"documents": [{"filename": ..., "path": ..., "size": ...}]}
    
    def read_document(filepath, max_length=10000)
        # 读取文档内容
        # 支持模糊匹配：'淘宝竞品' → '淘宝AI直播竞品综合分析报告.md'
        # PDF 自动 OCR
        # 返回: {"content": ..., "filename": ...}
    
    def create_document(filepath, content, overwrite=False)
        # 创建文档（支持子目录自动创建）
        # 返回: {"filepath": ...}
    
    def search_in_documents(keyword, directory="", limit=10)
        # 全文搜索（跳过 PDF）
        # 返回: {"results": [{"file": ..., "line_number": ..., "context": ...}]}
```

#### 🌐 网络访问工具 - `WebTools`

**特性：**
- ✅ 智能 URL 推荐（技术文档优先）
- ✅ 网页内容提取（自动去除广告、导航）
- ✅ 页面摘要生成
- ✅ 页内关键词搜索

**核心方法：**
```python
class WebTools:
    def suggest_tech_url(keyword)
        # 根据关键词推荐技术文档 URL
        # 支持：AI 模型、图像模型、框架等
        # 返回: {"suggested_url": ..., "source": ..., "confidence": ...}
    
    def fetch_url(url, extract_main=True)
        # 访问网页，提取内容
        # 返回: {"content": ..., "title": ..., "url": ...}
    
    def get_page_summary(url, max_paragraphs=5)
        # 获取网页摘要
        # 返回: {"summary": ..., "title": ..., "url": ...}
    
    def search_in_page(url, keyword, context_size=200)
        # 在网页中搜索关键词
        # 返回: {"matches": [{"context": ..., "position": ...}]}
```

---

### 4️⃣ **会话管理层** - `core/session_manager.py::SessionManager`

**职责：**
- 💾 SQLite 持久化存储会话
- 🔄 自动保存（每 60 秒或手动）
- 📝 上下文管理（清空、导入、导出）
- 🔍 会话列表查询

**核心方法：**
```python
class SessionManager:
    def create_session(model, model_type, system_prompt)
        # 创建新会话
        # 返回: session_id
    
    def get_session(session_id=None)
        # 获取当前会话或指定会话
        # 返回: Session 对象
    
    def save_current_session()
        # 保存当前会话到数据库
    
    def auto_save()
        # 自动保存（周期性调用）
    
    def list_sessions()
        # 列出所有会话
        # 返回: [{"session_id": ..., "model": ..., "messages": ...}]
```

**会话数据结构：**
```python
class Session:
    session_id: str           # 会话 ID
    model: str                # 模型名称
    model_type: str           # 模型类型
    conversation_history: List[Dict]  # 对话历史
    system_prompt: Optional[str]      # 系统提示词
    created_at: str           # 创建时间
    
    def add_message(role, content)
        # 添加消息到历史
    
    def clear_history(keep_system=True)
        # 清空历史（可保留系统消息）
    
    def get_messages_for_api()
        # 获取适用于 API 的消息格式
```

**数据库 Schema：**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    model TEXT,
    model_type TEXT,
    system_prompt TEXT,
    conversation_history TEXT,  -- JSON 格式
    created_at TEXT,
    last_updated TEXT
);
```

---

### 5️⃣ **模型客户端层** - `core/chat.py`

**职责：**
- 🤖 封装各模型 API 调用
- 📝 统一接口
- 📊 Token 统计
- 🔧 Function Calling 支持

**核心类：**
```python
class QwenClient:
    def chat_with_functions(messages, tools, ...)
        # 调用通义千问 API
        # 返回: {"content": ..., "tool_calls": [...], "usage": {...}}

class DeepSeekClient:
    def chat_with_functions(messages, tools, enable_thinking=True, ...)
        # 调用 DeepSeek API
        # 支持思考链（thinking）
        # 返回: {"content": ..., "thinking": ..., "tool_calls": [...]}

class OpenAIClient:
    def chat_with_functions(messages, tools, ...)
        # 调用 OpenAI API
        # 返回: {"content": ..., "tool_calls": [...], "usage": {...}}
```

---

### 6️⃣ **配置层**

#### ⚙️ `config/agent_config.py::AgentConfig`

**配置项：**
```python
class AgentConfig:
    # 工具协议
    TOOL_PROTOCOL = ToolProtocol.FUNCTION_CALL  # 或 MCP
    
    # 默认模式
    DEFAULT_MODE = AgentMode.FULL  # PURE/KB_ONLY/WEB_ONLY/FULL
    
    # 模型配置
    DEFAULT_MODEL_TYPE = "qwen"
    DEFAULT_MODEL = "qwen-plus"
    SUPPORTED_MODELS = {
        "qwen": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-flash"],
        "deepseek": ["deepseek-v3", "deepseek-v3.1", "deepseek-v3.2-exp", "deepseek-r1"],
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    }
    
    # 工具配置
    MAX_TOOL_ITERATIONS = 20  # 最大工具调用轮数
    
    # 知识库配置
    KNOWLEDGE_BASE_ROOT = Path("/path/to/knowledge_base")
    SUPPORTED_FILE_EXTENSIONS = [".txt", ".md", ".json", ".csv", ".log"]
    
    # 网络访问配置
    WEB_REQUEST_TIMEOUT = 10
    WEB_MAX_CONTENT_LENGTH = 50000
    
    # 交互界面配置
    SHOW_TOOL_SUMMARY = True   # 显示工具调用摘要
    SHOW_THINKING = True        # 显示思考过程（DeepSeek R1）
    SHOW_TOKEN_STATS = True     # 显示 Token 统计
    
    # 会话管理配置
    SESSION_DB_PATH = Path("data/Data_results/chat_sessions.db")
    AUTO_SAVE_INTERVAL = 60     # 秒
    CONTEXT_WINDOW_SIZE = 8000  # tokens
```

#### 📝 `config/system_prompts.py::SystemPrompts`

**系统提示词库：**
```python
class SystemPrompts:
    PROMPTS = {
        "product_expert": {
            "name": "产品专家",
            "description": "擅长产品规划、需求分析、用户研究",
            "content": "你是一位资深产品专家..."
        },
        "tech_expert": {
            "name": "技术专家",
            "description": "擅长技术架构、代码分析、技术调研",
            "content": "你是一位资深技术专家..."
        },
        "data_analyst": {
            "name": "数据分析师",
            "description": "擅长数据分析、可视化、报告撰写",
            "content": "你是一位资深数据分析师..."
        },
        "none": {
            "name": "无提示词",
            "description": "不使用系统提示词",
            "content": None
        }
    }
    
    @staticmethod
    def get_prompt(prompt_type) -> str
    @staticmethod
    def list_prompts() -> dict
    @staticmethod
    def get_prompt_names() -> list
```

---

## 🔄 数据流

### 📍 完整对话流程

```
用户输入
  ↓
┌─────────────────────────────────────────────────────┐
│ 1. UnifiedChat._handle_command()                    │
│    → 是命令？执行命令逻辑，结束                       │
│    → 不是命令？继续对话流程                          │
└─────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────┐
│ 2. UnifiedChat._handle_chat()                       │
│    → 获取会话历史                                    │
│    → 调用 UnifiedAgent.chat()                       │
└─────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────┐
│ 3. UnifiedAgent.chat()                              │
│    → 准备消息列表（系统提示词 + 历史 + 用户输入）     │
│    → 循环调用模型（最多 20 轮）                       │
│      ├─ 模型返回文本？结束循环                       │
│      ├─ 模型返回工具调用？                           │
│      │   ├─ 执行工具（KB 或 Web）                    │
│      │   ├─ 组装结果                                 │
│      │   └─ 继续下一轮（追加工具结果到消息列表）      │
│      └─ 达到 20 轮？询问用户是否继续                 │
│    → 返回最终答案 + 工具调用记录 + Token 统计       │
└─────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────┐
│ 4. UnifiedChat._handle_chat() (续)                  │
│    → 显示答案                                        │
│    → 显示工具调用摘要（可选）                         │
│    → 显示 Token 统计（可选）                         │
│    → 保存对话到会话历史                              │
└─────────────────────────────────────────────────────┘
  ↓
继续下一次输入
```

### 🔧 工具调用流程（详细）

```
模型返回工具调用
  ↓
UnifiedAgent._execute_tool_call()
  ↓
根据工具名分发
  ├─ KB 工具
  │   ├─ list_documents → KnowledgeBaseTools.list_documents()
  │   ├─ read_document → KnowledgeBaseTools.read_document()
  │   ├─ create_document → KnowledgeBaseTools.create_document()
  │   └─ search_in_documents → KnowledgeBaseTools.search_in_documents()
  │
  └─ Web 工具
      ├─ suggest_tech_url → WebTools.suggest_tech_url()
      ├─ fetch_url → WebTools.fetch_url()
      ├─ get_page_summary → WebTools.get_page_summary()
      └─ search_in_page → WebTools.search_in_page()
  ↓
返回工具执行结果
  ↓
组装为消息（role="tool"）
  ↓
追加到消息列表
  ↓
继续下一轮模型调用
```

---

## 📁 目录结构

```
component/chat/
├── unified_chat.py            # 🖥️ 交互表现层（主入口）
│
├── core/                      # 🧠 核心业务逻辑
│   ├── __init__.py
│   ├── unified_agent.py       # Agent 核心（工具编排、多轮调用）
│   ├── chat.py                # 模型客户端（Qwen/DeepSeek/OpenAI）
│   └── session_manager.py     # 会话管理（SQLite 持久化）
│
├── tools/                     # 🔧 工具层
│   ├── __init__.py
│   ├── kb_tools.py            # 知识库工具（文档读写、搜索）
│   ├── web_tools.py           # 网络访问工具（爬虫、推荐）
│   └── (预留 MCP 服务器)
│
├── config/                    # ⚙️ 配置层
│   ├── __init__.py
│   ├── agent_config.py        # Agent 配置（模式、模型、路径）
│   └── system_prompts.py      # 系统提示词库
│
├── knowledge_base/            # 📚 旧版知识库（兼容保留）
│   ├── kb_agent.py
│   ├── kb_tools.py
│   └── web_tools.py
│
├── ARCHITECTURE.md            # 📖 本架构文档
└── README.md                  # 📖 使用说明
```

---

## 🔒 知识库访问隔离

为了保证数据安全性，`unified_chat` 支持**知识库访问隔离**，即限制 Agent 只能访问指定子目录下的文件。

### 📌 使用场景

1. **多项目隔离**：不同项目的知识库分别存储在不同子目录，避免互相干扰
2. **权限控制**：限制某次对话只能访问特定项目的文档
3. **数据安全**：防止意外访问或修改其他目录的文件

### 🛠️ 实现机制

**1. 启动时选择知识库目录**

运行 `unified_chat` 时，会展示知识库根目录下的所有子目录：

```bash
python3 -m component.chat.unified_chat

# 会显示：
==================================================
📚 请选择知识库目录:

0. 不限制（访问所有知识库）
1. AI锐评 (35 个文件)
2. Ohyes_AI产品方向 (1 个文件)
3. avater (56 个文件)
4. hit_video_remake (6 个文件)
5. 图片视频复刻 (6 个文件)
==================================================
请输入选项 (0-5, 默认0): 
```

- **选择 0**：不限制，可访问所有子目录
- **选择 1-5**：只能访问对应子目录下的文件

**2. 工作目录限制**

当选择某个子目录时，`KnowledgeBaseTools` 会自动限制文件访问范围：

```python
# 例：选择了 "AI锐评" 目录
kb_tools = KnowledgeBaseTools(
    kb_root="/path/to/knowledge_base",
    working_dir="AI锐评"  # 限制只能访问该子目录
)

# 所有文件路径都会被解析为相对于 working_dir 的路径
kb_tools.read_document("竞品分析.md")  # 实际访问: /path/to/knowledge_base/AI锐评/竞品分析.md

# 尝试访问其他目录的文件会失败
kb_tools.read_document("../Ohyes_AI产品方向/doc.md")  # ❌ 抛出异常: 访问超出工作目录范围
```

**3. 安全检查**

`KnowledgeBaseTools._resolve_path()` 会对所有文件路径进行安全检查：

```python
def _resolve_path(self, relative_path: str) -> Path:
    # 移除开头的斜杠
    relative_path = relative_path.lstrip('/')
    
    # 从工作目录开始构建路径
    full_path = (self.working_dir / relative_path).resolve()
    
    # 安全检查：确保路径在工作目录内
    if not str(full_path).startswith(str(self.working_dir.resolve())):
        raise ValueError(f"访问超出工作目录范围: {relative_path}")
    
    return full_path
```

### 📄 使用示例

```python
# 启动时选择 "AI锐评" 目录
chat = UnifiedChat(
    api_key=api_key,
    model_type="qwen",
    model="qwen-plus",
    mode=AgentMode.KB_ONLY,
    kb_working_dir="AI锐评"  # 限制访问范围
)

# 对话中，Agent 只能访问 AI锐评 目录下的文件
用户: 请读取竞品分析文档
AI: [调用 read_document("AI锐评/竞品分析.md")]  ✅ 成功

用户: 请读取 Ohyes_AI产品方向 的文档
AI: [调用 read_document("../Ohyes_AI产品方向/doc.md")]  ❌ 失败: 访问超出工作目录范围
```

### ⚠️ 注意事项

1. **目录选择是会话级别的**：每次启动 `unified_chat` 都需要重新选择
2. **默认不限制**：如果直接回车或选择 0，则可访问所有知识库
3. **子目录递归访问**：选择某个目录后，可以访问其下的所有子目录
4. **路径遍历防护**：`..` 等路径遍历攻击会被自动阻止

---

## 🚀 扩展性设计

### 1️⃣ **多协议支持（预留 MCP）**

当前使用 **Function Calling**，已预留 **MCP (Model Context Protocol)** 接口：

```python
# agent_config.py
class ToolProtocol(Enum):
    FUNCTION_CALL = "function_call"
    MCP = "mcp"

class AgentConfig:
    TOOL_PROTOCOL = ToolProtocol.FUNCTION_CALL  # 可切换为 MCP
    
    MCP_SERVERS = {
        "knowledge_base": {
            "command": "python",
            "args": ["-m", "component.chat.tools.kb_mcp_server"],
            "env": {}
        },
        "web_access": {...}
    }
```

**扩展步骤：**
1. 实现 MCP 服务器（`tools/kb_mcp_server.py`）
2. 在 `UnifiedAgent` 中添加 MCP 客户端逻辑
3. 切换 `TOOL_PROTOCOL = ToolProtocol.MCP`

---

### 2️⃣ **新增工具**

**步骤：**
1. 在 `tools/` 下创建新工具类（如 `database_tools.py`）
2. 在 `UnifiedAgent` 中定义工具 Schema
3. 在 `_execute_tool_call()` 中添加工具分发逻辑
4. 在 `AgentMode` 中添加新模式（可选）

**示例：添加数据库工具**
```python
# tools/database_tools.py
class DatabaseTools:
    def query_database(sql):
        # 执行 SQL 查询
        return {"result": [...]}

# unified_agent.py
DB_TOOL_DEFINITIONS = [{
    "type": "function",
    "function": {
        "name": "query_database",
        "description": "执行 SQL 查询",
        "parameters": {"sql": {"type": "string"}}
    }
}]

def _execute_tool_call(self, tool_call):
    if tool_name == "query_database":
        return self.db_tools.query_database(**arguments)
```

---

### 3️⃣ **新增模型**

**步骤：**
1. 在 `core/chat.py` 中添加新模型客户端类
2. 在 `agent_config.py` 中注册模型
3. 在 `UnifiedAgent.__init__()` 中添加客户端初始化逻辑

**示例：添加 Claude 支持**
```python
# core/chat.py
class ClaudeClient:
    def chat_with_functions(self, messages, tools, **kwargs):
        # 调用 Claude API
        return {"content": ..., "tool_calls": [...]}

# agent_config.py
SUPPORTED_MODELS = {
    "qwen": [...],
    "deepseek": [...],
    "openai": [...],
    "claude": ["claude-3-opus", "claude-3-sonnet"]  # 新增
}

# unified_agent.py
def __init__(...):
    if model_type == "claude":
        self.client = ClaudeClient(api_key)
```

---

### 4️⃣ **新增系统提示词**

**步骤：**
1. 在 `config/system_prompts.py` 中添加新提示词
2. 使用 `prompt <type>` 命令切换

**示例：**
```python
# system_prompts.py
PROMPTS = {
    # ... 现有提示词
    "creative_writer": {
        "name": "创意作家",
        "description": "擅长创意写作、故事构思、文案撰写",
        "content": "你是一位富有创造力的作家..."
    }
}
```

---

## 📊 关键指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 最大工具调用轮数 | 20 | 防止死循环 |
| 上下文窗口大小 | 8000 tokens | 自动截断 |
| 网络请求超时 | 10 秒 | 可配置 |
| 网页内容最大长度 | 50000 字符 | 防止 Token 超限 |
| 自动保存间隔 | 60 秒 | 定期持久化 |
| 知识库文档最大长度 | 10000 字符 | PDF 可设为 50000 |

---

## 🎯 使用示例

### 启动 Chat
```bash
# 激活虚拟环境并运行
source .venv/bin/activate && python3 -m component.chat.unified_chat
```

### 交互示例
```
👤 你: 帮我读取淘宝竞品报告

🤔 思考中...
🔧 调用了 2 个工具:
   1. 📁 list_documents - ✅
      找到 12 个文档
   2. 📁 read_document - ✅
      内容长度: 8532 字符

🤖 助手: 我已经读取了淘宝AI直播竞品综合分析报告，报告主要内容包括...

📊 Token 统计: 提示词 1234 + 回复 567 = 总计 1801 | ⏱️  耗时: 3.45秒
```

---

## 📚 参考资料

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [prompt_toolkit 文档](https://python-prompt-toolkit.readthedocs.io/)

---

**文档版本**: v1.0  
**最后更新**: 2025-11-13  
**维护者**: Thomas Chan
