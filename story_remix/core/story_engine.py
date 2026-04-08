#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
故事混搭引擎 - 核心AI生成逻辑

职责:
- 调用LLM进行故事分析
- 片段混搭生成
- 多轮对话编辑
- 版本管理
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

from component.chat.chat import chat_with_model
from config.logging_config import get_logger

logger = get_logger(__name__)
load_dotenv()


@dataclass
class StorySegment:
    """故事片段"""
    segment_id: str
    source_file: str
    content: str
    tags: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GenerationVersion:
    """生成版本"""
    version_id: str
    content: str
    prompt: str
    timestamp: str
    parent_version: Optional[str] = None


class StoryRemixEngine:
    """故事混搭引擎"""

    def __init__(
        self,
        project_dir: Path,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        model_type: str = None,
    ):
        """
        初始化引擎

        Args:
            project_dir: 项目目录
            api_key: LLM API密钥（允许入参覆盖环境变量）
            base_url: 兼容历史参数（当前不再使用；实际路由由 model_type 决定）
            model: 模型名称（允许入参覆盖环境变量）
            model_type: 模型类型（允许入参覆盖环境变量）

        环境变量（默认）：
            STORY_ENGINE_MODEL_TYPE: 默认模型类型（默认 gemini_cloubic）
            STORY_ENGINE_MODEL: 默认模型名称（默认 gemini-3-pro-preview）

            CLOUBIC_API_KEY: gemini_cloubic 使用
            GEMINI_API_KEY: gemini 使用
            OPENAI_API_KEY: openai 使用
            DASHSCOPE_API_KEY: qwen/deepseek 使用
        """
        self.project_dir = Path(project_dir)

        # 兼容保留（不再使用）
        self.base_url = base_url

        # 默认：走 cloubic gemini
        self.model_type = model_type or os.getenv("STORY_ENGINE_MODEL_TYPE", "gemini_cloubic")
        self.model = model or os.getenv("STORY_ENGINE_MODEL", "gemini-3-pro-preview")

        # 按 model_type 选择默认 key（但入参 api_key 优先级最高）
        if self.model_type == "gemini_cloubic":
            default_key = os.getenv("CLOUBIC_API_KEY")
        elif self.model_type == "gemini":
            default_key = os.getenv("GEMINI_API_KEY")
        elif self.model_type == "openai":
            default_key = os.getenv("OPENAI_API_KEY")
        elif self.model_type in ["qwen", "deepseek"]:
            default_key = os.getenv("DASHSCOPE_API_KEY")
        else:
            default_key = None

        self.api_key = api_key or default_key

        if self.api_key:
            logger.info(f"LLM配置就绪: model_type={self.model_type}, model={self.model}")
        else:
            logger.warning(f"未配置API_KEY（model_type={self.model_type}），LLM功能将不可用")

        self.segments: List[StorySegment] = []
        self.versions: List[GenerationVersion] = []
        self._load_segments()
        self._load_versions()

    def add_segments_from_file(self, parsed_doc) -> List[str]:
        """
        从解析的文档添加片段

        Args:
            parsed_doc: ParsedDocument对象

        Returns:
            添加的片段ID列表
        """
        segment_ids = []
        for i, content in enumerate(parsed_doc.segments):
            segment_id = f"{parsed_doc.filename}_{i:03d}"
            segment = StorySegment(
                segment_id=segment_id,
                source_file=parsed_doc.filename,
                content=content,
                tags=[],
                metadata={"index": i}
            )
            self.segments.append(segment)
            segment_ids.append(segment_id)

        self._save_segments()
        logger.info(f"添加 {len(segment_ids)} 个片段，来源: {parsed_doc.filename}")
        return segment_ids

    def generate_story(self, selected_segments: List[str], user_prompt: str) -> str:
        """
        生成新故事

        Args:
            selected_segments: 选中的片段ID列表
            user_prompt: 用户提示词

        Returns:
            生成的故事内容
        """
        # 获取选中片段的内容
        selected_contents = []
        for seg_id in selected_segments:
            seg = next((s for s in self.segments if s.segment_id == seg_id), None)
            if seg:
                selected_contents.append(seg.content)

        # 构建系统提示词
        system_prompt = """你是一个专业的故事创作助手。
用户会提供多个故事片段，你需要根据用户的要求，将这些片段混搭、改编、扩展，创作出一个新的故事。

要求:
1. 保持故事的连贯性和逻辑性
2. 尊重原片段的核心元素
3. 根据用户要求调整风格、情节
4. 输出完整的故事文本（Markdown格式）"""

        # 构建用户提示词
        context = "\n\n---\n\n".join([f"片段 {i+1}:\n{content}" for i, content in enumerate(selected_contents)])
        full_prompt = f"# 原始片段\n\n{context}\n\n# 用户要求\n\n{user_prompt}\n\n请根据以上片段和要求，创作一个新故事。"

        # 调用LLM生成
        response = self._call_llm(full_prompt, system_prompt)

        # 保存版本
        self._save_version(response, user_prompt)
        return response

    def refine_story(self, current_content: str, user_feedback: str) -> str:
        """
        根据用户反馈优化故事

        Args:
            current_content: 当前故事内容
            user_feedback: 用户反馈

        Returns:
            优化后的故事
        """
        system_prompt = "你是一个专业的故事编辑助手。根据用户的反馈，修改和优化故事内容。"
        prompt = f"# 当前故事\n\n{current_content}\n\n# 用户反馈\n\n{user_feedback}\n\n请根据用户反馈修改故事。"

        response = self._call_llm(prompt, system_prompt)

        self._save_version(response, user_feedback, parent_version=self.versions[-1].version_id if self.versions else None)
        return response

    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """调用LLM（复用 component/chat/chat.py）。"""
        if not self.api_key:
            logger.warning("LLM未配置API_KEY，返回占位内容")
            return f"（LLM未配置）\n\n用户输入: {prompt[:200]}..."

        try:
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            content = chat_with_model(
                api_key=self.api_key,
                model_type=self.model_type,
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4000,
            )

            if content is None:
                logger.error("LLM调用失败：chat_with_model 返回 None")
                return "生成失败: chat_with_model 返回 None"

            logger.info(f"LLM响应成功，长度: {len(content)}")
            return content

        except Exception as e:
            logger.error(f"LLM调用异常: {e}", exc_info=True)
            return f"生成失败: {e}"

    def _save_segments(self):
        """保存片段到文件"""
        segments_file = self.project_dir / "segments" / "segments.json"
        with open(segments_file, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.segments], f, ensure_ascii=False, indent=2)

    def _load_segments(self):
        """从文件加载片段"""
        segments_file = self.project_dir / "segments" / "segments.json"
        if segments_file.exists():
            with open(segments_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.segments = [StorySegment(**s) for s in data]

    def _save_version(self, content: str, prompt: str, parent_version: Optional[str] = None):
        """保存生成版本"""
        from datetime import datetime
        version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = GenerationVersion(
            version_id=version_id,
            content=content,
            prompt=prompt,
            timestamp=datetime.now().isoformat(),
            parent_version=parent_version
        )
        self.versions.append(version)

        version_file = self.project_dir / "generations" / f"{version_id}.json"
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(asdict(version), f, ensure_ascii=False, indent=2)

    def _load_versions(self):
        """加载所有版本"""
        generations_dir = self.project_dir / "generations"
        if not generations_dir.exists():
            return

        for version_file in sorted(generations_dir.glob("*.json")):
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.versions.append(GenerationVersion(**data))
