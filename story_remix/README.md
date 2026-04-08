# 故事混搭生成系统

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 到 `.env`，填写LLM配置：

```bash
cp .env.example .env
# 编辑 .env 文件，填写 OPENAI_API_KEY 等配置
```

### 2. 启动应用

```bash
python3 run_story_remix.py
```

访问: http://127.0.0.1:7861

### 3. 使用流程

1. **项目管理**: 创建新项目
2. **素材管理**: 上传故事文件（.md/.txt/.epub）
3. **对话编辑**: 选择片段，输入指令生成新故事
4. **预览导出**: 导出Markdown或生成视频

## 架构说明

```
story_remix/
├── core/
│   ├── project_manager.py   # 项目管理
│   └── story_engine.py       # 故事生成引擎（已集成LLM）
├── parsers/
│   └── file_parser.py        # 文件解析器
└── ui/
    └── gradio_app.py         # Gradio界面
```

## 数据存储

```
data/projects/<project_id>/
├── metadata.json             # 项目元数据
├── uploads/                  # 上传的原始文件
├── segments/                 # 解析的片段
└── generations/              # 生成的版本
```

## 功能特性

- 多格式支持: md/txt/epub
- 智能分段: 自动按段落分割
- 对话式编辑: 多轮对话优化故事
- 版本管理: 保存所有生成历史
- 导出功能: Markdown导出，可对接现有视频流水线
- **真实LLM集成**: 使用OpenAI兼容API生成故事

## LLM配置

支持任何OpenAI兼容的API：

```bash
# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# DeepSeek
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 其他兼容服务
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama2
```

## 下一步开发

- [x] 集成LLM（使用component/chat/core/chat.py）
- [ ] 片段标签自动生成（情绪、风格分析）
- [ ] 视频生成集成（调用workflow/story_video_001）
- [ ] epub解析依赖（ebooklib, beautifulsoup4）
