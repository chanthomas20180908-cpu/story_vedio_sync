#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
故事混搭 Gradio UI

职责:
- 项目管理界面
- 素材上传与管理
- 对话式编辑
- 预览与导出
"""

import gradio as gr
from pathlib import Path
from typing import Optional, List, Tuple
import shutil

from story_remix.core.project_manager import ProjectManager
from story_remix.parsers.file_parser import FileParser
from story_remix.core.story_engine import StoryRemixEngine
from config.logging_config import get_logger

logger = get_logger(__name__)


class StoryRemixUI:
    """故事混搭UI"""

    def __init__(self):
        self.project_manager = ProjectManager()
        self.current_project_id: Optional[str] = None
        self.current_engine: Optional[StoryRemixEngine] = None

    def build_app(self) -> gr.Blocks:
        """构建Gradio应用"""
        with gr.Blocks(title="故事混搭生成系统") as app:
            gr.Markdown("# 故事混搭生成系统")
            gr.Markdown("上传多个故事文件，AI自动拆分混搭，生成新故事")

            with gr.Tabs() as tabs:
                # Tab 1: 项目管理
                with gr.Tab("项目管理"):
                    self._build_project_tab()

                # Tab 2: 素材管理
                with gr.Tab("素材管理"):
                    self._build_material_tab()

                # Tab 3: 对话编辑
                with gr.Tab("对话编辑"):
                    self._build_chat_tab()

                # Tab 4: 预览导出
                with gr.Tab("预览导出"):
                    self._build_export_tab()

            app.queue()
        return app

    def _build_project_tab(self):
        """构建项目管理Tab"""
        with gr.Row():
            with gr.Column(scale=2):
                project_list = gr.Dataframe(
                    headers=["项目ID", "标题", "创建时间", "素材数", "片段数"],
                    label="项目列表",
                    interactive=False
                )
            with gr.Column(scale=1):
                project_title = gr.Textbox(label="新项目标题", value="未命名项目")
                create_btn = gr.Button("创建项目", variant="primary")
                refresh_btn = gr.Button("刷新列表")

                gr.Markdown("---")
                selected_project = gr.Textbox(label="选中项目ID", interactive=True)
                open_btn = gr.Button("打开项目")
                delete_btn = gr.Button("删除项目", variant="stop")

        status = gr.Textbox(label="状态", interactive=False)

        # 事件绑定
        create_btn.click(
            fn=self._create_project,
            inputs=[project_title],
            outputs=[status, project_list]
        )
        refresh_btn.click(
            fn=self._list_projects,
            outputs=[project_list]
        )
        open_btn.click(
            fn=self._open_project,
            inputs=[selected_project],
            outputs=[status]
        )
        delete_btn.click(
            fn=self._delete_project,
            inputs=[selected_project],
            outputs=[status, project_list]
        )

        # 初始加载将在build_app中处理

    def _build_material_tab(self):
        """构建素材管理Tab"""
        gr.Markdown("## 上传故事文件")

        with gr.Row():
            upload_files = gr.File(
                label="上传文件（支持 .md / .txt / .epub）",
                file_count="multiple",
                file_types=[".md", ".txt", ".epub"]
            )
            upload_btn = gr.Button("解析文件", variant="primary")

        upload_status = gr.Textbox(label="上传状态", lines=3)

        gr.Markdown("## 片段列表")
        segments_display = gr.Dataframe(
            headers=["片段ID", "来源文件", "内容预览", "标签"],
            label="已解析片段",
            interactive=False
        )

        refresh_segments_btn = gr.Button("刷新片段列表")

        # 事件绑定
        upload_btn.click(
            fn=self._upload_and_parse,
            inputs=[upload_files],
            outputs=[upload_status, segments_display]
        )
        refresh_segments_btn.click(
            fn=self._list_segments,
            outputs=[segments_display]
        )

    def _build_chat_tab(self):
        """构建对话编辑Tab"""
        gr.Markdown("## 对话式故事生成")

        with gr.Row():
            with gr.Column(scale=1):
                selected_segments = gr.CheckboxGroup(
                    label="选择片段（勾选要使用的片段）",
                    choices=[]
                )
                refresh_choices_btn = gr.Button("刷新片段选项")

            with gr.Column(scale=2):
                chat_history = gr.Chatbot(label="对话历史", height=400)
                user_input = gr.Textbox(
                    label="输入指令",
                    placeholder="例如：将这些片段混搭成一个悬疑故事...",
                    lines=3
                )
                with gr.Row():
                    send_btn = gr.Button("发送", variant="primary")
                    clear_btn = gr.Button("清空对话")

        # 事件绑定
        send_btn.click(
            fn=self._chat_generate,
            inputs=[selected_segments, user_input, chat_history],
            outputs=[chat_history, user_input]
        )
        clear_btn.click(
            fn=lambda: ([], ""),
            outputs=[chat_history, user_input]
        )
        refresh_choices_btn.click(
            fn=self._get_segment_choices,
            outputs=[selected_segments]
        )

    def _build_export_tab(self):
        """构建预览导出Tab"""
        gr.Markdown("## 预览与导出")

        version_selector = gr.Dropdown(label="选择版本", choices=[])
        refresh_versions_btn = gr.Button("刷新版本列表")

        preview = gr.Markdown(label="故事预览")

        with gr.Row():
            export_md_btn = gr.Button("导出 Markdown", variant="primary")
            export_video_btn = gr.Button("生成视频（调用现有流水线）")

        export_status = gr.Textbox(label="导出状态")
        download_file = gr.File(label="下载文件")

        # 事件绑定
        refresh_versions_btn.click(
            fn=self._list_versions,
            outputs=[version_selector]
        )
        version_selector.change(
            fn=self._preview_version,
            inputs=[version_selector],
            outputs=[preview]
        )
        export_md_btn.click(
            fn=self._export_markdown,
            inputs=[version_selector],
            outputs=[export_status, download_file]
        )

    # 回调函数实现
    def _create_project(self, title: str) -> Tuple[str, List]:
        """创建项目"""
        try:
            project_id = self.project_manager.create_project(title)
            projects = self._list_projects()
            return f"创建成功: {project_id}", projects
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            return f"创建失败: {e}", []

    def _list_projects(self) -> List[List]:
        """列出项目"""
        projects = self.project_manager.list_projects()
        return [
            [p.project_id, p.title, p.created_at, p.upload_count, p.segment_count]
            for p in projects
        ]

    def _open_project(self, project_id: str) -> str:
        """打开项目"""
        if not project_id:
            return "请输入项目ID"

        project = self.project_manager.get_project(project_id)
        if not project:
            return f"项目不存在: {project_id}"

        self.current_project_id = project_id
        project_dir = self.project_manager.get_project_dir(project_id)
        self.current_engine = StoryRemixEngine(project_dir)
        return f"已打开项目: {project.title} ({project_id})"

    def _delete_project(self, project_id: str) -> Tuple[str, List]:
        """删除项目"""
        if not project_id:
            return "请输入项目ID", []

        success = self.project_manager.delete_project(project_id)
        projects = self._list_projects()
        if success:
            return f"删除成功: {project_id}", projects
        return f"删除失败: {project_id}", projects

    def _upload_and_parse(self, files) -> Tuple[str, List]:
        """上传并解析文件"""
        if not self.current_project_id:
            return "请先打开项目", []

        if not files:
            return "请选择文件", []

        try:
            project_dir = self.project_manager.get_project_dir(self.current_project_id)
            upload_dir = project_dir / "uploads"

            total_segments = 0
            for file in files:
                # 复制文件到项目目录
                dest = upload_dir / Path(file).name
                shutil.copy(file, dest)

                # 解析文件
                parsed = FileParser.parse(str(dest))
                segment_ids = self.current_engine.add_segments_from_file(parsed)
                total_segments += len(segment_ids)

            # 更新元数据
            self.project_manager.update_metadata(
                self.current_project_id,
                upload_count=len(files),
                segment_count=total_segments
            )

            segments = self._list_segments()
            return f"解析完成: {len(files)} 个文件, {total_segments} 个片段", segments

        except Exception as e:
            logger.error(f"解析失败: {e}")
            return f"解析失败: {e}", []

    def _list_segments(self) -> List[List]:
        """列出片段"""
        if not self.current_engine:
            return []

        return [
            [s.segment_id, s.source_file, s.content[:50] + "...", ", ".join(s.tags)]
            for s in self.current_engine.segments
        ]

    def _get_segment_choices(self) -> gr.CheckboxGroup:
        """获取片段选项"""
        if not self.current_engine:
            return gr.CheckboxGroup(choices=[])

        choices = [f"{s.segment_id}: {s.content[:30]}..." for s in self.current_engine.segments]
        return gr.CheckboxGroup(choices=choices)

    def _chat_generate(self, selected: List[str], user_input: str, history: List) -> Tuple[List, str]:
        """对话生成"""
        if not self.current_engine:
            history.append((user_input, "请先打开项目并上传素材"))
            return history, ""

        if not selected:
            history.append((user_input, "请先选择片段"))
            return history, ""

        # 提取片段ID
        segment_ids = [s.split(":")[0] for s in selected]

        # 生成故事
        response = self.current_engine.generate_story(segment_ids, user_input)
        history.append((user_input, response))

        return history, ""

    def _list_versions(self) -> gr.Dropdown:
        """列出版本"""
        if not self.current_engine:
            return gr.Dropdown(choices=[])

        choices = [v.version_id for v in self.current_engine.versions]
        return gr.Dropdown(choices=choices)

    def _preview_version(self, version_id: str) -> str:
        """预览版本"""
        if not self.current_engine or not version_id:
            return "无内容"

        version = next((v for v in self.current_engine.versions if v.version_id == version_id), None)
        return version.content if version else "版本不存在"

    def _export_markdown(self, version_id: str) -> Tuple[str, Optional[str]]:
        """导出Markdown"""
        if not self.current_engine or not version_id:
            return "请选择版本", None

        version = next((v for v in self.current_engine.versions if v.version_id == version_id), None)
        if not version:
            return "版本不存在", None

        # 保存到临时文件
        export_path = self.project_manager.get_project_dir(self.current_project_id) / f"{version_id}.md"
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(version.content)

        return f"导出成功: {export_path}", str(export_path)


def launch_app():
    """启动应用"""
    # 某些网络/代理环境会导致 Gradio 的 localhost 可达性检测走代理，从而误判不可访问。
    # 显式为 localhost 关闭代理，可避免 ValueError: When localhost is not accessible...
    import os

    # gradio_client 1.3.0 在解析 OpenAPI/JSON Schema 时，对 bool schema（True/False）兼容性不足：
    # - 可能在 get_type() 里触发 TypeError（"const" in schema）
    # - 也可能直接抛 APIInfoParseError: Cannot parse schema True
    # 这里做一个最小的运行时补丁：bool schema 直接映射为 Any / None，避免启动阶段崩溃。
    try:
        from typing import Any
        import gradio_client.utils as client_utils

        _orig_get_type = getattr(client_utils, "get_type", None)
        _orig_json_schema_to_python_type = getattr(client_utils, "json_schema_to_python_type", None)
        _orig__json_schema_to_python_type = getattr(client_utils, "_json_schema_to_python_type", None)

        if callable(_orig_get_type):
            def _patched_get_type(schema):  # type: ignore
                if isinstance(schema, bool):
                    return Any if schema else None
                return _orig_get_type(schema)

            client_utils.get_type = _patched_get_type  # type: ignore

        if callable(_orig__json_schema_to_python_type):
            def _patched__json_schema_to_python_type(schema, defs=None):  # type: ignore
                if isinstance(schema, bool):
                    return Any if schema else None
                return _orig__json_schema_to_python_type(schema, defs)

            client_utils._json_schema_to_python_type = _patched__json_schema_to_python_type  # type: ignore

        if callable(_orig_json_schema_to_python_type):
            def _patched_json_schema_to_python_type(schema):  # type: ignore
                if isinstance(schema, bool):
                    return Any if schema else None
                return _orig_json_schema_to_python_type(schema)

            client_utils.json_schema_to_python_type = _patched_json_schema_to_python_type  # type: ignore

    except Exception:
        # 如果补丁失败，继续走原逻辑（后续会在启动时报错并显示 show_error 信息）
        pass

    no_proxy_hosts = ["127.0.0.1", "localhost"]
    existing_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    if existing_no_proxy:
        merged = existing_no_proxy.split(",") + no_proxy_hosts
        os.environ["NO_PROXY"] = ",".join(dict.fromkeys([h.strip() for h in merged if h.strip()]))
    else:
        os.environ["NO_PROXY"] = ",".join(no_proxy_hosts)

    # 可通过环境变量强制开启 share（例如：GRADIO_SHARE=1）
    share_env = (os.environ.get("GRADIO_SHARE") or "").strip().lower()
    share = share_env in {"1", "true", "yes", "y"}

    ui = StoryRemixUI()
    app = ui.build_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=share,
        show_error=True,
        # 关闭 API schema 生成，绕过 gradio_client 对 bool schema 的不兼容问题
        show_api=False,
    )


if __name__ == "__main__":
    launch_app()
