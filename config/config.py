"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 环境变量、配置文件
Output: 全局配置常量
Pos: 系统全局配置中心
"""

# config.py
import os
from pathlib import Path

PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', Path(__file__).parent.parent))
PICTURE_RESULTS_DIR = PROJECT_ROOT / "data" / "Data_results" / "picture_results"
AUDIO_RESULTS_DIR = PROJECT_ROOT / "data" / "Data_results" / "audio_results"
VIDEO_RESULTS_DIR = PROJECT_ROOT / "data" / "Data_results" / "video_results"
SCRIPT_RESULTS_DIR = PROJECT_ROOT / "data" / "Data_results" / "script_results"

# 图片缓存（跨 run 复用）
# 实际使用路径：IMAGE_CACHE_DIR / <namespace>
IMAGE_CACHE_DIR = PROJECT_ROOT / "data" / "Data_results" / "image_cache"
# 默认 namespace："auto" 表示按输入文件自动生成（例如 <stem>__<hash8>）
IMAGE_CACHE_NAMESPACE_DEFAULT = "auto"

INTERVAL_TIME = 20  # 轮询结果的等待时间，默认20秒

# 聊天显示配置
CHAT_SHOW_SUMMARY = True  # 是否显示对话摘要（Token消耗等信息）
CHAT_SHOW_THINKING = True  # 是否显示深度思考模型的思考过程

