# 工程审查报告：Gradio 界面增强

**项目：** story_vedio_sync  
**分支：** main  
**日期：** 2026-04-01  
**审查类型：** 工程架构审查 (Engineering Review)

---

## 执行摘要

**任务：** 为 Gradio Web 界面添加以下功能：
1. 参考图上传（用于锁定人物/画风）
2. 音色选择（下拉框选择 TTS 音色）
3. 跳过视频生成（复选框）
4. Zip 输出（已实现，需验证）

**范围评估：** ✅ 合理 — 所有后端功能已存在，仅需 UI 参数传递

**复杂度：** ✅ 低 — 2 个文件，~50 行代码，0 个新抽象

**审查结果：**
- 架构问题：2 个（已解决）
- 代码质量问题：2 个（已解决）
- 测试覆盖：0/25 路径（用户选择跳过自动化测试）
- 性能问题：0 个

---

## Step 0: 范围挑战

### 现有代码已解决的问题

| 功能 | CLI 支持 | 位置 |
|------|---------|------|
| 参考图覆盖 | `--ref_image` | `activity_script_001.py:702` |
| 音色覆盖 | `--cloned_voice_id` | `activity_script_001.py:710` |
| 跳过视频 | `--skip_video` | `activity_script_001.py:697` |
| Zip 输出 | 已实现 | `run_case.py:82-118` |

**结论：** 所有后端功能已存在，本次仅需 UI 层传递参数。

### 最小变更集

**文件修改：**
1. `web/gradio_app.py` — 添加 3 个 UI 组件，更新函数签名（~30 行）
2. `web/run_case.py` — 添加参数处理和验证逻辑（~20 行）

**总计：** ~50 行代码

### 复杂度检查

- ✅ 文件数：2（远低于 8 的阈值）
- ✅ 新类/服务：0（远低于 2 的阈值）
- ✅ 新抽象：0

**结论：** 复杂度极低，无需缩减范围。

### 完整性检查

**当前范围：** 添加 UI 控件 + 参数传递

**完整版本包括：**
- 音色发现/列表（从 TTS API 动态获取）
- 参考图高级验证（内容质量检查）
- 多参考图支持
- Profile 选择（当前硬编码）
- Provider 选择（当前硬编码）
- 图片预览
- 进度条

**成本分析：**
- 当前范围：人力 ~4 小时，CC ~15 分钟
- 完整版本：人力 ~3 天，CC ~45 分钟

**决策：** 当前范围适合 MVP。完整功能可推迟。

---

## Section 1: 架构审查

### 数据流

```
用户输入 (Gradio UI)
  ├─ 故事文件 (.md/.txt)
  ├─ 参考图 (可选)
  ├─ 音色 ID (下拉框)
  └─ 跳过视频 (复选框)
       ↓
_run_stream(upload_file, ref_image, voice_id, skip_video)
       ↓
run_case_kesulu_001(uploaded_path, provider, ref_image, voice_id, skip_video)
       ↓
  1) 复制故事文件 → run_dir/input/
  2) [新增] 验证参考图格式 (PIL.Image.open)
  3) [新增] 验证参考图大小 (100B < size < 10MB)
  4) 复制参考图 → run_dir/input/ref_image.{ext}
  5) 构建子进程命令：
     python -m workflow.story_video_001.cases.case_kesulu_001 \
       --input <story_path> \
       --provider cloubic \
       [--ref_image <ref_path>] \
       [--cloned_voice_id <voice_id>] \
       [--skip_video]
  6) 流式输出日志
  7) 打包结果 → zip
       ↓
Gradio UI 显示日志 + 下载链接
```

### 组件边界

| 组件 | 职责 | 依赖 | 评估 |
|------|------|------|------|
| `web/gradio_app.py` | UI 布局、用户输入、显示输出 | `web.run_case`, `gradio` | ✅ 清晰分离 |
| `web/run_case.py` | 文件处理、子进程编排、结果打包 | `workflow.story_video_001` | ✅ 清晰分离 |
| `workflow/story_video_001/` | 故事转视频流程（7 步） | TTS、生图、视频合成脚本 | ✅ 不受影响 |

### 架构决策

**决策 1：音色列表硬编码 vs 配置文件**

