"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 搜索关键词
Output: 网页搜索结果
Pos: Web搜索工具
"""

# file: component/chat/knowledge_base/web_tools.py
"""
网络访问工具集
提供网页抓取、内容解析等功能
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from component.chat.config.web_platform_config import WebPlatformConfig, WebSearchMode

logger = get_logger(__name__)

# 在logger初始化后再导入playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright未安装，动态网页爬取功能不可用")


class WebTools:
    """网络访问工具类"""
    
    # 使用统一的平台配置（保留旧常量以兼容旧代码）
    TECH_PLATFORMS = WebPlatformConfig.TECH_PLATFORMS
    TECH_SEARCH_URLS = [url.replace("{keyword}", "") for url in WebPlatformConfig.TECH_SEARCH_URLS]
    MARKETING_DOMAINS = WebPlatformConfig.MARKETING_DOMAINS
    
    def __init__(self, timeout: int = 30, max_content_length: int = 50000):
        """
        初始化网络工具
        
        Args:
            timeout: 请求超时时间（秒）
            max_content_length: 最大内容长度（字符）
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        logger.info(f"网络工具初始化 - 超时: {timeout}秒, 最大内容长度: {max_content_length}字符")
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除首尾空白
        text = text.strip()
        return text
    
    def suggest_url(self, keyword: str, mode: str = "product") -> Dict[str, Any]:
        """
        根据关键词和模式建议URL（支持技术、产品、AI资讯等多种模式）
        
        工作原理：
        1. 根据mode参数选择对应的平台映射表（技术/产品/AI资讯）
        2. 优先尝试精确匹配：直接查找预设的常用关键词（如"qwen"、"36氪"）
        3. 如果精确匹配失败，尝试模糊匹配：判断关键词是否包含在预设列表中
        4. 如果都失败，返回搜索引擎URL，让用户在对应平台搜索
        
        Args:
            keyword: 关键词（如"qwen3", "用户增长", "AI新闻"等）
            mode: 查询模式，可选值:
                - "technical": 技术文档（GitHub、HuggingFace等）
                - "product": 产品理论（人人都是产品经理、36氪等）
                - "ai_news": AI资讯（机器之心、量子位等）
                - "comprehensive": 综合查询（所有类型）
            
        Returns:
            包含建议URL的字典，包括：
            - success: 是否成功
            - keyword: 原始关键词
            - mode: 使用的模式
            - suggested_url: 推荐的URL（最重要）
            - match_type: 匹配类型 (exact/fuzzy/search)
            - source: URL来源说明
        """
        # 步骤 1: 预处理 - 转换为小写以忽略大小写
        keyword_lower = keyword.lower()
        mode_lower = mode.lower()
        
        # 步骤 2: 从配置中获取对应模式的数据
        # platforms: 预设的平台映射表，如 {"qwen": "https://github.com/QwenLM/Qwen"}
        platforms = WebPlatformConfig.get_platforms_by_mode(mode_lower)
        # search_urls: 搜索URL模板列表，如 ["https://github.com/search?q={keyword}"]
        search_urls = WebPlatformConfig.get_search_urls_by_mode(mode_lower)
        # mode_desc: 模式描述，用于日志和返回信息
        mode_desc = WebPlatformConfig.get_mode_description(mode_lower)
        
        # 步骤 3: 精确匹配 - 查找完全匹配的关键词
        # 例如：keyword="qwen" 可以直接匹配到 platforms["qwen"]
        if keyword_lower in platforms:
            url = platforms[keyword_lower]
            logger.info(f"[{mode}] 关键词 '{keyword}' 精确匹配到: {url}")
            return {
                "success": True,
                "keyword": keyword,
                "mode": mode_lower,
                "mode_description": mode_desc,
                "suggested_url": url,  # 这是LLM需要使用的字段
                "match_type": "exact",  # 标记为精确匹配
                "source": f"预设平台映射（{mode_desc}）",
            }
        
        # 步骤 4: 模糊匹配 - 尝试部分匹配
        # 例如：keyword="qwen3" 包含 "qwen"，或 "llama" 包含在 "llama3" 中
        for key, url in platforms.items():
            # 双向检查：关键词包含预设键，或预设键包含关键词
            if key in keyword_lower or keyword_lower in key:
                logger.info(f"[{mode}] 关键词 '{keyword}' 模糊匹配到: {url}")
                return {
                    "success": True,
                    "keyword": keyword,
                    "mode": mode_lower,
                    "mode_description": mode_desc,
                    "suggested_url": url,
                    "match_type": "fuzzy",  # 标记为模糊匹配
                    "matched_key": key,  # 记录匹配到的预设键
                    "source": f"预设平台映射（模糊，{mode_desc}）",
                }
        
        # 步骤 5: 无匹配 - 生成搜索URL
        # 将关键词填入搜索URL模板，生成实际的搜索链接
        # 例如："https://github.com/search?q={keyword}" -> "https://github.com/search?q=新技术"
        suggestions = [url.format(keyword=keyword) for url in search_urls]
        
        logger.info(f"[{mode}] 关键词 '{keyword}' 无匹配，建议搜索: {suggestions[0]}")
        return {
            "success": True,
            "keyword": keyword,
            "mode": mode_lower,
            "mode_description": mode_desc,
            "suggested_url": suggestions[0],  # 返回第一个搜索URL
            "match_type": "search",  # 标记为搜索类型
            "all_suggestions": suggestions,  # 提供所有可选的搜索URL
            "source": f"搜索引擎（{mode_desc}）",
        }
    
    def suggest_tech_url(self, keyword: str) -> Dict[str, Any]:
        """
        根据关键词建议技术调研URL（兼容旧API）
        
        Args:
            keyword: 技术关键词（如"qwen3", "llama", "stable-diffusion"等）
            
        Returns:
            包含建议URL的字典
        """
        logger.warning("suggest_tech_url 已废弃，请使用 suggest_url(keyword, mode='technical')")
        return self.suggest_url(keyword, mode="technical")
    
    def is_marketing_site(self, url: str) -> bool:
        """
        判断URL是否为营销网站
        
        Args:
            url: 目标URL
            
        Returns:
            是否为营销网站
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for marketing_domain in self.MARKETING_DOMAINS:
            if marketing_domain in domain:
                logger.warning(f"检测到营销网站: {url}")
                return True
        
        return False
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """提取网页主要内容"""
        # 移除脚本和样式
        for script in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            script.decompose()
        
        # 尝试查找主要内容区域
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', '.main', '#main']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # 如果没找到主内容，使用body
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            return soup.get_text()
        
        # 提取文本
        text = main_content.get_text(separator='\n', strip=True)
        return self._clean_text(text)
    
    def fetch_url(self, url: str, extract_main: bool = True, warn_marketing: bool = True) -> Dict[str, Any]:
        """
        访问URL并获取内容
        
        Args:
            url: 目标URL
            extract_main: 是否只提取主要内容
            warn_marketing: 是否警告营销网站
            
        Returns:
            包含网页内容和元信息的字典
        """
        if not self._is_valid_url(url):
            return {"error": f"无效的URL格式: {url}"}
        
        # 检测营销网站并警告
        if warn_marketing and self.is_marketing_site(url):
            logger.warning(f"⚠️  访问营销网站可能获取不到技术细节: {url}")
            logger.warning(f"💡 建议改为访问技术平台: GitHub, HuggingFace, arXiv")
        
        try:
            logger.info(f"访问URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 获取编码
            response.encoding = response.apparent_encoding or 'utf-8'
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "无标题"
            
            # 提取内容
            if extract_main:
                content = self._extract_main_content(soup)
            else:
                content = soup.get_text(separator='\n', strip=True)
            
            # 截断过长内容
            truncated = False
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length]
                truncated = True
            
            # 提取元信息
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description.get('content', '') if meta_description else ''
            
            result = {
                "success": True,
                "url": url,
                "title": title_text,
                "description": description[:200] if description else "",
                "content": content,
                "content_length": len(content),
                "truncated": truncated,
                "status_code": response.status_code,
            }
            
            logger.info(f"成功访问 {url} - 标题: {title_text}, 内容长度: {len(content)}, 截断: {truncated}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"访问超时: {url}")
            return {"error": f"访问超时（{self.timeout}秒）: {url}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"访问失败: {url} - {e}")
            return {"error": f"访问失败: {str(e)}"}
        except Exception as e:
            logger.error(f"解析网页失败: {url} - {e}", exc_info=True)
            return {"error": f"解析网页失败: {str(e)}"}
    
    def search_in_page(self, url: str, keyword: str, context_chars: int = 200) -> Dict[str, Any]:
        """
        在网页中搜索关键词
        
        Args:
            url: 目标URL
            keyword: 搜索关键词
            context_chars: 上下文字符数
            
        Returns:
            包含匹配结果的字典
        """
        # 先获取网页内容
        fetch_result = self.fetch_url(url)
        
        if not fetch_result.get('success'):
            return fetch_result
        
        content = fetch_result['content']
        
        # 搜索关键词
        matches = []
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        
        start = 0
        while True:
            pos = content_lower.find(keyword_lower, start)
            if pos == -1:
                break
            
            # 提取上下文
            context_start = max(0, pos - context_chars)
            context_end = min(len(content), pos + len(keyword) + context_chars)
            context = content[context_start:context_end]
            
            matches.append({
                "position": pos,
                "context": context,
            })
            
            start = pos + 1
            
            # 限制结果数量
            if len(matches) >= 10:
                break
        
        result = {
            "success": True,
            "url": url,
            "keyword": keyword,
            "total_matches": len(matches),
            "matches": matches,
        }
        
        logger.info(f"搜索关键词 '{keyword}' 在 {url} - 找到 {len(matches)} 处匹配")
        return result
    
    def get_page_summary(self, url: str, max_paragraphs: int = 5) -> Dict[str, Any]:
        """
        获取网页摘要（前几段内容）
        
        Args:
            url: 目标URL
            max_paragraphs: 最大段落数
            
        Returns:
            包含摘要的字典
        """
        fetch_result = self.fetch_url(url, extract_main=True)
        
        if not fetch_result.get('success'):
            return fetch_result
        
        content = fetch_result['content']
        
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n') if p.strip() and len(p.strip()) > 50]
        
        # 取前几段
        summary_paragraphs = paragraphs[:max_paragraphs]
        summary = '\n\n'.join(summary_paragraphs)
        
        result = {
            "success": True,
            "url": url,
            "title": fetch_result['title'],
            "description": fetch_result['description'],
            "summary": summary,
            "total_paragraphs": len(paragraphs),
            "summary_paragraphs": len(summary_paragraphs),
        }
        
        logger.info(f"生成网页摘要 {url} - 标题: {fetch_result['title']}, 段落: {len(summary_paragraphs)}")
        return result
    
    def fetch_dynamic_url(self, url: str, wait_time: int = 3, extract_main: bool = True,
                         scroll_to_bottom: bool = True, screenshot: bool = False) -> Dict[str, Any]:
        """
        使用浏览器访问动态网页（支持JavaScript渲染）
        
        Args:
            url: 目标URL
            wait_time: 等待页面加载时间（秒）
            extract_main: 是否只提取主要内容
            scroll_to_bottom: 是否滚动到页面底部（触发懒加载）
            screenshot: 是否保存截图
            
        Returns:
            包含网页内容和元信息的字典
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "error": "Playwright未安装，请运行: pip install playwright && playwright install chromium"
            }
        
        if not self._is_valid_url(url):
            return {"error": f"无效的URL格式: {url}"}
        
        try:
            logger.info(f"使用浏览器访问动态URL: {url}")
            
            with sync_playwright() as p:
                # 启动浏览器（无头模式）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN'
                )
                page = context.new_page()
                
                # 设置较长的超时时间
                page.set_default_timeout(self.timeout * 1000)
                
                try:
                    # 访问页面
                    response = page.goto(url, wait_until='networkidle')
                    
                    # 等待页面加载
                    page.wait_for_timeout(wait_time * 1000)
                    
                    # 滚动到底部（触发懒加载）
                    if scroll_to_bottom:
                        page.evaluate("""
                            async () => {
                                const distance = 100;
                                const delay = 100;
                                while (document.scrollingElement.scrollTop + window.innerHeight < document.scrollingElement.scrollHeight) {
                                    document.scrollingElement.scrollBy(0, distance);
                                    await new Promise(resolve => setTimeout(resolve, delay));
                                }
                            }
                        """)
                        page.wait_for_timeout(1000)  # 等待内容加载
                    
                    # 获取页面标题
                    title = page.title()
                    
                    # 获取页面HTML
                    html_content = page.content()
                    
                    # 解析HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 提取内容
                    if extract_main:
                        content = self._extract_main_content(soup)
                    else:
                        content = soup.get_text(separator='\n', strip=True)
                    
                    # 截断过长内容
                    truncated = False
                    if len(content) > self.max_content_length:
                        content = content[:self.max_content_length]
                        truncated = True
                    
                    # 提取元信息
                    meta_description = soup.find('meta', attrs={'name': 'description'})
                    description = meta_description.get('content', '') if meta_description else ''
                    
                    # 截图（可选）
                    screenshot_path = None
                    if screenshot:
                        screenshot_path = f"/tmp/{urlparse(url).netloc.replace('.', '_')}_screenshot.png"
                        page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"截图已保存: {screenshot_path}")
                    
                    result = {
                        "success": True,
                        "url": url,
                        "title": title,
                        "description": description[:200] if description else "",
                        "content": content,
                        "content_length": len(content),
                        "truncated": truncated,
                        "status_code": response.status if response else None,
                        "screenshot": screenshot_path,
                        "method": "playwright",
                    }
                    
                    logger.info(f"成功访问动态页面 {url} - 标题: {title}, 内容长度: {len(content)}, 截断: {truncated}")
                    return result
                    
                except PlaywrightTimeout:
                    logger.error(f"页面加载超时: {url}")
                    return {"error": f"页面加载超时（{self.timeout}秒）: {url}"}
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"浏览器访问失败: {url} - {e}", exc_info=True)
            return {"error": f"浏览器访问失败: {str(e)}"}


if __name__ == "__main__":
    from config.logging_config import setup_logging
    
    setup_logging()
    
    web_tools = WebTools()
    
    # 测试访问网页
    print("\n=== 测试访问网页 ===")
    result = web_tools.fetch_url("https://www.baidu.com")
    if result.get('success'):
        print(f"标题: {result['title']}")
        print(f"内容长度: {result['content_length']}")
        print(f"内容预览: {result['content'][:200]}...")
    else:
        print(f"错误: {result.get('error')}")
    
    print("\n=== 测试获取摘要 ===")
    result = web_tools.get_page_summary("https://www.baidu.com")
    if result.get('success'):
        print(f"标题: {result['title']}")
        print(f"摘要: {result['summary'][:300]}...")
