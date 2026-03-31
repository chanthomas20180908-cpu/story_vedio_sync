# 统一 Chat 系统

## 📁 新架构目录结构

```
component/chat/
├── config/                          # 配置模块
│   ├── __init__.py
│   └── agent_config.py             # Agent 配置（模式、模型、工具等）
│
├── core/                            # 核心模块（业务逻辑层）
│   ├── __init__.py
│   ├── chat.py                     # 基础 AI 客户端
│   ├── session_manager.py          # 会话管理器
│   └── unified_agent.py            # 统一 Agent（工具编排）
│
├── tools/                           # 工具模块
│   ├── __init__.py
│   ├── kb_config.py                # 知识库配置
│   ├── kb_tools.py                 # 知识库工具
│   └── web_tools.py                # 网络访问工具
│
├── unified_chat.py                  # 🌟 统一交互入口
│
└── [旧文件保留]                     # 旧版本文件（待清理）
    ├── chat.py
    ├── chat_*.py
    ├── interactive_chat.py
    └── knowledge_base/
```

## 🚀 快速开始

### 运行统一 Chat

```bash
python component/chat/unified_chat.py
```

### 程序化使用

```python
from component.chat.core.unified_agent import UnifiedAgent
from component.chat.config.agent_config import AgentMode

# 创建 Agent
agent = UnifiedAgent(
    api_key="your_api_key",
    model_type="qwen",
    model="qwen-plus",
    mode=AgentMode.FULL  # 全功能模式
)

# 调用
result = agent.chat(
    user_input="搜索知识库中关于AI的文档",
    conversation_history=[]
)

print(result['answer'])
```

## 🎯 核心模块说明

### 1. `unified_agent.py` - 业务逻辑层

**职责**:
- ✅ AI 模型调用 (Qwen/DeepSeek/OpenAI)
- ✅ Function Calling 处理
- ✅ 工具编排与执行
- ✅ 多轮工具调用逻辑
- ✅ Token 计数与统计

**特点**:
- ❌ 不关心用户交互
- ❌ 不处理终端输入输出
- ✅ 只负责"思考"和"执行"
- ✅ 可被任何界面调用 (CLI/Web/API)

**关键方法**:
```python
agent.chat(user_input, conversation_history) → Dict
agent.set_mode(AgentMode.KB_ONLY)
agent._get_available_tools() → List[Dict]
agent._execute_tool(function_name, arguments) → Dict
```

---

### 2. `unified_chat.py` - 交互表现层

**职责**:
- ✅ prompt_toolkit 交互界面
- ✅ 命令解析与路由
- ✅ 会话生命周期管理
- ✅ 显示格式化输出
- ✅ 用户配置管理

**特点**:
- ✅ 处理所有用户交互
- ✅ 管理显示逻辑
- ❌ 不涉及 AI 调用细节
- ❌ 不实现工具逻辑

**支持命令**:
```bash
# 基本命令
exit/quit          # 退出程序
clear              # 清空历史
history            # 查看历史
sessions           # 列出会话
model              # 显示当前模型

# 模式切换
mode pure          # 纯对话模式
mode kb            # 仅知识库
mode web           # 仅网络
mode full          # 全功能（默认）

# 模型切换 🆕
switch qwen        # 切换到 Qwen 模型
switch deepseek    # 切换到 DeepSeek 模型
switch openai      # 切换到 OpenAI 模型

# 设置
toggle_summary     # 切换工具摘要显示
toggle_stats       # 切换 Token 统计显示
```

---

### 3. `agent_config.py` - 配置管理

**包含配置**:
- 工具协议类型 (Function Call / MCP)
- Agent 工作模式 (PURE / KB_ONLY / WEB_ONLY / FULL)
- 模型配置 (支持的模型列表)
- 知识库配置 (路径、文件类型)
- 网络访问配置 (超时、内容长度)
- 交互界面配置 (摘要显示、统计显示)

**使用示例**:
```python
from component.chat.config.agent_config import AgentConfig, AgentMode

# 获取模式配置
config = AgentConfig.get_mode_config(AgentMode.FULL)
# → {"enable_kb": True, "enable_web": True}

# 验证模型
is_valid = AgentConfig.validate_model("qwen", "qwen-plus")

# 切换工具协议（预留 MCP）
AgentConfig.TOOL_PROTOCOL = ToolProtocol.MCP
```

---

## 🔧 Agent 工作模式