| 方案 | 完整度 | 成本 | 决策 |
|------|--------|------|------|
| A) 硬编码列表 | 7/10 | 人力 ~0 分钟 / CC ~0 分钟 | ✅ 采用 |
| B) 加载 voices.json | 9/10 | 人力 ~30 分钟 / CC ~5 分钟 | ❌ 过度设计 |

**理由：** 音色 ID 变化频率低，硬编码匹配当前模式（provider 也硬编码）。

**决策 2：参考图验证**

| 方案 | 完整度 | 成本 | 决策 |
|------|--------|------|------|
| A) 添加格式验证 (PIL) | 9/10 | 人力 ~20 分钟 / CC ~3 分钟 | ✅ 采用 |
| B) 跳过验证 | 6/10 | 人力 ~0 分钟 / CC ~0 分钟 | ❌ 安全风险 |

**理由：** 防止恶意文件传递到后端，安全优先。

### 依赖图

```
gradio_app.py
    ↓ 调用
run_case.py
    ↓ 启动子进程
case_kesulu_001.py (CLI)
    ↓ 加载
profile_kesulu_001.py
    ↓ 传递给
activity_script_001.py (主工作流)
```

✅ **依赖方向正确** — UI → 业务逻辑 → 工作流，无循环依赖。

### 单点故障

| SPOF | 现状 | 影响 | 是否修复 |
|------|------|------|---------|
| `_RUN_LOCK` 全局锁 | 已存在 | 并发度 = 1，多用户排队 | ❌ MVP 设计决策 |
| 子进程失败 | 已存在 | 整个流程失败 | ❌ 已有错误处理 |

### 安全架构

**风险：** 用户上传的参考图未经验证直接传递给生图脚本。

**缓解措施：**
1. ✅ Gradio `file_types=["image"]` 基础验证
2. ✅ [新增] PIL.Image.open() 格式验证
3. ✅ [新增] 文件大小验证 (100B < size < 10MB)

---

## Section 2: 代码质量审查

### 代码组织

```
web/
  ├─ gradio_app.py    # UI 层
  └─ run_case.py      # 业务逻辑层
```

✅ **职责分离清晰**

### DRY 违规

**问题：** `_run()` 和 `_run_stream()` 函数逻辑重复（`gradio_app.py:76-136`）

**分析：**
- `_run()` 注释为 "non-streaming fallback"，但未被使用
- 两函数逻辑几乎相同，唯一区别是 `yield` vs `return`

**决策：** 📝 推迟清理（用户选择）

### 错误处理

**当前模式：**
```python
try:
    # 执行工作流
except Exception:
    import traceback
    tb = traceback.format_exc()
    logs.append("[error] 异常:\n" + tb)
```

**评估：** ✅ 错误处理存在，完整 traceback 便于调试（用户选择保持）

### 边缘情况

**决策 3：文件大小验证**

| 方案 | 完整度 | 成本 | 决策 |
|------|--------|------|------|
| A) 添加大小验证 | 9/10 | 人力 ~15 分钟 / CC ~3 分钟 | ✅ 采用 |
| B) 跳过验证 | 6/10 | 人力 ~0 分钟 / CC ~0 分钟 | ❌ 用户体验差 |

**理由：** 防止空文件和过大文件导致后端失败，提前在 UI 层拦截。

---

## Section 3: 测试审查

### 测试框架

**检测结果：**
- 项目中存在少量测试文件（`component/chat/test_research_mode.py`）
- 无统一测试框架配置
- `web/` 目录完全无测试

### 代码路径覆盖图

