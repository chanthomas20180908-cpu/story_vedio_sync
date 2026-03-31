"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 查询文本
Output: 知识库检索结果
Pos: 知识库查询工具
"""

# file: component/chat/knowledge_base/kb_tools.py
"""
知识库文档操作工具集
提供 CRUD 等基础操作，供 Function Calling 使用
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import easyocr
    from pdf2image import convert_from_path
    import numpy as np
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from component.chat.tools.kb_config import (
    KNOWLEDGE_BASE_ROOT,
    SUPPORTED_FILE_EXTENSIONS,
    SECURITY_CONFIG,
    DEFAULT_LIST_LIMIT,
    DEFAULT_READ_MAX_LENGTH,
    DEFAULT_SEARCH_LIMIT
)

logger = get_logger(__name__)


class KnowledgeBaseTools:
    """知识库文档操作工具类"""
    
    def __init__(self, kb_root: Path = None, working_dir: str = None):
        """
        初始化知识库工具
        
        Args:
            kb_root: 知识库根目录，默认使用配置中的路径
            working_dir: 工作目录（相对于kb_root的子目录），限制文件访问范围
        """
        self.kb_root = Path(kb_root) if kb_root else KNOWLEDGE_BASE_ROOT
        self.kb_root.mkdir(parents=True, exist_ok=True)
        
        # 设置工作目录限制
        if working_dir:
            # 移除开头和结尾的斜杠
            working_dir = working_dir.strip('/')
            self.working_dir = (self.kb_root / working_dir).resolve()
            # 确保工作目录在kb_root内
            if not str(self.working_dir).startswith(str(self.kb_root.resolve())):
                raise ValueError(f"不安全的工作目录: {working_dir}")
            self.working_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"知识库工具初始化 - 根目录: {self.kb_root}, 工作目录: {self.working_dir}")
        else:
            self.working_dir = self.kb_root
            logger.info(f"知识库工具初始化 - 根目录: {self.kb_root} (无限制)")
    
    def _is_valid_extension(self, filename: str) -> bool:
        """检查文件扩展名是否支持"""
        ext = Path(filename).suffix.lower()
        return ext in SUPPORTED_FILE_EXTENSIONS
    
    def _resolve_path(self, relative_path: str) -> Path:
        """
        解析相对路径到绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            绝对路径
            
        Raises:
            ValueError: 如果路径不安全或超出工作目录范围
        """
        # 移除开头的斜杠
        relative_path = relative_path.lstrip('/')
        
        # 从工作目录开始构建路径
        full_path = (self.working_dir / relative_path).resolve()
        
        # 安全检查：确保路径在工作目录内
        if not str(full_path).startswith(str(self.working_dir.resolve())):
            raise ValueError(f"访问超出工作目录范围: {relative_path}")
        
        return full_path
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """获取文件元信息"""
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(self.working_dir)),
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix
        }
    
    def _fuzzy_find_file(self, filepath: str) -> Optional[Path]:
        """
        模糊查找文件，支持部分匹配和递归搜索
        
        Args:
            filepath: 用户输入的文件路径（可能不完整）
            
        Returns:
            找到的文件路径，或 None
        """
        try:
            # 先尝试精确匹配
            exact_path = self._resolve_path(filepath)
            if exact_path.exists() and exact_path.is_file():
                return exact_path
            
            # 解析目录和文件名
            path_parts = Path(filepath).parts
            if len(path_parts) == 0:
                return None
            
            filename_pattern = path_parts[-1]
            directory = str(Path(*path_parts[:-1])) if len(path_parts) > 1 else ""
            
            # 在指定目录中搜索
            search_dir = self._resolve_path(directory)
            if not search_dir.exists() or not search_dir.is_dir():
                # 如果指定目录不存在，尝试从工作目录搜索
                search_dir = self.working_dir
            
            # 模糊匹配：递归查找包含该模式的文件
            candidates = []
            for ext in SUPPORTED_FILE_EXTENSIONS:
                # 尝试多种匹配模式
                patterns = [
                    f"**/*{filename_pattern}*{ext}",  # 递归包含匹配
                    f"*{filename_pattern}*{ext}",      # 当前目录包含匹配
                    f"**/{filename_pattern}*{ext}",   # 递归前缀匹配
                    f"{filename_pattern}*{ext}",       # 当前目录前缀匹配
                ]
                for pattern in patterns:
                    candidates.extend(search_dir.glob(pattern))
            
            # 去重
            candidates = list(set(candidates))
            
            if not candidates:
                return None
            
            # 如果只有一个结果，直接返回
            if len(candidates) == 1:
                logger.info(f"模糊匹配成功: '{filepath}' -> '{candidates[0].relative_to(self.working_dir)}'")
                return candidates[0]
            
            # 多个结果：选择最相似的
            # 优先级：1. 文件名最短 2. 路径最短
            def similarity_score(p: Path) -> tuple:
                name_len = len(p.name)
                path_len = len(str(p.relative_to(self.working_dir)))
                # 如果文件名包含完整的搜索模式，优先级更高
                exact_match = filename_pattern.lower() in p.stem.lower()
                return (0 if exact_match else 1, name_len, path_len)
            
            best_match = min(candidates, key=similarity_score)
            logger.info(f"模糊匹配（多个结果）: '{filepath}' -> '{best_match.relative_to(self.working_dir)}'")
            return best_match
            
        except Exception as e:
            logger.debug(f"模糊查找失败: {e}")
            return None
    
    # ========== CRUD 操作 ==========
    
    def list_documents(self, directory: str = "", limit: int = DEFAULT_LIST_LIMIT, 
                      pattern: str = "*") -> Dict[str, Any]:
        """
        列出指定目录下的文档
        
        Args:
            directory: 子目录路径，为空则列出根目录
            limit: 返回数量限制
            pattern: 文件名模式，支持通配符（如 '*.md' 或 'test*'）
            
        Returns:
            包含文档列表和统计信息的字典
        """
        try:
            target_dir = self._resolve_path(directory)
            
            if not target_dir.exists():
                return {"error": f"目录不存在: {directory}"}
            
            if not target_dir.is_dir():
                return {"error": f"不是目录: {directory}"}
            
            # 收集文件
            all_files = []
            
            # 检查 pattern 是否包含扩展名过滤（如 '*.md'）
            if '.' in pattern and pattern.startswith('*'):
                # pattern 包含扩展名，直接使用
                all_files.extend(target_dir.rglob(pattern))
            else:
                # pattern 不包含扩展名，遍历所有支持的扩展名
                for ext in SUPPORTED_FILE_EXTENSIONS:
                    all_files.extend(target_dir.rglob(f"{pattern}{ext}"))
            
            # 限制数量
            files = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
            
            result = {
                "success": True,
                "directory": directory or "/",
                "total_found": len(all_files),
                "returned": len(files),
                "documents": [self._get_file_info(f) for f in files]
            }
            
            logger.info(f"列出文档 - 目录: {directory}, 找到: {len(all_files)}, 返回: {len(files)}")
            return result
            
        except Exception as e:
            logger.error(f"列出文档失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _read_pdf_with_ocr(self, file_path: Path) -> str:
        """
        使用OCR读取图片类PDF文件内容
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        if not OCR_SUPPORT:
            raise ImportError("OCR支持未安装，无法读取图片类PDF。请运行: pip install easyocr pdf2image")
        
        try:
            logger.info("检测到图片类PDF，使用OCR识别...")
            
            # 初始化EasyOCR（支持中英文）
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            
            # 将PDF转换为图片
            images = convert_from_path(str(file_path))
            total_pages = len(images)
            logger.info(f"PDF转图片完成，共 {total_pages} 页，开始OCR识别...")
            
            text_parts = []
            for page_num, image in enumerate(images, 1):
                # 转换为numpy数组
                img_array = np.array(image)
                
                # OCR识别
                logger.info(f"正在识别第 {page_num}/{total_pages} 页...")
                results = reader.readtext(img_array, detail=0, paragraph=True)
                
                if results:
                    page_text = "\n".join(results)
                    text_parts.append(f"\n=== 第 {page_num}/{total_pages} 页 ===\n{page_text}")
            
            if not text_parts:
                logger.warning("OCR未能识别到任何文本")
                return ""
            
            logger.info(f"OCR识别完成，共提取 {len(text_parts)} 页内容")
            return "\n".join(text_parts)
            
        except Exception as e:
            raise Exception(f"OCR识别失败: {str(e)}")
    
    def _read_pdf(self, file_path: Path, use_ocr: bool = False) -> str:
        """
        读取PDF文件内容（支持文本PDF和图片PDF）
        
        Args:
            file_path: PDF文件路径
            use_ocr: 是否强制使用OCR（默认自动检测）
            
        Returns:
            提取的文本内容
        """
        if not PDF_SUPPORT:
            raise ImportError("pdfplumber未安装，无法读取PDF文件。请运行: pip install pdfplumber")
        
        try:
            text_parts = []
            
            # 如果不强制使用OCR，先尝试普通文本提取
            if not use_ocr:
                with pdfplumber.open(str(file_path)) as pdf:
                    total_pages = len(pdf.pages)
                    logger.info(f"PDF文件共 {total_pages} 页")
                    
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text and text.strip():  # 只添加非空页面
                            text_parts.append(f"\n=== 第 {page_num}/{total_pages} 页 ===\n{text}")
            
            # 如果没有提取到文本，或强制使用OCR，则使用OCR
            if not text_parts or use_ocr:
                if not text_parts:
                    logger.warning("未能从 PDF 中提取到文本，尝试使用OCR识别...")
                
                if OCR_SUPPORT:
                    return self._read_pdf_with_ocr(file_path)
                else:
                    logger.error("图片类PDF需要OCR支持，但OCR组件未安装")
                    return ""
            
            return "\n".join(text_parts)
            
        except Exception as e:
            raise Exception(f"PDF解析失败: {str(e)}")
    
    def read_document(self, filepath: str, max_length: int = DEFAULT_READ_MAX_LENGTH,
                     start_line: int = None, end_line: int = None) -> Dict[str, Any]:
        """
        读取文档内容（支持模糊匹配和PDF）
        
        Args:
            filepath: 文件路径（相对于知识库根目录，可以是部分文件名）
            max_length: 最大读取字符数
            start_line: 起始行号（可选，PDF不支持）
            end_line: 结束行号（可选，PDF不支持）
            
        Returns:
            包含文档内容和元信息的字典
        """
        try:
            # 尝试精确匹配
            file_path = self._resolve_path(filepath)
            
            # 如果精确路径不存在，尝试模糊匹配
            if not file_path.exists():
                fuzzy_path = self._fuzzy_find_file(filepath)
                if fuzzy_path:
                    file_path = fuzzy_path
                    # 更新 filepath 为实际找到的路径
                    filepath = str(fuzzy_path.relative_to(self.kb_root))
                else:
                    return {
                        "error": f"文件不存在: {filepath}",
                        "suggestion": "请使用 'list_documents' 查看可用文件"
                    }
            
            # 检查文件大小
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > SECURITY_CONFIG['max_file_size_mb']:
                return {"error": f"文件过大: {size_mb:.2f}MB (限制: {SECURITY_CONFIG['max_file_size_mb']}MB)"}
            
            # 判断文件类型并读取内容
            is_pdf = file_path.suffix.lower() == '.pdf'
            
            if is_pdf:
                if not PDF_SUPPORT:
                    return {
                        "error": "PDF支持未安装",
                        "suggestion": "请运行: pip install pdfplumber"
                    }
                # 读取PDF
                content = self._read_pdf(file_path)
                if start_line is not None or end_line is not None:
                    logger.warning("PDF文件不支持行范围读取，将返回完整内容")
            else:
                # 检查是否为支持的文本格式
                if not self._is_valid_extension(filepath):
                    return {"error": f"不支持的文件格式: {file_path.suffix}"}
                
                # 读取文本内容
                content = file_path.read_text(encoding='utf-8')
                
                # 如果指定了行范围
                if start_line is not None or end_line is not None:
                    lines = content.split('\n')
                    start = (start_line - 1) if start_line else 0
                    end = end_line if end_line else len(lines)
                    content = '\n'.join(lines[start:end])
            
            # 截断过长内容
            truncated = False
            if len(content) > max_length:
                content = content[:max_length]
                truncated = True
            
            result = {
                "success": True,
                "filepath": filepath,
                "content": content,
                "truncated": truncated,
                "total_length": len(content),
                "file_type": "PDF" if is_pdf else "TEXT",
                "info": self._get_file_info(file_path)
            }
            
            logger.info(f"读取文档 - 文件: {filepath}, 类型: {'PDF' if is_pdf else '文本'}, 长度: {len(content)}, 截断: {truncated}")
            return result
            
        except Exception as e:
            logger.error(f"读取文档失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def create_document(self, filepath: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        创建新文档
        
        Args:
            filepath: 文件路径（相对于知识库根目录）
            content: 文档内容
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            操作结果
        """
        try:
            file_path = self._resolve_path(filepath)
            
            if not self._is_valid_extension(filepath):
                return {"error": f"不支持的文件格式: {file_path.suffix}"}
            
            if file_path.exists() and not overwrite:
                return {"error": f"文件已存在: {filepath}，设置 overwrite=true 以覆盖"}
            
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入内容
            file_path.write_text(content, encoding='utf-8')
            
            result = {
                "success": True,
                "filepath": filepath,
                "action": "created" if not file_path.exists() else "overwritten",
                "bytes_written": len(content.encode('utf-8')),
                "info": self._get_file_info(file_path)
            }
            
            logger.info(f"创建文档 - 文件: {filepath}, 大小: {result['bytes_written']} 字节")
            return result
            
        except Exception as e:
            logger.error(f"创建文档失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def update_document(self, filepath: str, content: str) -> Dict[str, Any]:
        """
        更新文档内容（覆盖）
        
        Args:
            filepath: 文件路径
            content: 新内容
            
        Returns:
            操作结果
        """
        return self.create_document(filepath, content, overwrite=True)
    
    def append_to_document(self, filepath: str, content: str, newline: bool = True) -> Dict[str, Any]:
        """
        追加内容到文档末尾
        
        Args:
            filepath: 文件路径
            content: 要追加的内容
            newline: 是否在追加前添加换行
            
        Returns:
            操作结果
        """
        try:
            file_path = self._resolve_path(filepath)
            
            if not file_path.exists():
                return {"error": f"文件不存在: {filepath}"}
            
            # 读取原内容
            original_content = file_path.read_text(encoding='utf-8')
            
            # 追加内容
            if newline and not original_content.endswith('\n'):
                content = '\n' + content
            
            new_content = original_content + content
            file_path.write_text(new_content, encoding='utf-8')
            
            result = {
                "success": True,
                "filepath": filepath,
                "appended_bytes": len(content.encode('utf-8')),
                "total_bytes": len(new_content.encode('utf-8')),
                "info": self._get_file_info(file_path)
            }
            
            logger.info(f"追加到文档 - 文件: {filepath}, 追加: {result['appended_bytes']} 字节")
            return result
            
        except Exception as e:
            logger.error(f"追加到文档失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def delete_document(self, filepath: str) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            filepath: 文件路径
            
        Returns:
            操作结果
        """
        try:
            if not SECURITY_CONFIG['allow_delete']:
                return {"error": "删除操作已禁用"}
            
            file_path = self._resolve_path(filepath)
            
            if not file_path.exists():
                return {"error": f"文件不存在: {filepath}"}
            
            # 获取文件信息（删除前）
            info = self._get_file_info(file_path)
            
            # 删除文件
            file_path.unlink()
            
            result = {
                "success": True,
                "filepath": filepath,
                "deleted_info": info
            }
            
            logger.info(f"删除文档 - 文件: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def search_in_documents(self, keyword: str, directory: str = "", 
                           case_sensitive: bool = False, 
                           limit: int = DEFAULT_SEARCH_LIMIT) -> Dict[str, Any]:
        """
        在文档中搜索关键词
        
        Args:
            keyword: 搜索关键词
            directory: 搜索目录，为空则搜索整个知识库
            case_sensitive: 是否区分大小写
            limit: 返回结果数量限制
            
        Returns:
            搜索结果
        """
        try:
            target_dir = self._resolve_path(directory)
            
            if not target_dir.exists():
                return {"error": f"目录不存在: {directory}"}
            
            results = []
            search_keyword = keyword if case_sensitive else keyword.lower()
            
            # 遍历所有支持的文件
            for ext in SUPPORTED_FILE_EXTENSIONS:
                for file_path in target_dir.rglob(f"*{ext}"):
                    try:
                        # 跳过PDF文件（PDF文件是二进制格式，需要用专门的方法读取）
                        if ext.lower() == '.pdf':
                            logger.debug(f"跳过PDF文件: {file_path.name}（PDF文件搜索需使用read_document后再搜索）")
                            continue
                        
                        content = file_path.read_text(encoding='utf-8')
                        search_content = content if case_sensitive else content.lower()
                        
                        if search_keyword in search_content:
                            # 找到匹配的行
                            matches = []
                            for i, line in enumerate(content.split('\n'), 1):
                                search_line = line if case_sensitive else line.lower()
                                if search_keyword in search_line:
                                    matches.append({
                                        "line_number": i,
                                        "content": line.strip()
                                    })
                                    if len(matches) >= 3:  # 每个文件最多显示3个匹配
                                        break
                            
                            results.append({
                                "filepath": str(file_path.relative_to(self.kb_root)),
                                "matches_count": content.count(keyword) if case_sensitive else search_content.count(search_keyword),
                                "sample_matches": matches,
                                "info": self._get_file_info(file_path)
                            })
                            
                            if len(results) >= limit:
                                break
                    except Exception as e:
                        logger.warning(f"搜索文件 {file_path} 时出错: {e}")
                        continue
                
                if len(results) >= limit:
                    break
            
            result = {
                "success": True,
                "keyword": keyword,
                "directory": directory or "/",
                "case_sensitive": case_sensitive,
                "total_matches": len(results),
                "results": results
            }
            
            logger.info(f"搜索关键词 - 关键词: {keyword}, 找到: {len(results)} 个文件")
            return result
            
        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_document_info(self, filepath: str) -> Dict[str, Any]:
        """
        获取文档元信息
        
        Args:
            filepath: 文件路径
            
        Returns:
            文档元信息
        """
        try:
            file_path = self._resolve_path(filepath)
            
            if not file_path.exists():
                return {"error": f"文件不存在: {filepath}"}
            
            result = {
                "success": True,
                "filepath": filepath,
                "info": self._get_file_info(file_path)
            }
            
            logger.info(f"获取文档信息 - 文件: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"获取文档信息失败: {e}", exc_info=True)
            return {"error": str(e)}


if __name__ == "__main__":
    from config.logging_config import setup_logging
    
    setup_logging()
    
    # 测试工具
    tools = KnowledgeBaseTools()
    
    print("\n=== 测试知识库工具 ===\n")
    
    # 1. 列出文档
    print("1. 列出所有文档:")
    result = tools.list_documents()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 2. 读取文档
    print("\n2. 读取 avater/test.txt:")
    result = tools.read_document("avater/test.txt", max_length=500)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 3. 创建文档
    print("\n3. 创建测试文档:")
    result = tools.create_document("test_kb_tools.txt", "这是一个测试文档\n创建于测试阶段")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 4. 搜索
    print("\n4. 搜索关键词 'AI':")
    result = tools.search_in_documents("AI", limit=3)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n✅ 测试完成")
