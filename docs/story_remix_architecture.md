# 故事混搭生成系统架构方案

## Context（背景）

当前项目 `story_vedio_sync` 是一个端到端的 AI 视频生成系统，能够将单个文本故事转换为带音频、字幕和视频的完整产品。用户现在希望扩展功能：

**新需求**：输入多个故事文件（md/epub 等格式），AI 自动拆分并混搭，合成一个新的故事。

**现有能力**：
- 完整的文本→视频流水线（7步工作流）
- LLM 集成（Gemini/OpenAI-compat）
- 文件处理工具（util_file.py）
- Gradio Web UI
- Agent 框架（Function Calling）

**设计目标**：在现有架构基础上，新增故事混搭模块，复用现有的视频生成流水线。

---

## 架构设计

### 1. 整体架构（会话式创作工具）

**核心差异**：从「一次性工作流」转变为「会话式创作」

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI Layer (Gradio)                   │
│                                                               │
│  🏠 项目管理                                                 │
│  - 项目列表（卡片式，显示最近项目）                           │
│  - 新建项目/打开项目/删除项目                                 │
│  - 项目元数据显示（标题、创建时间、素材数量）                   │
│                                                               │
│  📚 素材管理                                                 │
│  - 文件上传（多文件支持 md/epub/txt，拖拽上传）                │
│  - 文件列表展示（来源、大小、状态）                           │
│  - 片段展示与选择（卡片式，支持勾选）                          │
│  - 片段标签（情绪、风格、来源故事，支持修改）                   │
│                                                               │
│  💬 对话式编辑                                               │
│  - 聊天输入框（支持 Markdown，发送消息）                       │
│  - 历史记录（轮次展示，显示角色和消息）                       │
│  - 版本管理（显示历史版本，支持回滚）                         │
│                                                               │
│  📖 预览与导出                                               │
│  - 实时预览（Markdown 渲染）                                 │
│  - 导出 md 文件（用于视频生成）                               │
│  - 导出为视频（直接调用现有 workflow）                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Project/Session Management Layer                 │
│                                                               │
│  🔄 会话管理                                                 │
│  - 会话状态持久化（刷新页面不丢失）                           │
│  - 操作历史记录（用于撤销/重做）                               │
│  - 项目结构管理（data/projects/<timestamp>/）                  │
│                                                               │
│  📦 素材仓库                                                 │
│  - 上传文件存储（projects/<id>/uploads/）                     │
│  - 分析结果存储（projects/<id>/analyzed/）                    │
│  - 片段存储（projects/<id>/segments/）                        │
│  - 生成历史存储（projects/<id>/generations/）                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Story Remix Engine Layer                         │
│                                                               │
│  📄 文件解析与预处理（Phase 1）                               │
│  ├─ 格式转换器（epub/md/txt → 统一文本）                     │
│  ├─ 元数据提取（标题、作者、章节结构）                        │
│  └─ 文本分段（按章节/段落/语义单元）                         │
│                                                               │
│  🧠 故事理解与拆解（Phase 2）                                 │
│  ├─ 故事元素提取（人物、情节、场景、冲突、主题）              │
│  ├─ 叙事结构分析（起承转合、时间线、视角）                    │
│  └─ 片段标注（情绪、节奏、风格标签）                         │
│                                                               │
│  ✨ 智能生成与对话（Phase 3-4）                               │
│  ├─ 片段混搭（用户勾选 + AI 建议）                           │
│  ├─ 多轮对话（修改、扩展、调整风格）                          │
│  ├─ 版本管理（每次修改产生新快照）                           │
│  └─ 输出标准化（Markdown，与现有 workflow 完全兼容）           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Existing Video Generation Workflow (复用)             │
│  Step 1-7: 口播稿生成 → TTS → 字幕 → 分镜 → 生图 → 视频合成    │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. 核心模块设计

#### **Module 1: 文件解析器（File Parser）**

**位置**：`component/file_parser/`

**功能**：
- 支持多格式输入（md/epub/txt/docx）
- 统一输出为结构化文本对象