```
代码路径覆盖
═══════════════════════════════════════════════════════════
[+] web/gradio_app.py
    │
    ├── build_app()
    │   ├── [GAP] UI 组件渲染 — 无测试
    │   └── [GAP] 事件绑定 — 无测试
    │
    └── _run_stream()
        ├── [GAP] upload_file=None — 无测试
        ├── [GAP] ref_image=None (使用默认) — 无测试
        ├── [GAP] ref_image=<valid_path> — 无测试
        ├── [GAP] voice_id=<custom> — 无测试
        ├── [GAP] skip_video=True — 无测试
        ├── [GAP] skip_video=False — 无测试
        └── [GAP] 异常处理 — 无测试

[+] web/run_case.py
    │
    ├── validate_and_copy_input()
    │   ├── [GAP] 有效文件 — 无测试
    │   ├── [GAP] 文件不存在 — 无测试
    │   ├── [GAP] 无效后缀 — 无测试
    │   └── [GAP] 文件为目录 — 无测试
    │
    ├── [新增] validate_ref_image()
    │   ├── [GAP] 有效图片 — 无测试
    │   ├── [GAP] 无效格式 — 无测试
    │   ├── [GAP] 文件过大 — 无测试
    │   ├── [GAP] 文件过小 — 无测试
    │   └── [GAP] 文件损坏 — 无测试
    │
    └── run_case_kesulu_001()
        ├── [GAP] 基础流程 — 无测试
        ├── [GAP] ref_image 参数传递 — 无测试
        ├── [GAP] voice_id 参数传递 — 无测试
        ├── [GAP] skip_video 参数传递 — 无测试
        ├── [GAP] 命令构建正确性 — 无测试
        ├── [GAP] 子进程失败处理 — 无测试
        └── [GAP] zip 生成 — 无测试

用户流程覆盖
═══════════════════════════════════════════════════════════
[+] 完整流程（所有选项）
    └── [GAP] [→E2E] 上传故事+参考图+选音色+跳过视频

[+] 最小流程（仅故事文件）
    └── [GAP] [→E2E] 上传故事 → 验证完整视频生成

[+] 错误恢复流程
    ├── [GAP] 上传无效参考图 → 显示错误 → 重新上传
    └── [GAP] 选择无效音色 → TTS 失败 → 查看日志

─────────────────────────────────────────────────────────
覆盖率: 0/25 路径测试 (0%)
  代码路径: 0/17 (0%)
  用户流程: 0/3 (0%)
  错误路径: 0/5 (0%)
质量:  ★★★: 0  ★★: 0  ★: 0
缺口: 25 个路径需要测试 (3 个需要 E2E)
─────────────────────────────────────────────────────────
```

### 测试决策

**决策 4：自动化测试**

| 方案 | 完整度 | 成本 | 决策 |
|------|--------|------|------|
| A) 完整单元测试 (11 个) | 9/10 | 人力 ~4 小时 / CC ~20 分钟 | ❌ |
| B) 核心单元测试 (5 个) | 7/10 | 人力 ~2 小时 / CC ~10 分钟 | ❌ |
| C) 仅手动测试 | 4/10 | 人力 ~0 分钟 / CC ~0 分钟 | ✅ 用户选择 |

**风险：** 无自动化回归保护，未来修改可能破坏现有功能。

### 手动测试清单

**必须验证的路径：**

1. ✅ 基础流程：上传故事文件 → 生成视频 → 下载 zip
2. ✅ 参考图上传：上传故事 + 参考图 → 验证图片被使用
3. ✅ 音色选择：选择不同音色 → 验证音频使用正确音色
4. ✅ 跳过视频：勾选跳过视频 → 验证 zip 无视频文件
5. ✅ 组合：所有选项同时使用 → 验证所有参数生效
6. ✅ 错误：上传无效参考图 → 验证错误提示
7. ✅ 错误：参考图过大 → 验证错误提示
8. ✅ 错误：参考图过小 → 验证错误提示

---

## Section 4: 性能审查

### 内存使用

**分析：**
- Gradio 上传 → 临时文件（磁盘）
- `shutil.copyfile()` 流式复制，内存占用低
- PIL.Image.open() 加载图片到内存验证

**风险评估：**
- 10MB 图片 → ~30MB 内存（解压后）
- 文件大小限制 < 10MB，风险可控

✅ **内存使用合理**

### 缓存

**潜在缓存点：**
1. 参考图 — 通常每次不同，缓存收益低
2. 音色列表 — 硬编码，无需缓存

**决策：** 不添加缓存

### 延迟分析

| 操作 | 延迟 |
|------|------|
| PIL.Image.open() 验证 | 100-500ms |
| shutil.copyfile() (10MB) | 50-100ms |
| 子进程启动 | 100-200ms |
| **总计** | **250-800ms** |

✅ **延迟可接受**（< 1 秒）

---

## 失败模式分析

