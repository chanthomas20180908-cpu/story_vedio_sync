# 会话管理系统文档

## 🎯 概述

增强版会话管理系统为多轮对话提供了完整的生命周期管理，解决了原版本的所有限制。

## ✨ 核心改进

### 1. **Token 计数和上下文窗口管理** ✅

#### 功能
- 自动估算消息的 Token 数量
- 实时监控上下文使用情况
- 自动截断超长对话历史
- 保留重要的 system 消息

#### 实现
```python
from component.chat.session_manager import TokenCounter, ContextWindowManager

# Token 计数
tokens = TokenCounter.estimate_tokens("你好，世界！")  # 约 5 tokens

# 上下文管理
manager = ContextWindowManager(model="qwen-plus", max_ratio=0.7)
truncated_messages = manager.truncate_messages(messages)  # 自动截断
stats = manager.get_stats(messages)  # 获取统计
```

#### 模型限制
| 模型 | 上下文窗口 | 最大使用（70%） |
|------|-----------|---------------|
| qwen-turbo | 8K | 5.6K |
| qwen-plus | 32K | 22.4K |
| deepseek-v3 | 64K | 44.8K |
| gpt-4-turbo | 128K | 89.6K |

### 2. **多会话管理系统** ✅

#### 功能
- 创建多个独立会话
- 会话间自由切换
- 列出所有会话
- 删除不需要的会话
- 每个会话独立的模型和配置

#### 使用

**创建会话**
```bash
# 交互式
new

# 代码中
session_id = session_manager.create_session(
    model="qwen-plus",
    model_type="qwen",
    system_prompt="你是一个AI助手"
)
```

**切换会话**
```bash
switch <session_id>  # 例如: switch abc123de
```

**列出会话**
```bash
sessions

# 输出示例:
# [✓] abc123de - qwen/qwen-plus - 15 条消息 - 更新: 2025-10-27 15:30:45
# [ ] def456gh - deepseek/deepseek-r1 - 8 条消息 - 更新: 2025-10-27 14:20:15
```

**删除会话**
```bash
delete <session_id>
```

### 3. **SQLite 持久化存储** ✅

#### 功能
- 所有会话自动保存到数据库
- 程序重启后自动恢复会话
- 崩溃安全
- 支持导出/导入

#### 数据库位置
```
项目根目录/Data/chat_sessions.db
```

#### 表结构
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    model_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    conversation_history TEXT NOT NULL  -- JSON 格式
)
```

#### 自动保存机制
- 每次对话后自动保存
- 退出程序时自动保存
- 手动触发: `session_manager.save_current_session()`

### 4. **高级对话功能** ✅

#### 消息历史查看
```bash
history

# 输出:
# [0] ⚙️ system: 你是一个有用的AI助手，擅长回答各种问题。
# [1] 👤 user: 你好
# [2] 🤖 assistant: 你好！有什么可以帮助你的吗？
```

#### 对话回溯
```bash
rollback <index>  # 回滚到指定消息，删除之后的所有内容

# 例如: rollback 1  # 回滚到第1条消息，删除第2条及之后的所有消息
```

#### 重新生成回答
```bash
regenerate  # 删除最后一条助手回答并重新生成
```

#### 会话统计
```bash
stats

# 输出:
# {
#   "session_id": "abc123de",
#   "model": "qwen/qwen-plus",
#   "total_messages": 15,
#   "api_messages": 12,  # 实际发送给API的消息数（截断后）
#   "context_stats": {
#     "tokens_used": 450,
#     "tokens_limit": 22400,
#     "usage_ratio": 2.01,
#     "remaining_tokens": 21950
#   }
# }
```

#### 清空历史
```bash
clear  # 清空当前会话历史（保留系统消息）
```

## 📚 完整命令列表

### 基本命令
| 命令 | 说明 |
|------|------|
| `exit` / `quit` | 退出对话（自动保存） |
| `clear` | 清空当前会话历史 |
| `history` | 查看对话历史 |
| `stats` | 查看会话统计 |

### 会话管理
| 命令 | 说明 |
|------|------|
| `sessions` | 列出所有会话 |
| `new` | 创建新会话 |
| `switch <id>` | 切换到指定会话 |
| `delete <id>` | 删除指定会话 |

### 高级功能
| 命令 | 说明 |
|------|------|
| `rollback <n>` | 回滚到第 n 条消息 |
| `regenerate` | 重新生成最后一条回答 |
| `toggle_summary` | 切换摘要显示 |
| `toggle_thinking` | 切换思考显示 |

## 🚀 快速开始

### 运行增强版
```bash
python component/chat/chat_multiround_v2.py
```

### 代码中使用
```python
from component.chat.chat_multiround_v2 import EnhancedMultiRoundChat
from component.chat.session_manager import SessionManager

# 初始化
session_manager = SessionManager()
chat = EnhancedMultiRoundChat(api_key=your_api_key, session_manager=session_manager)

# 创建会话
session_id = session_manager.create_session(
    model="qwen-plus",
    model_type="qwen",
    system_prompt="你是一个AI助手"
)