**实现**：
```python
# component/file_parser/parser.py
class StoryDocument:
    """统一的故事文档对象"""
    title: str
    author: str
    chapters: List[Chapter]  # 章节列表
    metadata: Dict[str, Any]
    
class Chapter:
    """章节对象"""
    title: str
    content: str
    order: int
    paragraphs: List[str]

class FileParser:
    """多格式解析器"""
    def parse(self, file_path: str) -> StoryDocument:
        ext = Path(file_path).suffix.lower()
        if ext == '.md':
            return self._parse_markdown(file_path)
        elif ext == '.epub':
            return self._parse_epub(file_path)
        elif ext == '.txt':
            return self._parse_text(file_path)
        # ...
    
    def _parse_markdown(self, path: str) -> StoryDocument:
        """解析 Markdown（按 # 标题分章节）"""
        # 使用 markdown-it-py 或正则解析
        
    def _parse_epub(self, path: str) -> StoryDocument:
        """解析 EPUB（使用 ebooklib）"""
        # 提取 HTML 内容 → 清洗标签 → 分章节
```

**依赖库**：
- `ebooklib`（EPUB 解析）
- `markdown-it-py`（Markdown 解析）
- `python-docx`（可选，支持 Word）

---

#### **Module 2: 故事分析器（Story Analyzer）**

**位置**：`component/story_remix/analyzer.py`

**功能**：
- 使用 LLM 提取故事元素
- 生成结构化的故事元数据

**实现**：
```python
class StoryElement:
    """故事元素"""
    characters: List[Dict]  # [{"name": "张三", "role": "主角", "traits": [...]}]
    plots: List[Dict]       # [{"summary": "...", "type": "冲突/转折/高潮"}]
    scenes: List[Dict]      # [{"location": "...", "time": "...", "mood": "..."}]
    themes: List[str]       # ["爱情", "复仇", "成长"]
    style: Dict             # {"tone": "悲剧", "pov": "第一人称", "pace": "快节奏"}

class StoryAnalyzer:
    """故事分析器（基于 LLM）"""
    def __init__(self, llm_client):
        self.llm = llm_client
        
    async def analyze(self, document: StoryDocument) -> StoryElement:
        """分析单个故事"""
        # 构造提示词：提取人物、情节、场景、主题
        prompt = self._build_analysis_prompt(document)
        response = await self.llm.chat(prompt, response_format="json")
        return StoryElement.from_dict(response)
    
    def _build_analysis_prompt(self, doc: StoryDocument) -> str:
        """构造分析提示词"""
        return f"""
        分析以下故事，提取关键元素（JSON 格式）：
        
        故事标题：{doc.title}
        故事内容：
        {doc.get_full_text()[:5000]}  # 限制长度，避免超 token
        
        请提取：
        1. 主要人物（姓名、角色、性格特征）
        2. 核心情节（起因、发展、高潮、结局）
        3. 关键场景（地点、时间、氛围）
        4. 主题标签（3-5个关键词）
        5. 叙事风格（语气、视角、节奏）
        """
```

**提示词模板**：存储在 `data/remix_prompts.py`

---

#### **Module 3: 故事混搭引擎（Story Remixer）**

**位置**：`component/story_remix/remixer.py`

**功能**：
- 实现多种混搭策略
- 生成连贯的新故事

**混搭策略**：

1. **随机拼接模式（Random Splice）**
   - 从每个故事随机抽取片段
   - 按时间线/情绪曲线排序
   - LLM 生成过渡段落

2. **主题融合模式（Theme Fusion）**
   - 提取共同主题（如"爱情+科幻"）
   - 选择相关片段
   - 重新编织为统一叙事

3. **角色互换模式（Character Swap）**
   - 将故事 A 的角色放入故事 B 的情节
   - 保持角色性格，改变事件背景

4. **情节嫁接模式（Plot Grafting）**
   - 提取故事 A 的情节结构
   - 填充故事 B 的场景/对话
   - 生成混合叙事