| 代码路径 | 失败场景 | 测试覆盖 | 错误处理 | 用户体验 |
|---------|---------|---------|---------|---------|
| 参考图上传 | 文件损坏/格式错误 | ❌ | ✅ PIL 验证 | 清晰错误提示 |
| 参考图上传 | 文件过大 (>10MB) | ❌ | ✅ 大小验证 | 清晰错误提示 |
| 参考图上传 | 文件过小 (<100B) | ❌ | ✅ 大小验证 | 清晰错误提示 |
| 音色选择 | 音色 ID 不存在 | ❌ | ✅ TTS 错误日志 | 日志中显示错误 |
| 跳过视频 | 标志传递失败 | ❌ | ✅ 子进程错误 | 日志中显示错误 |
| 子进程执行 | 工作流崩溃 | ❌ | ✅ 异常捕获 | 完整 traceback |
| Zip 生成 | 磁盘空间不足 | ❌ | ✅ IO 错误 | 日志中显示错误 |

**关键缺口：** 0 个（所有失败场景都有错误处理）

---

## NOT in Scope

以下工作已明确排除：

1. 音色发现/列表 — 硬编码 2-3 个已知音色
2. 参考图高级验证 — 仅验证格式和大小
3. 多参考图支持 — 仅支持单张
4. Profile 选择 — 仍硬编码为 `case_kesulu_001`
5. Provider 选择 — 仍硬编码为 `cloubic`
6. 进度条 — 流式日志已足够
7. 图片预览 — zip 下载已足够
8. 重试机制 — 用户可手动重新运行
9. 自动化测试 — 仅手动测试
10. `_run()` 函数清理 — 推迟到后续

---

## What Already Exists

以下功能已在现有代码中实现：

1. 参考图覆盖 — `--ref_image` CLI 参数
2. 音色覆盖 — `--cloned_voice_id` CLI 参数
3. 跳过视频 — `--skip_video` CLI 参数
4. Zip 输出 — `_zip_results()` 函数
5. 文件上传处理 — `validate_and_copy_input()` 函数
6. 子进程执行 — 流式日志输出
7. 错误处理 — 异常捕获和 traceback 显示

**结论：** 无需重复构建，仅需 UI 层参数传递。

---

## 实现计划

### 文件修改清单

**1. `web/gradio_app.py`**

添加 UI 组件：
```python
# 音色选项（硬编码）
VOICE_OPTIONS = [
    ("男声 Flash 01 (默认)", "cosyvoice-v3-flash-manflash01-7cc91b1194ed4a4a982d035734709b8b"),
    # 添加更多音色...
]
DEFAULT_VOICE = "cosyvoice-v3-flash-manflash01-7cc91b1194ed4a4a982d035734709b8b"

def build_app() -> gr.Blocks:
    with gr.Blocks(title="story_vedio_sync - MVP") as demo:
        gr.Markdown(_format_header())

        with gr.Row():
            upload = gr.File(
                label="上传文档（.md / .txt）",
                file_types=[".md", ".txt"],
                type="filepath",
            )

        # [新增] 参考图上传
        with gr.Row():
            ref_image_upload = gr.File(
                label="参考图（可选，用于锁定人物/画风）",
                file_types=["image"],
                type="filepath",
            )

        # [新增] 音色选择
        with gr.Row():
            voice_dropdown = gr.Dropdown(
                choices=VOICE_OPTIONS,
                label="音色选择",
                value=DEFAULT_VOICE,
            )

        # [新增] 跳过视频
        with gr.Row():
            skip_video_checkbox = gr.Checkbox(
                label="跳过视频生成（仅生成图片+音频+字幕）",
                value=False,
            )

        run_btn = gr.Button("开始执行", variant="primary")
        logs = gr.Textbox(label="日志", lines=22, interactive=False)
        download = gr.File(label="下载结果（zip）")

        # [修改] 更新输入参数
        run_btn.click(
            fn=_run_stream,
            inputs=[upload, ref_image_upload, voice_dropdown, skip_video_checkbox],
            outputs=[logs, download]
        )

        demo.queue(default_concurrency_limit=1)

    return demo

# [修改] 更新函数签名
def _run_stream(upload_file, ref_image, voice_id, skip_video):
    if upload_file is None:
        msg = "请先上传 .md / .txt 文件"
        print(msg, flush=True)
        yield msg, None
        return

    logs: list[str] = []
    zip_path: Optional[str] = None

    try:
        with _RUN_LOCK:
            gen = run_case_kesulu_001(
                upload_file,
                provider="cloubic",
                ref_image=ref_image,
                voice_id=voice_id,
                skip_video=skip_video,
            )
            try:
                while True:
                    line = next(gen)
                    logs.append(line)
                    print(line, flush=True)
                    yield "\n".join(logs[-400:]), None
            except StopIteration as e:
                res: RunResult = e.value
                zip_path = str(res.zip_path) if res.zip_path else None
    except Exception:
        import traceback
        tb = traceback.format_exc()
        logs.append("[error] 异常:\n" + tb)
        print(tb, flush=True)

    yield "\n".join(logs[-400:]), zip_path
```

