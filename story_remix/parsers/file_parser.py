#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件解析器 - 支持 md/txt/epub 格式

职责:
- 文件格式识别
- 文本提取
- 元数据提取
- 文本分段
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedDocument:
    """解析后的文档"""
    filename: str
    title: str
    content: str
    metadata: Dict[str, str]
    segments: List[str]


class FileParser:
    """文件解析器"""

    @staticmethod
    def parse(file_path: str) -> ParsedDocument:
        """
        解析文件

        Args:
            file_path: 文件路径

        Returns:
            ParsedDocument: 解析结果
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in [".md", ".txt"]:
            return FileParser._parse_text(path)
        elif suffix == ".epub":
            return FileParser._parse_epub(path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

    @staticmethod
    def _parse_text(path: Path) -> ParsedDocument:
        """解析文本文件（md/txt）"""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取标题（第一行 # 标题 或文件名）
        title = path.stem
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("#").strip()

        # 简单分段：按空行分段
        segments = FileParser._split_by_paragraphs(content)

        return ParsedDocument(
            filename=path.name,
            title=title,
            content=content,
            metadata={"format": path.suffix},
            segments=segments
        )

    @staticmethod
    def _parse_epub(path: Path) -> ParsedDocument:
        """解析 epub 文件"""
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("epub 解析需要安装: pip install ebooklib beautifulsoup4")
            # 降级为空文档
            return ParsedDocument(
                filename=path.name,
                title=path.stem,
                content="",
                metadata={"format": ".epub", "error": "缺少依赖"},
                segments=[]
            )

        book = epub.read_epub(str(path))
        title = book.get_metadata("DC", "title")[0][0] if book.get_metadata("DC", "title") else path.stem

        # 提取所有文本内容
        content_parts = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if text:
                    content_parts.append(text)

        content = "\n\n".join(content_parts)
        segments = FileParser._split_by_paragraphs(content)

        return ParsedDocument(
            filename=path.name,
            title=title,
            content=content,
            metadata={"format": ".epub"},
            segments=segments
        )

    @staticmethod
    def _split_by_paragraphs(text: str, min_length: int = 50) -> List[str]:
        """按段落分割文本"""
        # 按双换行符分段
        raw_segments = re.split(r"\n\s*\n", text)

        # 过滤空段落和过短段落
        segments = []
        for seg in raw_segments:
            seg = seg.strip()
            if len(seg) >= min_length:
                segments.append(seg)

        return segments