**实现**：
```python
class RemixStrategy(Enum):
    RANDOM_SPLICE = "random"
    THEME_FUSION = "theme"
    CHARACTER_SWAP = "character"
    PLOT_GRAFT = "plot"

class StoryRemixer:
    """故事混搭引擎"""
    def __init__(self, llm_client):
        self.llm = llm_client
        
    async def remix(
        self,
        stories: List[Tuple[StoryDocument, StoryElement]],
        strategy: RemixStrategy,
        params: Dict
    ) -> str:
        """混搭生成新故事"""
        if strategy == RemixStrategy.RANDOM_SPLICE:
            return await self._random_splice(stories, params)
        elif strategy == RemixStrategy.THEME_FUSION:
            return await self._theme_fusion(stories, params)
        # ...
    
    async def _random_splice(self, stories, params) -> str:
        """随机拼接策略"""
        # 1. 从每个故事抽取 N 个片段
        segments = []
        for doc, element in stories:
            selected = self._select_segments(
                doc, 
                count=params.get('segments_per_story', 3),
                min_length=params.get('min_segment_length', 200)
            )
            segments.extend(selected)
        
        # 2. 打乱并排序（可选：按情绪曲线）
        random.shuffle(segments)
        
        # 3. LLM 生成过渡 + 统一风格
        new_story = await self._generate_transitions(segments, params)
        return new_story
    
    async def _generate_transitions(self, segments, params) -> str:
        """生成过渡段落，确保连贯性"""
        prompt = f"""
        将以下故事片段混搭成一个新故事：
        
        片段列表：
        {self._format_segments(segments)}
        
        要求：
        1. 在片段之间生成自然的过渡段落
        2. 统一叙事视角为：{params.get('pov', '第三人称')}
        3. 保持整体风格：{params.get('style', '悬疑')}
        4. 目标长度：{params.get('target_length', 2000)} 字
        5. 确保逻辑连贯，人物行为合理
        
        输出完整的新故事（Markdown 格式）。
        """
        response = await self.llm.chat(prompt)
        return response
```

---

#### **Module 4: 会话管理系统（Session Management）**

**位置**：`component/story_remix/session/`（新增模块）

**核心职责**：管理创作会话状态，实现"持久化素材"

**结构**：
```
component/story_remix/session/
├── __init__.py
├── project_manager.py              # 项目 CRUD 管理
├── session_state.py                # 会话状态管理
└── storage.py                      # 文件存储（读写 JSON/文本）
```

**项目结构（文件系统）**：
```
data/projects/
├── 20260407_143025_123/           # 项目目录：<timestamp>_<run_id>
│   ├── project.json               # 项目元数据
│   ├── uploads/                   # 上传的原始文件
│   │   ├── story1.md
│   │   └── story2.epub
│   ├── analyzed/                  # 分析结果
│   │   ├── story1.json            # 包含人物、情节、场景、标签
│   │   └── story2.json
│   ├── segments/                  # 拆分后的片段
│   │   ├── story1/
│   │   │   ├── seg001.txt
│   │   │   ├── seg002.txt
│   │   │   └── seg003.txt
│   │   └── story2/
│   └── generations/               # 生成的历史版本
│       ├── version_001.md         # 初始版本（全部片段拼接）
│       ├── version_002.md         # 用户修改了结尾
│       └── version_003.md         # 用户要求扩展中间部分
```

**主要代码实现**：
```python
# component/story_remix/session/project_manager.py
class ProjectManager:
    """项目管理类"""
    
    def list_projects(self, limit: int = 10) -> List[Dict]:
        """列出最近的项目"""
        project_dir = Path(cfg.PROJECTS_DIR)
        if not project_dir.exists():
            project_dir.mkdir(parents=True)
        
        projects = []
        for d in sorted(
            project_dir.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ):
            if d.is_dir():
                try:
                    meta_path = d / "project.json"
                    if meta_path.exists():
                        meta = json.loads(meta_path.read_text())
                        projects.append({
                            "id": d.name,
                            "name": meta.get("name", "未命名项目"),
                            "create_time": meta.get("create_time"),
                            "file_count": len(list((d / "uploads").glob("*"))),
                            "gen_count": len(list((d / "generations").glob("version_*.md")))
                        })
                except Exception as e:
                    logger.warning(f"Invalid project {d.name}: {e}")
        
        return projects[:limit]
    
    def save_project(self, project_id: str, content: str, version: int = None) -> str:
        """保存故事版本"""
        gen_dir = Path(cfg.PROJECTS_DIR) / project_id / "generations"
        gen_dir.mkdir(parents=True, exist_ok=True)
        
        if version is None:
            # 自动计算版本号
            existing = list(gen_dir.glob("version_*.md"))
            version = len(existing) + 1
        
        version_str = f"version_{version:03d}.md"
        save_path = gen_dir / version_str
        save_path.write_text(content)
        return version_str
```

#### **Module 5: 多轮对话引擎（Multi-turn Dialogue）**

**位置**：`component/story_remix/dialogue/`（新增模块）

**核心职责**：基于现有的 `UnifiedAgent`，实现故事编辑的多轮对话

**结构**：
```
component/story_remix/dialogue/
├── __init__.py
├── dialogue_engine.py              # 对话引擎主类
├── tools.py                        # 故事编辑工具（修改/扩展/删除）
└── prompts.py                      # 对话系统提示词
```