**2. `web/run_case.py`**

添加验证和参数处理：
```python
from PIL import Image

def validate_ref_image(ref_image_path: str | os.PathLike[str]) -> None:
    """验证参考图格式和大小。
    
    Raises:
        ValueError: 如果图片无效
    """
    path = Path(ref_image_path)
    
    # 检查文件大小
    size = path.stat().st_size
    if size < 100:
        raise ValueError("图片文件过小，请上传有效的图片文件")
    if size > 10 * 1024 * 1024:  # 10MB
        raise ValueError("图片文件过大，请上传小于 10MB 的文件")
    
    # 检查图片格式
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as e:
        raise ValueError(f"无效的图片文件: {e}")

def run_case_kesulu_001(
    uploaded_path: str | os.PathLike[str],
    provider: str = "cloubic",
    ref_image: Optional[str | os.PathLike[str]] = None,
    voice_id: Optional[str] = None,
    skip_video: bool = False,
) -> Generator[str, None, RunResult]:
    """运行工作流。
    
    Args:
        uploaded_path: 故事文件路径
        provider: 模型提供方
        ref_image: 参考图路径（可选）
        voice_id: 音色 ID（可选）
        skip_video: 是否跳过视频生成
    
    Yields:
        日志行
    
    Returns:
        RunResult
    """
    repo_root = _repo_root()
    run_id = _now_run_id()
    run_dir = repo_root / "data" / "web_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "run.log"

    input_path = validate_and_copy_input(uploaded_path, run_dir=run_dir)

    # [新增] 处理参考图
    ref_image_arg = None
    if ref_image:
        ref_src = Path(ref_image)
        validate_ref_image(ref_src)
        
        in_dir = run_dir / "input"
        in_dir.mkdir(parents=True, exist_ok=True)
        
        ref_dst = in_dir / f"ref_image{ref_src.suffix}"
        shutil.copyfile(ref_src, ref_dst)
        ref_image_arg = str(ref_dst)

    data_results_root = repo_root / "data" / "Data_results"
    before_dirs = _snapshot_dirs(data_results_root)

    py = _venv_python(repo_root)
    if not py.exists():
        py = Path("python3")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)

    cmd = [
        str(py),
        "-m",
        "workflow.story_video_001.cases.case_kesulu_001",
        "--input",
        str(input_path),
        "--provider",
        provider,
    ]

    # [新增] 添加可选参数
    if ref_image_arg:
        cmd.extend(["--ref_image", ref_image_arg])
    
    if voice_id:
        cmd.extend(["--cloned_voice_id", voice_id])
    
    if skip_video:
        cmd.append("--skip_video")

    yield f"run_id={run_id}"
    yield f"cmd={' '.join(cmd)}"

    # ... 其余代码不变 ...
```

---

## 完成总结

| 审查部分 | 问题数 | 状态 |
|---------|--------|------|
| Step 0: 范围挑战 | 0 | ✅ 范围合理 |
| 架构审查 | 2 | ✅ 已解决 |
| 代码质量审查 | 2 | ✅ 已解决，1 个推迟 |
| 测试审查 | 25 缺口 | ⚠️ 跳过自动化测试 |
| 性能审查 | 0 | ✅ 无问题 |

**Lake Score:** 2/4 推荐选择完整选项

**未解决决策：** 0 个

**关键缺口：** 0 个（所有失败场景都有错误处理）

**推荐：** ✅ 可以开始实现

---

## 下一步

1. **实现代码修改** — 按照上述实现计划修改 2 个文件
2. **手动测试** — 按照测试清单验证所有路径
3. **文档更新** — 更新 README 说明新增功能
4. **部署** — 运行 `/ship` 创建 PR

**预计时间：**
- 人力团队：~4 小时
- CC+gstack：~15 分钟

---

**审查完成日期：** 2026-04-01  
**审查人：** Claude Code (Engineering Review)
