#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 无
Output: Web平台配置
Pos: Web平台配置管理
"""

"""
网站平台配置
集中管理不同类型的网站平台映射
"""
from enum import Enum
from typing import Dict, List


class WebSearchMode(Enum):
    """网络搜索模式"""
    TECHNICAL = "technical"          # 技术网站
    PRODUCT = "product"              # 产品理论
    AI_NEWS = "ai_news"              # AI资讯
    COMPREHENSIVE = "comprehensive"  # 综合查询


class WebPlatformConfig:
    """网站平台配置类"""
    
    # ==================== 技术平台 ====================
    TECH_PLATFORMS = {
        # AI 模型
        "qwen": "https://github.com/QwenLM/Qwen",
        "qwen2": "https://github.com/QwenLM/Qwen2",
        "qwen3": "https://github.com/QwenLM/Qwen",
        "llama": "https://github.com/meta-llama/llama",
        "llama2": "https://github.com/meta-llama/llama",
        "llama3": "https://github.com/meta-llama/llama3",
        "deepseek": "https://github.com/deepseek-ai/DeepSeek-V2",
        "chatglm": "https://github.com/THUDM/ChatGLM",
        "baichuan": "https://github.com/baichuan-inc/Baichuan2",
        "yi": "https://github.com/01-ai/Yi",
        "mistral": "https://github.com/mistralai/mistral-src",
        "gemma": "https://github.com/google-deepmind/gemma",
        "claude": "https://docs.anthropic.com/claude/docs",
        "gpt": "https://platform.openai.com/docs",
        
        # 文生图模型
        "stable-diffusion": "https://github.com/Stability-AI/stablediffusion",
        "sd": "https://github.com/Stability-AI/stablediffusion",
        "flux": "https://github.com/black-forest-labs/flux",
        "dalle": "https://github.com/openai/dall-e",
        "midjourney": "https://docs.midjourney.com",
        
        # 视频生成
        "sora": "https://openai.com/sora",
        "runway": "https://research.runwayml.com",
        "pika": "https://pika.art",
        
        # 语音模型
        "whisper": "https://github.com/openai/whisper",
        "cosyvoice": "https://github.com/FunAudioLLM/CosyVoice",
        "bark": "https://github.com/suno-ai/bark",
        
        # 框架和工具
        "langchain": "https://github.com/langchain-ai/langchain",
        "llamaindex": "https://github.com/run-llama/llama_index",
        "transformers": "https://github.com/huggingface/transformers",
        "pytorch": "https://github.com/pytorch/pytorch",
        "tensorflow": "https://github.com/tensorflow/tensorflow",
        "ollama": "https://github.com/ollama/ollama",
        "vllm": "https://github.com/vllm-project/vllm",
        "fastapi": "https://github.com/tiangolo/fastapi",
        "gradio": "https://github.com/gradio-app/gradio",
        "streamlit": "https://github.com/streamlit/streamlit",
    }
    
    # 技术平台搜索优先级
    TECH_SEARCH_URLS = [
        "https://github.com/search?q={keyword}",
        "https://huggingface.co/models?search={keyword}",
        "https://arxiv.org/search/?query={keyword}",
        "https://paperswithcode.com/search?q_meta={keyword}",
    ]
    
    # ==================== 产品理论平台 ====================
    PRODUCT_PLATFORMS = {
        # 产品经理社区
        "产品经理": "https://www.woshipm.com",
        "人人都是产品经理": "https://www.woshipm.com",
        "woshipm": "https://www.woshipm.com",
        "pmcaff": "https://coffee.pmcaff.com",
        "产品壹佰": "http://www.chanpin100.com",
        
        # 创业/科技媒体
        "36氪": "https://36kr.com",
        "36kr": "https://36kr.com",
        "虎嗅": "https://www.huxiu.com",
        "少数派": "https://sspai.com",
        "爱范儿": "https://www.ifanr.com",
        
        # 数据分析
        "神策数据": "https://www.sensorsdata.cn/blog",
        "growingio": "https://www.growingio.com/blog",
        
        # 设计/交互
        "站酷": "https://www.zcool.com.cn",
        "优设": "https://www.uisdc.com",
        "ui中国": "https://www.ui.cn",
        
        # 知识平台
        "知乎": "https://www.zhihu.com",
        "知乎产品": "https://www.zhihu.com/topic/19551147",
        
        # 用户增长
        "用户增长": "https://www.woshipm.com/tag/%E7%94%A8%E6%88%B7%E5%A2%9E%E9%95%BF",
        "增长黑客": "https://www.growthhackers.com",
        
        # 产品方法论
        "精益创业": "https://www.woshipm.com/tag/%E7%B2%BE%E7%9B%8A%E5%88%9B%E4%B8%9A",
        "用户体验": "https://www.nngroup.com",
        "交互设计": "https://www.interaction-design.org",
    }
    
    # 产品平台搜索优先级
    PRODUCT_SEARCH_URLS = [
        "https://www.woshipm.com/search?keyword={keyword}",
        "https://36kr.com/search?keyword={keyword}",
        "https://www.zhihu.com/search?q={keyword}",
        "https://coffee.pmcaff.com/search?q={keyword}",
    ]
    
    # ==================== AI资讯平台 ====================
    AI_NEWS_PLATFORMS = {
        # AI产品网站
        "toolify.ai": "https://www.toolify.ai/",
        "观猹": "https://watcha.cn/",
        "AIbase": "https://www.aibase.com/zh",
        "producthunt": "https://www.producthunt.com/",
        "aibot": "https://ai-bot.cn/",
        "aiagc": "https://www.aiagc.com/",

        # 中文AI媒体
        "机器之心": "https://www.jiqizhixin.com",
        "jiqizhixin": "https://www.jiqizhixin.com",
        "量子位": "https://www.qbitai.com",
        "qbitai": "https://www.qbitai.com",
        "新智元": "https://www.aiust.com",
        "aiust": "https://www.aiust.com",
        "ai科技评论": "https://www.leiphone.com/category/ai",
        "雷峰网": "https://www.leiphone.com",
        "leiphone": "https://www.leiphone.com",
        "智东西": "https://www.zhidx.com",
        "腾讯ai": "https://ai.tencent.com/ailab/zh/news",
        
        # 英文AI媒体
        "openai blog": "https://openai.com/blog",
        "anthropic blog": "https://www.anthropic.com/news",
        "google ai blog": "https://blog.google/technology/ai",
        "deepmind blog": "https://deepmind.google/discover/blog",
        "ai news": "https://www.artificialintelligence-news.com",
        "venturebeat ai": "https://venturebeat.com/category/ai",
        "mit technology review": "https://www.technologyreview.com/topic/artificial-intelligence",
        
        # 论文/研究
        "papers with code": "https://paperswithcode.com",
        "arxiv ai": "https://arxiv.org/list/cs.AI/recent",
        "huggingface blog": "https://huggingface.co/blog",
        
        # 行业报告
        "ai指数": "https://aiindex.stanford.edu",
        "ai报告": "https://www.jiqizhixin.com/reports",
        
        # 综合
        "ai资讯": "https://www.jiqizhixin.com",
        "人工智能": "https://www.jiqizhixin.com",
    }
    
    # AI资讯搜索优先级
    AI_NEWS_SEARCH_URLS = [
        "https://www.jiqizhixin.com/search?keyword={keyword}",
        "https://www.qbitai.com/?s={keyword}",
        "https://www.leiphone.com/search?keyword={keyword}",
        "https://paperswithcode.com/search?q={keyword}",
    ]
    
    # ==================== 应避免的营销网站 ====================
    MARKETING_DOMAINS = [
        "tongyi.aliyun.com",
        "dashscope.aliyun.com",
        "bailian.aliyun.com",
        "qwen.cn",
        "tongyi.com",
    ]
    
    @classmethod
    def get_platforms_by_mode(cls, mode: str) -> Dict[str, str]:
        """
        根据模式获取平台映射
        
        Args:
            mode: 搜索模式 (technical/product/ai_news/comprehensive)
            
        Returns:
            平台映射字典
        """
        mode_lower = mode.lower()
        
        if mode_lower == WebSearchMode.TECHNICAL.value:
            return cls.TECH_PLATFORMS
        elif mode_lower == WebSearchMode.PRODUCT.value:
            return cls.PRODUCT_PLATFORMS
        elif mode_lower == WebSearchMode.AI_NEWS.value:
            return cls.AI_NEWS_PLATFORMS
        elif mode_lower == WebSearchMode.COMPREHENSIVE.value:
            # 合并所有平台
            all_platforms = {}
            all_platforms.update(cls.TECH_PLATFORMS)
            all_platforms.update(cls.PRODUCT_PLATFORMS)
            all_platforms.update(cls.AI_NEWS_PLATFORMS)
            return all_platforms
        else:
            # 默认返回技术平台
            return cls.TECH_PLATFORMS
    
    @classmethod
    def get_search_urls_by_mode(cls, mode: str) -> List[str]:
        """
        根据模式获取搜索URL模板
        
        Args:
            mode: 搜索模式
            
        Returns:
            搜索URL模板列表
        """
        mode_lower = mode.lower()
        
        if mode_lower == WebSearchMode.TECHNICAL.value:
            return cls.TECH_SEARCH_URLS
        elif mode_lower == WebSearchMode.PRODUCT.value:
            return cls.PRODUCT_SEARCH_URLS
        elif mode_lower == WebSearchMode.AI_NEWS.value:
            return cls.AI_NEWS_SEARCH_URLS
        elif mode_lower == WebSearchMode.COMPREHENSIVE.value:
            # 合并所有搜索URL
            return cls.TECH_SEARCH_URLS + cls.PRODUCT_SEARCH_URLS + cls.AI_NEWS_SEARCH_URLS
        else:
            return cls.TECH_SEARCH_URLS
    
    @classmethod
    def get_mode_description(cls, mode: str) -> str:
        """
        获取模式描述
        
        Args:
            mode: 搜索模式
            
        Returns:
            模式描述
        """
        descriptions = {
            WebSearchMode.TECHNICAL.value: "技术文档和开源项目（GitHub、HuggingFace、arXiv等）",
            WebSearchMode.PRODUCT.value: "产品理论和方法论（人人都是产品经理、36氪、PMCaff等）",
            WebSearchMode.AI_NEWS.value: "AI行业资讯和研究动态（机器之心、量子位、Papers with Code等）",
            WebSearchMode.COMPREHENSIVE.value: "综合查询（包含技术、产品、资讯所有类型）",
        }
        return descriptions.get(mode.lower(), "技术平台")


if __name__ == "__main__":
    # 测试配置
    print("=== 技术平台 ===")
    print(f"数量: {len(WebPlatformConfig.TECH_PLATFORMS)}")
    print(f"示例: {list(WebPlatformConfig.TECH_PLATFORMS.items())[:3]}")
    
    print("\n=== 产品平台 ===")
    print(f"数量: {len(WebPlatformConfig.PRODUCT_PLATFORMS)}")
    print(f"示例: {list(WebPlatformConfig.PRODUCT_PLATFORMS.items())[:3]}")
    
    print("\n=== AI资讯平台 ===")
    print(f"数量: {len(WebPlatformConfig.AI_NEWS_PLATFORMS)}")
    print(f"示例: {list(WebPlatformConfig.AI_NEWS_PLATFORMS.items())[:3]}")
    
    print("\n=== 综合平台 ===")
    all_platforms = WebPlatformConfig.get_platforms_by_mode("comprehensive")
    print(f"总数量: {len(all_platforms)}")
    
    print("\n=== 搜索URL ===")
    for mode in ["technical", "product", "ai_news"]:
        urls = WebPlatformConfig.get_search_urls_by_mode(mode)
        print(f"{mode}: {len(urls)} 个搜索引擎")