**主要实现**：
```python
# component/story_remix/dialogue/dialogue_engine.py
class StoryEditEngine:
    """故事编辑引擎 - 基于多轮对话"""
    
    def __init__(self):
        # 复用现有的 Agent
        self.agent = UnifiedAgent(
            mode=AgentMode.CHAT,
            tools=self._get_edit_tools()
        )
        self.conversation_history = []
    
    async def process(
        self,
        user_message: str,
        current_story: str,
        project_context: Dict
    ) -> Dict:
        """
        处理用户的编辑请求
        
        Args:
            user_message: 用户的自然语言指令（如"把张三换成李四"）
            current_story: 当前版本的故事文本
            project_context: 项目上下文（人物列表、场景列表、片段库）
        
        Returns:
            {
                "new_story": "...",      // 修改后的新故事
                "explanation": "...",    // 解释做了什么修改
                "diff": "...",           // 差异对比
                "action": "replace/expand/delete"
            }
        """
        # 构建系统提示词
        system_prompt = self._build_system_prompt(project_context)
        
        # 调用 Agent 处理
        response = await self.agent.chat_with_tools(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=self.conversation_history,
            extra_context={"current_story": current_story}
        )
        
        # 记录对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    def _get_edit_tools(self) -> List:
        """获取故事编辑工具（Function Calling）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "replace_character",
                    "description": "替换故事中的角色名",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "old_name": {"type": "string", "description": "旧角色名"},
                            "new_name": {"type": "string", "description": "新角色名"}
                        },
                        "required": ["old_name", "new_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "expand_section",
                    "description": "扩展故事的某个部分",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string", "description": "要扩展的部分（'开头'/'中间'/'结尾'或段落引用）"},
                            "target_length": {"type": "integer", "description": "目标长度（字）"}
                        },
                        "required": ["section"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "change_style",
                    "description": "改变故事的整体风格",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "style": {"type": "string", "description": "目标风格（'悬疑'/'科幻'/'爱情'/'奇幻'）"},
                            "pov": {"type": "string", "description": "叙事视角（'第一人称'/'第三人称'）"}
                        },
                        "required": ["style"]
                    }
                }
            }
        ]
```

---

### 3. 数据流设计（会话式）

```
用户操作：新建项目 → 上传文件 → 解析文件 → 分析故事 → 选择片段 → 对话编辑 → 导出

──────────────────────────────────────────────────────────────────

【项目创建】
输入：用户点击"新建项目"
存储：data/projects/<timestamp>/
      ├── project.json          // {"name": "未命名项目", "create_time": "..."}
      ├── uploads/              // 空文件夹
      ├── analyzed/             // 空文件夹
      ├── segments/             // 空文件夹
      └── generations/          // 空文件夹

【文件上传】
输入：用户上传 story1.md 和 story2.epub
存储：data/projects/<id>/uploads/
      ├── story1.md
      └── story2.epub

【文件解析与分析（Phase 1-2）】
输出：data/projects/<id>/analyzed/
      ├── story1.json
      └── story2.json
  字段：{
    "title": "...",
    "characters": [...],
    "plots": [...],
    "scenes": [...],
    "themes": [...],
    "style": {...}
  }

【片段拆分（Phase 2）】
输出：data/projects/<id>/segments/
      ├── story1/
      │   ├── seg001.txt        // "在一个遥远的未来，..."
      │   └── seg002.txt        // "张三站在废墟上，..."
      └── story2/
          ├── seg001.txt        // "夜幕降临，城市霓虹闪烁..."
          └── seg002.txt        // "机器人助手端来一杯咖啡..."

【初步生成（Phase 3）】
输入：用户勾选了某些片段，点击"生成初稿"
输出：data/projects/<id>/generations/version_001.md
      └── 内容："在一个遥远的未来，城市霓虹闪烁..."

【对话编辑（Phase 3-4）】
输入：用户发送消息 "把张三换成李四，背景换成古代"
输出：data/projects/<id>/generations/version_002.md

【再次编辑】
输入：用户发送消息 "结尾太急了，帮我扩展"
输出：data/projects/<id>/generations/version_003.md

【导出】
输入：用户点击"导出为 md 文件"
输出：data/projects/<id>/output.md

【生成视频】
输入：用户点击"导出为视频"
调用：activity_script_001.execute(output.md, profile="default")
输出：data/Data_results/script_results/<run_id>/06_video/output.mp4
```