| 模式 | 知识库 | 网络访问 | 说明 |
|------|-------|---------|------|
| `PURE` | ❌ | ❌ | 纯对话，不使用任何工具 |
| `KB_ONLY` | ✅ | ❌ | 仅知识库查询 |
| `WEB_ONLY` | ❌ | ✅ | 仅网络访问 |
| `FULL` | ✅ | ✅ | 全功能（默认） |

**动态切换模式**:
```python
# 在对话中切换
mode kb          # 切换到仅知识库模式

# 程序化切换
agent.set_mode(AgentMode.WEB_ONLY)
```

---

## 🛠️ 工具集成

### 知识库工具 (kb_tools.py)

- `list_documents()` - 列出文档
- `read_document()` - 读取文档
- `create_document()` - 创建文档
- `search_in_documents()` - 搜索文档

### 网络访问工具 (web_tools.py)

- `fetch_url()` - 访问网页
- `get_page_summary()` - 获取网页摘要
- `search_in_page()` - 页面内搜索

---

## 📊 架构优势

### 1. 关注点分离
- **Agent**: 专注 AI 能力
- **Chat**: 专注用户体验
- **Tools**: 专注工具实现

### 2. 可测试性
- Agent 可独立单元测试，无需模拟终端
- 工具可独立测试

### 3. 可复用性
- Agent 可被 Gradio/API 等其他界面调用
- 工具可被其他模块使用

### 4. 可扩展性
- 新增工具只需修改 Agent
- 新增命令只需修改 Chat
- **预留 MCP 协议接口**

### 5. 可维护性
- 修改交互不影响业务逻辑
- 修改业务不影响界面

---

## 🔄 迁移到 MCP 协议

当前架构已预留 MCP 扩展接口，未来迁移改动量极小：

**需要改动**:
1. 创建 `core/mcp_adapter.py` (约 100-150 行)
2. 修改 `unified_agent.py` 添加 MCP 分支 (约 20% 改动)
3. 配置文件添加 `TOOL_PROTOCOL = ToolProtocol.MCP`

**无需改动**:
- ✅ `unified_chat.py` - 交互层
- ✅ `kb_tools.py` / `web_tools.py` - 工具实现
- ✅ `session_manager.py` - 会话管理

**一行切换协议**:
```python
# agent_config.py
TOOL_PROTOCOL = ToolProtocol.MCP  # 从 FUNCTION_CALL 切换到 MCP
```

---

## 📚 依赖关系

```
unified_chat.py
    ├─→ UnifiedAgent (core/unified_agent.py)
    │       ├─→ QwenClient / DeepSeekClient (core/chat.py)
    │       ├─→ KnowledgeBaseTools (tools/kb_tools.py)
    │       └─→ WebTools (tools/web_tools.py)
    │
    ├─→ SessionManager (core/session_manager.py)
    └─→ AgentConfig (config/agent_config.py)
```

---

## 🧹 旧文件清理计划

待新架构测试稳定后，可删除以下旧文件：

```bash
# 可删除的旧文件
component/chat/interactive_chat.py
component/chat/chat_with_kb.py
component/chat/chat_with_web.py
component/chat/chat_multiround_v2.py
component/chat/chat_dp.py
component/chat/chat_multiround.py

# 可删除的旧目录
component/chat/knowledge_base/  # 已迁移到 tools/
```

**注意**: 删除前请确认所有功能已迁移且测试通过！

---

## 🎓 学习路径

1. **新手**: 直接运行 `unified_chat.py`，体验交互功能
2. **开发者**: 阅读 `unified_agent.py`，了解业务逻辑
3. **架构师**: 参考 `agent_config.py`，理解配置管理
4. **集成者**: 使用 `UnifiedAgent` 集成到其他系统

---

## 📞 FAQ

**Q: 如何添加新工具？**
A: 在 `tools/` 下创建工具类，在 `unified_agent.py` 中添加工具定义

**Q: 如何切换工作模式？**
A: 对话中输入 `mode <模式>`，例如 `mode kb` 或 `mode full`

**Q: 如何切换 AI 模型？**
A: 对话中输入 `switch <模型类型>`，例如:
- `switch qwen` - 切换到通义千问
- `switch deepseek` - 切换到 DeepSeek
- `switch openai` - 切换到 OpenAI

然后从显示的列表中选择具体模型。模型切换后会立即生效，之前的对话历史保持不变。

**Q: 如何禁用某个功能？**
A: 使用 `mode` 命令切换，或设置 `enable_kb=False` / `enable_web=False`

**Q: 如何查看历史会话？**
A: 输入 `sessions` 查看所有会话，输入 `history` 查看当前对话历史

---

**版本**: v2.0.0  
**更新时间**: 2025-10-28  
**维护者**: @thomaschan
