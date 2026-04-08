#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目管理器 - 负责项目的创建、加载、保存、删除

职责:
- 项目生命周期管理
- 文件系统操作
- 项目元数据管理
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ProjectMetadata:
    """项目元数据"""
    project_id: str
    title: str
    created_at: str
    updated_at: str
    upload_count: int = 0
    segment_count: int = 0
    generation_count: int = 0


class ProjectManager:
    """项目管理器"""

    def __init__(self, base_dir: Path = None):
        """
        初始化项目管理器

        Args:
            base_dir: 项目根目录，默认为 data/projects/
        """
        if base_dir is None:
            from config.config import PROJECT_ROOT
            base_dir = PROJECT_ROOT / "data" / "projects"

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"项目管理器初始化: {self.base_dir}")

    def create_project(self, title: str = "未命名项目") -> str:
        """
        创建新项目

        Args:
            title: 项目标题

        Returns:
            project_id: 项目ID（时间戳格式）
        """
        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = self.base_dir / project_id

        # 创建项目目录结构
        (project_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (project_dir / "analyzed").mkdir(parents=True, exist_ok=True)
        (project_dir / "segments").mkdir(parents=True, exist_ok=True)
        (project_dir / "generations").mkdir(parents=True, exist_ok=True)

        # 创建元数据
        metadata = ProjectMetadata(
            project_id=project_id,
            title=title,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self._save_metadata(project_id, metadata)
        logger.info(f"创建项目: {project_id} - {title}")
        return project_id

    def list_projects(self) -> List[ProjectMetadata]:
        """列出所有项目"""
        projects = []
        for project_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if project_dir.is_dir():
                metadata = self._load_metadata(project_dir.name)
                if metadata:
                    projects.append(metadata)
        return projects

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """获取项目元数据"""
        return self._load_metadata(project_id)

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        project_dir = self.base_dir / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.info(f"删除项目: {project_id}")
            return True
        return False

    def get_project_dir(self, project_id: str) -> Path:
        """获取项目目录路径"""
        return self.base_dir / project_id

    def update_metadata(self, project_id: str, **kwargs) -> None:
        """更新项目元数据"""
        metadata = self._load_metadata(project_id)
        if metadata:
            for key, value in kwargs.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            metadata.updated_at = datetime.now().isoformat()
            self._save_metadata(project_id, metadata)

    def _save_metadata(self, project_id: str, metadata: ProjectMetadata) -> None:
        """保存元数据到文件"""
        metadata_file = self.base_dir / project_id / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, ensure_ascii=False, indent=2)

    def _load_metadata(self, project_id: str) -> Optional[ProjectMetadata]:
        """从文件加载元数据"""
        metadata_file = self.base_dir / project_id / "metadata.json"
        if not metadata_file.exists():
            return None
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProjectMetadata(**data)
        except Exception as e:
            logger.error(f"加载元数据失败: {project_id}, {e}")
            return None
