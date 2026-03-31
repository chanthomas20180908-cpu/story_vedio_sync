# story_vedio_sync

把 `story_video_001` 工作流从原工程中抽出来，作为可单独维护的最小可运行项目（方案 A：clone 后按 README 跑）。

## 1) 环境要求
- Python 3.10+（建议）
- `ffmpeg`（用于合成视频）

macOS 安装 ffmpeg：
```bash
brew install ffmpeg
```

## 2) 安装依赖
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 3) 配置密钥
把示例文件复制一份：
```bash
cp env/default.env.example env/default.env
```
然后编辑 `env/default.env`，填写你自己的：
- `CLOUBIC_API_KEY`（provider=cloubic）
- `GEMINI_API_KEY`（provider=official）
- `DASHSCOPE_API_KEY`（TTS/克隆音色）

## 4) 快速跑通（不生图、不合成视频）
> 用自带示例输入文件验证链路。

```bash
PYTHONPATH=$(pwd) .venv/bin/python3 -m workflow.story_video_001.cases.case_kesulu_001 \
  --input "workflow/story_video_001/cases/input/001.md" \
  --skip_images \
  --skip_video
```

输出目录默认在：
- `data/Data_results/script_results/<stem>__<hash>_script_<run_id>/...`

## 5) 跑完整链路（生图 + 合成视频）

在跑“生图”前，你需要准备参考图（锁定人物/画风）：
- `assets/ref_images/kesulu_ref.png`
- `assets/ref_images/cabian_ref.png`

（文件名按 profile 约定；你也可以改 profile 里的 `ref_image` 指向其它路径。）

### 5.1 cloubic（推荐：OpenAI-compat banana 生图）
```bash
PYTHONPATH=$(pwd) .venv/bin/python3 -m workflow.story_video_001.cases.case_kesulu_001 \
  --input "workflow/story_video_001/cases/input/001.md" \
  --provider cloubic
```

### 5.2 official（Google Gemini 官方生图）
```bash
PYTHONPATH=$(pwd) .venv/bin/python3 -m workflow.story_video_001.cases.case_kesulu_001 \
  --input "workflow/story_video_001/cases/input/001.md" \
  --provider official
```

## 6) 常见问题
- `ModuleNotFoundError: faster_whisper`：
  - 说明你没装字幕强制对齐依赖：`pip install faster-whisper`
- `ffmpeg: not found`：
  - 安装 ffmpeg，或在 profile 里把 `ffmpeg_bin` 改成绝对路径

## 7) 目录说明（关键）
- `workflow/story_video_001/`：主工作流
- `tools/`：字幕/清洗工具
- `debug/story_audio/`：TTS 入口脚本
- `debug/nanobanana/`：生图脚本（official / cloubic）
- `env/`：环境变量（只提交 `.example`，不提交真实 key）