---

### 4. Web UI 设计（会话式）

**位置**：`web/gradio_remix_app.py`（替代原方案的 UI）

**界面布局**：
```python
import gradio as gr
from component.story_remix.session.project_manager import ProjectManager

pm = ProjectManager()

def create_remix_ui():
    with gr.Blocks() as app:
        gr.Markdown("# 故事混搭创作器")
        
        # 全局状态
        with gr.Row():
            project_id = gr.State("")
            current_version = gr.State(0)
        
        # 第一行：项目管理（侧边栏）
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📁 项目管理")
                
                # 项目列表
                project_list = gr.Dataframe(
                    headers=["项目ID", "名称", "创建时间", "文件数", "版本数"],
                    datatype=["str", "str", "str", "number", "number"],
                    col_count=(5, "fixed"),
                    label="最近项目",
                    interactive=True,
                    height=300
                )
                
                # 项目操作
                with gr.Row():
                    new_project_btn = gr.Button("➕ 新建项目", variant="primary")
                    open_project_btn = gr.Button("📂 打开项目")
                    delete_project_btn = gr.Button("🗑️ 删除项目")
                
                gr.Markdown("---")
                
                # 文件上传
                with gr.Row():
                    file_upload = gr.File(
                        label="📚 上传故事文件（md/epub/txt）",
                        file_count="multiple",
                        file_types=[".md", ".epub", ".txt"]
                    )
                    parse_btn = gr.Button("🔍 解析文件")
                
                # 文件列表
                file_list = gr.Dataframe(
                    headers=["文件名", "大小", "状态"],
                    datatype=["str", "number", "str"],
                    col_count=(3, "fixed"),
                    label="已上传文件",
                    interactive=False,
                    height=200
                )
            
            # 第二列：创作区域（主内容）
            with gr.Column(scale=3):
                
                # 第一部分：片段选择
                with gr.Tab("🎬 片段选择"):
                    gr.Markdown("### 选择要使用的片段（支持多选）")
                    segment_grid = gr.Dataframe(
                        headers=["来源故事", "片段内容", "情绪", "风格", "选择"],
                        datatype=["str", "str", "str", "str", "bool"],
                        col_count=(5, "fixed"),
                        label="可使用片段",
                        interactive=True,
                        height=300
                    )
                    generate_draft_btn = gr.Button("✨ 生成初稿", variant="primary")
                
                # 第二部分：对话式编辑
                with gr.Tab("💬 对话式编辑"):
                    gr.Markdown("### 输入您的修改意见")
                    
                    with gr.Row():
                        chat_input = gr.Textbox(
                            label="说点什么？（如'把张三换成李四'）",
                            lines=2,
                            placeholder="支持指令：替换角色、调整风格、扩展段落、修改结尾..."
                        )
                        send_btn = gr.Button("发送")
                    
                    chat_history = gr.Chatbot(
                        label="对话历史",
                        height=400
                    )
                
                # 第三部分：版本管理
                with gr.Tab("📖 版本管理"):
                    version_list = gr.Dropdown(
                        label="选择历史版本",
                        interactive=True
                    )
                    with gr.Row():
                        preview_btn = gr.Button("👁️ 预览")
                        export_md_btn = gr.Button("📄 导出 MD")
                        export_video_btn = gr.Button("🎥 导出视频")
                    
                    story_preview = gr.Markdown(
                        label="故事预览",
                        height=600
                    )
        
        # 事件绑定
        # 1. 项目管理
        new_project_btn.click(pm.create_project, inputs=[], outputs=[project_id])
        open_project_btn.click(pm.open_project, inputs=[project_list], outputs=[project_id])
        delete_project_btn.click(pm.delete_project, inputs=[project_list], outputs=[project_list])
        pm.refresh_project_list(inputs=[], outputs=[project_list])
        
        # 2. 文件处理
        parse_btn.click(pm.upload_and_parse, inputs=[file_upload, project_id], outputs=[file_list])
        
        # 3. 片段管理
        file_list.change(pm.list_segments, inputs=[project_id], outputs=[segment_grid])
        generate_draft_btn.click(
            pm.generate_draft,
            inputs=[project_id, segment_grid],
            outputs=[chat_history, story_preview, version_list]
        )
        
        # 4. 对话编辑
        send_btn.click(
            pm.dialogue_edit,
            inputs=[project_id, chat_input, chat_history, story_preview],
            outputs=[chat_history, story_preview, version_list]
        )
        
        # 5. 版本管理
        version_list.change(
            pm.load_version,
            inputs=[project_id, version_list],
            outputs=[story_preview]
        )
        export_md_btn.click(
            pm.export_md,
            inputs=[project_id, version_list],
            outputs=[gr.File(label="导出的 MD 文件")]
        )
        export_video_btn.click(
            pm.export_video,
            inputs=[project_id, version_list],
            outputs=[gr.Video(label="生成的视频")]
        )
    
    return app
```

