#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 允许从任意工作目录运行：把项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from component.muti.synthesis_gemini_flash_image import gemini_flash_generate_image

# =========================
# IDE 调试：只改这几行
# =========================
PROMPT = (
    '''
【1. 核心画风：暗黑史诗 / 巨大沉默物体 (BDO)】
风格定义：IMAX 电影级概念艺术，丹尼斯·维伦纽瓦（Denis Villeneuve）式美学。极简主义巨构（Brutalism），压迫感极强。
光影基调：整体极度昏暗（Low-key lighting）。只有两处光源：A. 角色身上的红白格子衫（视觉刺点）；B. 手中酒杯发出的神圣琥珀光。背景处于深灰色的迷雾与阴影中。
镜头语言：超广角镜头（16mm），极远景。人物在画面中占比适中，被巨大的环境包围，强调**“一人对抗世界”的孤独感**。
【2. 主体塑造：荒诞的王】
角色：写实的 NBA 超级巨星（面部轮廓深邃，眼神坚毅）。
服装（强制高亮）：穿着一件鲜艳的红白法兰绒格子衬衫。这是画面中唯一的暖色块，在灰暗的废土风中显得格格不入，充满戏剧张力。
座具：巨大的、边缘锋利的灰色混凝土方块（Concrete Monolith）。它不是椅子，而是一块像悬崖一样的几何巨石。
姿态（精确指令）：他坐在巨石边缘，左脚高高翘在右膝上（二郎腿），身体后仰，呈现出一种“看戏”的放松姿态。单手举杯，姿势优雅而傲慢。
【3. 环境氛围：酒精废土】
地表：无边无际的深色液体海洋（Dark Liquid Ocean），表面平静如镜，倒映着微光。
天空/背景：充满尘埃、雾气和颗粒感。
巨物背景：在浓重的迷雾深处，隐约耸立着一个巨大的酒瓶剪影（Silhouette），它像一艘停泊的星际战舰，只露出轮廓，压迫感十足。
【4. 负面限制】
严禁出现文字、字母、水印、商标、任何品牌 Logo。严禁画面过亮或像电视新闻截图。
'''
)

IMAGE_PATHS = [
    # "/Users/test/Library/Mobile Documents/com~apple~CloudDocs/my_mutimedia/my_images/下载原图/老詹/张敬轩.jpeg",
]

# 输出宽高比（Gemini 端生成）。
# 可选值（参考官方）：1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
# 置空则使用 Gemini 默认行为（通常：跟随输入图；否则 1:1）。
ASPECT_RATIO = "1:1"

# 输出分辨率/档位（Gemini 端生成）。
# 说明：并非所有模型都支持 image_size；如不支持会由 API 报错。
# 置空则不传 image_size。
# flash不支持resolution参数
RESOLUTION = "2K" # "1K", "2K", "4K"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini Flash 文生图/图文生图（最小可用）")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="文本提示词（可选；不传则使用文件顶部 PROMPT）",
    )
    parser.add_argument(
        "--image",
        dest="images",
        action="append",
        default=[],
        help="本地图片路径；可重复传参以提供多张图，例如：--image a.png --image b.jpg",
    )
    parser.add_argument(
        "--aspect-ratio",
        dest="aspect_ratio",
        default=None,
        help="强制输出宽高比（Gemini 端生成），例如：1:1、16:9；不传则使用文件顶部 ASPECT_RATIO（如仍为空则走 Gemini 默认行为）",
    )
    args = parser.parse_args()

    prompt = args.prompt or PROMPT
    images = args.images if args.images else IMAGE_PATHS
    aspect_ratio = args.aspect_ratio if args.aspect_ratio is not None else ASPECT_RATIO
    # NOTE: Flash 模型目前不支持 resolution/image_size 之类的参数；并且 CLI 未暴露该参数。
    # 保留 RESOLUTION 常量仅用于实验记录，不参与本脚本运行逻辑。

    # 兼容项目现有习惯：尽量加载 env/default.env
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))

    print("prompt:")
    print(prompt)
    print("images:")
    for p in images:
        print(p)
    print("aspect_ratio:", aspect_ratio)

    saved_paths, meta = gemini_flash_generate_image(
        prompt=prompt,
        image_paths=images,
        api_key=os.getenv("GEMINI_API_KEY"),
        aspect_ratio=aspect_ratio,
    )

    if meta.get("input_image_oss_urls"):
        print("input_image_oss_urls:")
        for u in meta["input_image_oss_urls"]:
            print(u)

    # 显示 OSS 去重上传过程（是否复用对象）
    if meta.get("oss_uploads"):
        print("oss_uploads:")
        for idx, info in enumerate(meta["oss_uploads"]):
            action = (info or {}).get("action")
            obj = (info or {}).get("object_name")
            sha = (info or {}).get("sha256")
            print(f"[{idx}] action={action} object_name={obj} sha256={sha}")

    print("saved_paths:")
    for p in saved_paths:
        print(p)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
