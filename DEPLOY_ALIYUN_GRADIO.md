# story_vedio_sync：阿里云（公网 IP，无域名）部署 Gradio + Docker（1-2人）
目标：让用户通过 `http://<服务器公网IP>:7860` 直接打开网页使用，触发当前工作流并下载产物（mp4/srt/zip）。

## 0. 结论（最小可用形态）
- 一台阿里云轻量服务器（建议 2C4G / 80GB 起步）
- Docker 运行一个容器：
  - 容器里跑 Gradio（后续会新增 `web/gradio_app.py`）
  - 容器内调用现有工作流（等价 README 的 `python3 -m workflow.story_video_001...`）
- 安全组放行 TCP 端口 `7860`
- 不配置域名、不上 HTTPS（先跑通；后续需要再加 Nginx + 443）

## 1. 服务器与系统建议
### 1.1 规格建议
- 预期 1-2 人使用：
  - CPU/内存：2C4G（比 1C2G 稳定很多）
  - 磁盘：80GB+（图片/视频产物增长很快）
- 如果你发现：
  - 合成视频卡顿、任务经常 OOM、或希望更快：升级到 4C8G。

### 1.2 系统镜像
- 推荐 Ubuntu 22.04（或 Debian 12）。

## 2. 网络与安全组
### 2.1 端口
- 放行：`7860/tcp`（Gradio 默认端口）
- 可选：`22/tcp`（SSH 管理）

### 2.2 访问地址
- `http://<你的服务器公网IP>:7860`

## 3. 密钥（Secrets）管理原则
本项目需要的 key（示例，按 README）：
- `CLOUBIC_API_KEY`
- `GEMINI_API_KEY`
- `DASHSCOPE_API_KEY`

建议做法（部署时用环境变量注入）：
- 不把真实 key 写进仓库
- 不在 Web UI 输入 key
- 通过 `docker run -e ...` 或 `--env-file` 注入

> 注意：你可以继续保留本地的 `env/default.env` 用于本地跑 CLI；线上容器建议用单独的 `--env-file`。

## 4. 产物与目录（重要）
项目默认输出目录在：
- `data/Data_results/...`

部署时建议把 `data/` 挂载到宿主机，避免容器重启丢数据：
- 宿主机：`/opt/story_vedio_sync/data`
- 容器内：`/app/data`

这样：
- Gradio 页面给用户下载的 zip/mp4/srt 来自同一套输出目录
- 你也可以直接在服务器上查看生成结果

## 5. 部署步骤（Docker 版，最小可用）
下面命令是“模板”，你需要根据你的实际路径调整。

### 5.1 安装 Docker
在服务器上安装 Docker（Ubuntu 为例）：
- 安装 docker + docker compose（任选一种方式即可）
- 安装完成后确保 `docker ps` 可用

### 5.2 准备代码
两种方式任选：
- 方式 A：服务器上 `git clone` 代码仓库
- 方式 B：本地打包上传（scp/rsync）到服务器

建议代码放到：
- `/opt/story_vedio_sync`

### 5.3 准备 env 文件（仅服务器端）
在服务器创建：
- `/opt/story_vedio_sync/env/prod.env`

内容类似（示例，不要把真实 key 提交到 git）：
- `CLOUBIC_API_KEY=...`
- `GEMINI_API_KEY=...`
- `DASHSCOPE_API_KEY=...`

### 5.4 构建镜像
在项目根目录（有 `Dockerfile` 后）：
- `docker build -t story_vedio_sync:latest .`

### 5.5 运行容器
建议单并发（避免 1-2 人同时点“开始”导致资源抢占）。

- 挂载数据目录
- 注入 env
- 映射端口

模板：
- `docker run -d --name story_vedio_sync \
  -p 7860:7860 \
  --env-file /opt/story_vedio_sync/env/prod.env \
  -v /opt/story_vedio_sync/data:/app/data \
  story_vedio_sync:latest`

### 5.6 查看日志
- `docker logs -f story_vedio_sync`

### 5.7 停止与重启
- 停止：`docker stop story_vedio_sync`
- 启动：`docker start story_vedio_sync`
- 重启：`docker restart story_vedio_sync`

## 6. 运行时行为（你将看到什么）
Gradio 页面（后续实现）建议提供：
- 上传/粘贴 markdown
- 选择 case（如 kesulu/cabian）
- 选择 provider（cloubic/official）
- 勾选：`skip_images` / `skip_video` / `only_video`
- 输出：实时日志 + 产物链接（mp4/srt/zip）

## 7. 常见问题（排查清单）
### 7.1 打不开页面
- 确认安全组放行 7860
- 确认容器端口映射：`docker ps` 看 `0.0.0.0:7860->7860/tcp`
- 确认程序监听 0.0.0.0（Gradio 需要 `server_name="0.0.0.0"`）

### 7.2 任务报错：ffmpeg not found
- Docker 镜像需要安装 `ffmpeg`

### 7.3 任务报错：key 未配置
- 检查 `--env-file` 文件是否正确
- 检查容器内环境变量：进入容器后确认（不要在终端回显真实 key）

### 7.4 磁盘满
- `data/Data_results` 会持续增长
- 定期清理旧 run 目录，或把产物同步到 OSS 再清理

## 8. 后续增强（可选，不影响 MVP）
- 加 Nginx + HTTPS（443），隐藏 7860
- 加登录/口令（避免公网被扫）
- 加任务队列（同一时间只允许 1 个 run；其他排队）
- 产物上传 OSS（下载更快、也方便清理服务器磁盘）

## 9. 与本仓库现状的关系
当前仓库是 CLI 工作流（README.md）。
本部署文档对应“下一步要做的代码改动”：新增 `web/` 与 `Dockerfile`，把 CLI 入口包装成 Web UI 调用。