---

### 5. 配置与提示词

**配置文件**：`config/remix_config.py`
```python
# 混搭相关配置
REMIX_CACHE_DIR = PROJECT_ROOT / "data" / "remix_cache"
REMIX_RESULTS_DIR = PROJECT_ROOT / "data" / "remix_results"

# LLM 参数
REMIX_LLM_MODEL = "gemini-2.0-flash-exp"  # 或 cloubic
REMIX_MAX_TOKENS = 8000
REMIX_TEMPERATURE = 0.8  # 创意性较高

# 分段参数
MIN_SEGMENT_LENGTH = 200  # 最小片段长度（字）
MAX_SEGMENT_LENGTH = 1000
SEGMENTS_PER_STORY = 3    # 每个故事抽取片段数

# 缓存策略
ENABLE_ANALYSIS_CACHE = True  # 启用分析结果缓存
CACHE_EXPIRY_DAYS = 30
```

**提示词模板**：`data/remix_prompts.py`
```python
# 故事分析提示词
ANALYSIS_SYSTEM_PROMPT = """
你是一位专业的文学分析师，擅长提取故事的核心元素。
请以结构化的 JSON 格式输出分析结果。
"""

ANALYSIS_USER_PROMPT = """
分析以下故事，提取关键元素：

【故事标题】{title}
【故事内容】
{content}

请提取（JSON 格式）：
{{
  "characters": [
    {{"name": "角色名", "role": "主角/配角/反派", "traits": ["性格1", "性格2"]}}
  ],
  "plots": [
    {{"summary": "情节摘要", "type": "起因/发展/高潮/结局", "emotion": "情绪标签"}}
  ],
  "scenes": [
    {{"location": "地点", "time": "时间", "mood": "氛围"}}
  ],
  "themes": ["主题1", "主题2"],
  "style": {{
    "tone": "悲剧/喜剧/中性",
    "pov": "第一人称/第三人称",
    "pace": "快节奏/慢节奏"
  }}
}}
"""

# 混搭生成提示词（主题融合模式）
REMIX_THEME_FUSION_PROMPT = """
你是一位创意作家，擅长将多个故事融合成新的叙事。

【任务】
将以下故事片段混搭成一个新故事，主题为：{theme}

【故事片段】
{segments}

【要求】
1. 提取共同主题元素，重新编织叙事
2. 保持角色性格一致，但可改变背景设定
3. 生成自然的过渡段落，确保逻辑连贯
4. 统一叙事视角为：{pov}
5. 整体风格：{style}
6. 目标长度：{target_length} 字

【输出格式】
Markdown 格式，包含：
- 标题（# 新故事标题）
- 正文（分段落）
- 结尾

开始创作：
"""
```

---

### 6. 关键文件清单

**新增文件**：
```
component/file_parser/
  ├── __init__.py
  ├── parser.py              # 多格式解析器（md/epub/txt）
  └── models.py              # StoryDocument/Chapter 数据模型

component/story_remix/
  ├── __init__.py
  ├── analyzer.py            # 故事分析器（提取人物/情节/标签）
  ├── dialogues/
  │   ├── __init__.py
  │   ├── dialogue_engine.py # 多轮对话引擎
  │   ├── tools.py          # 编辑工具（replace/expand/change_style）
  │   └── prompts.py        # 对话系统提示词
  └── session/
      ├── __init__.py
      ├── project_manager.py  # 项目管理类
      ├── session_state.py    # 会话状态管理
      └── storage.py         # 存储操作（读写文件/JSON）

web/
  └── gradio_remix_app.py    # 新的创作 UI

config/
  ├── remix_config.py        # 混搭配置
  └── remix_prompts.py       # 提示词模板

data/
  ├── projects/              # 项目存储目录（<timestamp>/）
  │   └── <timestamp>/       # 每个项目的根目录
  │       ├── project.json
  │       ├── uploads/
  │       ├── analyzed/
  │       ├── segments/
  │       └── generations/
  └── remix_cache/           # 临时分析缓存
```