# 对话
result = chat.chat("你好")
print(result['answer'])

# 查看统计
session = session_manager.get_session()
stats = session.get_stats()
print(stats)

# 保存会话
session_manager.save_current_session()
```

## 📊 对比原版与增强版

| 功能 | 原版 | 增强版 |
|------|------|--------|
| Token 计数 | ❌ 无 | ✅ 自动估算 |
| 上下文管理 | ❌ 无限制，易超限 | ✅ 自动截断 |
| 会话管理 | ❌ 单一全局会话 | ✅ 多会话支持 |
| 持久化 | ❌ 手动导出JSON | ✅ SQLite 自动保存 |
| 消息编辑 | ❌ 不支持 | ✅ 编辑/删除/回溯 |
| 崩溃恢复 | ❌ 数据丢失 | ✅ 自动恢复 |
| 重新生成 | ❌ 不支持 | ✅ 支持 |
| 统计信息 | ⚠️ 基本信息 | ✅ 详细统计 |

## 🎨 使用场景

### 场景 1: 长对话自动管理
```
问题: 对话太长导致API报错
解决: 系统自动截断旧消息，保持在上下文窗口内
```

### 场景 2: 多任务并行
```
场景: 同时进行代码调试、文档编写、问题咨询
操作:
1. new  # 创建"代码调试"会话
2. new  # 创建"文档编写"会话  
3. new  # 创建"问题咨询"会话
4. switch <id>  # 随时切换
```

### 场景 3: 回答不满意重新生成
```bash
你: 解释一下量子力学
AI: [给出回答]
你: regenerate  # 不满意，重新生成
AI: [给出新回答]
```

### 场景 4: 对话分支探索
```bash
[对话进行到第10条]
你: rollback 5  # 回到第5条，尝试不同方向
你: [从第5条开始新的对话分支]
```

## ⚙️ 配置说明

在 `config/config.py` 中:

```python
# 聊天显示配置
CHAT_SHOW_SUMMARY = True   # 显示 Token 消耗等摘要信息
CHAT_SHOW_THINKING = True  # 显示深度思考模型的思考过程
```

## 🔧 高级用法

### 自定义 Token 计数策略
```python
from component.chat.session_manager import TokenCounter

class MyTokenCounter(TokenCounter):
    @staticmethod
    def estimate_tokens(text: str) -> int:
        # 自定义实现
        return len(text) // 3  # 更激进的估算
```

### 自定义上下文截断策略
```python
from component.chat.session_manager import ContextWindowManager

class MyContextManager(ContextWindowManager):
    def truncate_messages(self, messages):
        # 自定义截断逻辑
        # 例如：总结旧消息而不是删除
        pass
```

### 批量会话操作
```python
manager = SessionManager()

# 导出所有会话
for session_id in manager.sessions.keys():
    session = manager.get_session(session_id)
    session.export_history(f"backup_{session_id}.json")

# 清理旧会话
for session_id, session in list(manager.sessions.items()):
    days_old = (datetime.now() - session.updated_at).days
    if days_old > 30:
        manager.delete_session(session_id)
```

## 🐛 故障排查

### 问题 1: 数据库锁定
```
错误: database is locked
原因: 多个进程同时访问数据库
解决: 确保只有一个程序实例运行
```

### 问题 2: Token 估算不准确
```
现象: 仍然偶尔超出上下文限制
原因: 使用简化的字符估算方法
解决: 调整 max_ratio 到更保守的值（如 0.6）
```

### 问题 3: 会话恢复失败
```
错误: JSON decode error
原因: 数据库中的历史记录损坏
解决: 删除对应会话或清空数据库
```

## 📈 性能建议

1. **Token 估算**: 简化版本速度快但不够精确，生产环境建议使用 `tiktoken` 库
2. **数据库大小**: 定期清理旧会话，避免数据库过大
3. **内存使用**: 长时间运行时定期重启，释放内存
4. **并发控制**: 避免多进程同时操作同一数据库

## 🔒 安全注意事项

1. **敏感信息**: 数据库中存储明文对话内容，注意保护
2. **API 密钥**: 不要在系统提示词中包含 API 密钥
3. **数据备份**: 定期备份 `chat_sessions.db`
4. **权限控制**: 设置数据库文件的合适权限

## 🎓 最佳实践

1. **会话命名**: 虽然是 UUID，但可以在系统提示词中包含任务描述
2. **定期保存**: 重要对话后手动触发 `stats` 确认已保存
3. **合理分会话**: 不同主题使用不同会话，便于管理
4. **监控 Token**: 关注上下文使用率，及时清理或分会话
5. **备份策略**: 每周备份一次数据库文件

## 📝 更新日志

### v2.0 (2025-10-27)
- ✅ 添加 Token 计数和上下文窗口管理
- ✅ 实现多会话管理系统
- ✅ 添加 SQLite 持久化存储
- ✅ 实现高级对话功能（编辑/删除/回溯）
- ✅ 自动保存机制
- ✅ 崩溃恢复功能

### v1.0 (Initial)
- 基础多轮对话功能
- 简单的历史记录管理
- 手动 JSON 导入导出
