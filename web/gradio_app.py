from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import gradio as gr

from web.run_case import RunResult, run_case_kesulu_001


def _patch_gradio_client_schema_bool() -> None:
    """Workaround for gradio_client<=1.3.0 JSON schema parsing.

    In JSON Schema, some fields (e.g. additionalProperties) may be boolean.
    Older gradio_client versions don't fully support boolean schemas and may:
    - crash with `TypeError: argument of type 'bool' is not iterable` in get_type
    - raise `APIInfoParseError: Cannot parse schema True`

    This patch makes the schema parser tolerate boolean schemas.
    """

    try:
        from gradio_client import utils as client_utils  # type: ignore
    except Exception:
        return

    # 1) Patch get_type() for bool
    orig_get_type = getattr(client_utils, "get_type", None)
    if callable(orig_get_type):

        def get_type_patched(schema):  # type: ignore[no-untyped-def]
            if isinstance(schema, bool):
                return "Any"
            return orig_get_type(schema)

        client_utils.get_type = get_type_patched  # type: ignore[attr-defined]

    # 2) Patch json_schema_to_python_type() to gracefully handle bool schema
    orig_json_schema_to_python_type = getattr(client_utils, "json_schema_to_python_type", None)
    api_err = getattr(client_utils, "APIInfoParseError", Exception)

    if callable(orig_json_schema_to_python_type):

        def json_schema_to_python_type_patched(schema, *args, **kwargs):  # type: ignore[no-untyped-def]
            # Some versions expose json_schema_to_python_type(schema) (1-arg),
            # others accept extra params; keep compatible.
            if isinstance(schema, bool):
                return "Any"
            try:
                return orig_json_schema_to_python_type(schema, *args, **kwargs)
            except api_err:
                # Some older parsers can't handle boolean schemas (e.g. `True`).
                return "Any"

        client_utils.json_schema_to_python_type = json_schema_to_python_type_patched  # type: ignore[attr-defined]


_patch_gradio_client_schema_bool()


_RUN_LOCK = threading.Lock()


def _format_header() -> str:
    return "\n".join(
        [
            "最简 Web 前端（MVP）:",
            "- 仅支持上传 .md / .txt",
            "- 固定执行：case_kesulu_001 + provider=cloubic",
            "- 并发=1（避免资源争用）",
        ]
    )


def _run(upload_file) -> tuple[str, Optional[str]]:
    # This function is used for the non-streaming fallback.
    # We still keep streaming below as the primary.
    logs = []
    zip_path: Optional[str] = None

    if upload_file is None:
        return "请先上传 .md / .txt 文件", None

    with _RUN_LOCK:
        gen = run_case_kesulu_001(upload_file, provider="cloubic")
        try:
            while True:
                logs.append(next(gen))
        except StopIteration as e:
            res: RunResult = e.value
            zip_path = str(res.zip_path) if res.zip_path else None

    return "\n".join(logs), zip_path


def _run_stream(upload_file):
    if upload_file is None:
        yield "请先上传 .md / .txt 文件", None
        return

    logs = []
    zip_path: Optional[str] = None

    with _RUN_LOCK:
        gen = run_case_kesulu_001(upload_file, provider="cloubic")
        try:
            while True:
                logs.append(next(gen))
                yield "\n".join(logs[-400:]), None
        except StopIteration as e:
            res: RunResult = e.value
            zip_path = str(res.zip_path) if res.zip_path else None

    yield "\n".join(logs[-400:]), zip_path


def build_app() -> gr.Blocks:
    with gr.Blocks(title="story_vedio_sync - MVP") as demo:
        gr.Markdown(_format_header())

        with gr.Row():
            upload = gr.File(
                label="上传文档（.md / .txt）",
                file_types=[".md", ".txt"],
                type="filepath",
            )

        run_btn = gr.Button("开始执行", variant="primary")

        logs = gr.Textbox(label="日志", lines=22, interactive=False)
        download = gr.File(label="下载结果（zip）")

        run_btn.click(fn=_run_stream, inputs=[upload], outputs=[logs, download])

        # Built-in queue helps keep UI responsive; we still also use a lock.
        demo.queue(default_concurrency_limit=1)

    return demo


if __name__ == "__main__":
    app = build_app()
    # For local dev; for server deployment, set server_name to 0.0.0.0
    app.launch(server_name="127.0.0.1", server_port=7860, show_api=False, share=True)