**修改文件**：
```
requirements.txt           # 新增依赖：ebooklib, markdown-it-py
config/config.py          # 新增 PROJECTS_DIR 配置
web/gradio_app.py         # 可选：集成入口到现有 UI（推荐单独运行）
```

---

### 7. 依赖库更新

**新增依赖**（requirements.txt）：
```
# 文件解析
ebooklib==0.18           # EPUB 解析
markdown-it-py==3.0.0    # Markdown 解析
beautifulsoup4==4.12.0   # HTML 清洗（EPUB 内容）
lxml==5.1.0              # XML 解析

# 可选
python-docx==1.1.0       # Word 文档支持
```

---

### 8. 执行流程示例

**命令行执行**：
```bash
# 方式 1：直接运行 case
python workflow/story_remix/cases/case_remix_demo.py \
  --files story1.md story2.epub story3.txt \
  --strategy theme \
  --style 科幻 \
  --length 3000

# 方式 2：Web UI
python web/gradio_remix_app.py
# 浏览器打开 http://localhost:7860
```

**Python API 调用**：
```python
from workflow.story_remix.activities.activity_remix_001 import RemixActivity

activity = RemixActivity()
result_path = await activity.execute(
    input_files=["story1.md", "story2.epub"],
    strategy="theme",
    params={
        "target_length": 2000,
        "style": "科幻",
        "pov": "第三人称"
    },
    output_dir="data/remix_results/demo_001"
)

print(f"新故事已生成：{result_path}")

# 继续生成视频
from workflow.story_video_001.activities.activity_script_001 import VideoActivity
video_activity = VideoActivity()
video_path = await video_activity.execute(
    input_file=result_path,
    profile="kesulu",
    ...
)
```

---

## 技术亮点

1. **模块化设计**：混搭模块独立，不影响现有视频生成流水线
2. **策略可扩展**：新增混搭策略只需实现 `_strategy_name()` 方法
3. **缓存优化**：故事分析结果可复用，减少 LLM 调用
4. **格式兼容**：输出标准 Markdown，无缝对接现有 workflow
5. **渐进式实现**：可先实现基础策略（随机拼接），后续扩展高级策略

---

## 实现优先级（会话式架构）

**Phase 1（MVP，创作工具的基础）**：
1. 项目管理系统（使用文件系统 + JSON 元数据）
2. 文件解析器（支持 md/txt，复用 util/util_file.py）
3. 基础的故事分析器（提取片段，简单标签）
4. 片段展示与选择 UI（Gradio 表格组件，支持勾选）
5. 初步的对话式编辑（基于提示词的简单修改）
6. 版本管理（保存历史版本，支持回滚）

**Phase 2（增强，完整的创作体验）**：
1. 支持 EPUB 格式解析
2. 高级故事分析（人物/情节/场景/情绪分类）
3. 更智能的对话引擎（支持 Function Calling）
4. 更丰富的编辑工具（替换/扩展/删除/调整风格）
5. 导出功能（导出 md 用于视频生成）

**Phase 3（高级，性能与质量）**：
1. 分析结果缓存（避免重复 LLM 调用）
2. 批量处理（一次解析多个文件）
3. 质量评估（故事连贯性打分）
4. 版本对比（显示两个版本的差异）
5. 直接导出视频（集成现有 workflow）

---

## 验证方案

### 3.1 单元测试
```python
# 测试文件解析
def test_md_parse():
    # 测试按 # 标题分章节
    
def test_epub_parse():
    # 测试 HTML 标签清洗
    
def test_txt_parse():
    # 测试按段落分段

# 测试项目管理
def test_project_crud():
    pm = ProjectManager()
    assert len(pm.list_projects()) == 0
    
def test_save_project():
    pm = ProjectManager()
    project_id = pm.create_project()
    assert (Path(cfg.PROJECTS_DIR) / project_id).exists()

# 测试故事分析
def test_story_analysis():
    sa = StoryAnalyzer()
    content = "张三在公园散步，突然看到一只猫..."
    result = sa.analyze(content)
    assert "张三" in [c["name"] for c in result.characters]
    assert "散步" in [p["summary"] for p in result.plots]
```

### 3.2 集成测试
- 完整流程：新建项目 → 上传文件 → 解析文件 → 选择片段 → 生成初稿 → 导出
- 会话恢复：刷新页面 → 恢复当前项目状态
- 项目管理：创建项目 → 关闭项目 → 重新打开项目 → 数据完整

### 3.3 用户验收测试 (UAT)
- 片段选择：用户能否看到并勾选片段
- 对话式编辑：用户能否修改角色、调整结尾、扩展段落
- 版本管理：用户能否回滚到之前的版本
- 导出功能：导出的 md 文件能否直接用于视频生成
- 视频导出：最终生成的视频是否符合质量标准

### 3.4 性能指标
- 文件解析：<100MB 文件解析时间 <30 秒
- 故事分析：每 1000 字符分析时间 <30 秒
- 生成响应：简单修改响应时间 <30 秒，复杂修改 <60 秒
- 会话存储：刷新页面恢复时间 <2 秒

---

## 风险与挑战

### 1. 会话状态一致性
**问题**：用户刷新页面后，会话状态需要准确恢复（项目信息、文件列表、分析结果）

**缓解**：
- 使用项目目录和 JSON 元数据（而非内存状态）
- 在每个关键操作后立即持久化到磁盘
- 恢复时检查文件完整性和一致性

### 2. 对话历史管理
**问题**：多轮对话的历史记录可能变得很长，影响上下文窗口大小

**缓解**：
- 压缩对话历史（只保留关键信息）
- 使用摘要技术，在需要时重新生成完整上下文
- 按版本管理，每个版本独立对话

### 3. 性能瓶颈（LLM 密集型操作）
**问题**：项目中所有分析和生成操作都是 LLM 密集型，并发使用时可能导致排队

**缓解**：
- 使用分析结果缓存（避免重复解析同一文件）
- 支持分段分析（分章节处理长文档）
- 提供进度指示和排队机制

### 4. 用户期望管理
**问题**：对话式生成可能不符合用户的预期，需要多次调整

**缓解**：
- 清晰的提示词引导（"支持的指令：替换角色、调整风格..."）
- 显示修改预览和版本对比
- 鼓励用户提供具体的反馈（"请告诉我你想要修改哪个部分"）

---

## 总结

本方案基于用户的需求，从「一次性工作流」架构重新设计为「会话式创作工具」架构，实现：

### 核心改进（针对用户提出的三大遗漏点）

✅ **文件持久化**
- 使用 `data/projects/<timestamp>/` 存储项目数据
- 项目目录结构清晰：uploads/（原始文件）、analyzed/（分析结果）、segments/（片段）、generations/（版本历史）
- 使用 JSON 元数据存储项目信息

✅ **片段展示与选择**
- 卡片式展示片段（来源、内容、情绪、风格标签）
- 支持用户手动勾选要使用的片段
- 保留用户控制权，不依赖纯自动化

✅ **多轮对话式生成**
- 基于现有的 `UnifiedAgent` 框架
- 支持 Function Calling（替换角色、扩展段落、调整风格等）
- 完整的版本管理（每次修改生成新快照，支持回滚）

### 架构优势

1. **完全复用现有代码**
   - 使用现有的 `component/chat/core/chat.py` 进行 LLM 调用
   - 使用现有的 `util/util_file.py` 处理文件操作
   - 输出标准 Markdown，无缝对接现有视频生成流水线

2. **轻量且可扩展**
   - 不引入数据库，纯文件系统 + JSON
   - 不引入用户系统，单用户场景
   - 新增编辑工具只需添加 Function Definition

3. **渐进式实现**
   - Phase 1 完成 MVP（项目管理 + 片段选择 + 简单对话）
   - Phase 2 完成完整的创作体验
   - Phase 3 优化性能和质量

---

## 工程评审摘要

### 问题修复

| 问题编号 | 修复内容 | 原方案得分 | 改进后得分 |
|---------|---------|-----------|-----------|
| 1       | 新增项目/会话管理层 | 3/10 | 8/10 |
| 2       | 新增片段展示与选择交互 | 2/10 | 7/10 |
| 3       | 新增多轮对话式编辑 | 2/10 | 10/10 |
| 4       | 复用现有 util_file.py | 6/10 | 8/10 |
| 5       | 使用现有的 UnifiedAgent | 4/10 | 10/10 |

### 最终建议

**架构选择**：会话式创作工具（文件系统 + JSON 元数据，轻量无数据库）  
**优先级**：从 Phase 1 开始，先实现项目管理和片段选择，再逐步完善  
**测试重点**：会话恢复、多轮对话质量、导出兼容性  
**与现有系统集成**：输出与现有 video workflow 完全兼容的 Markdown 格式
