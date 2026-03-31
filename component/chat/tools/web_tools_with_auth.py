#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 搜索关键词、认证信息
Output: 网页搜索结果
Pos: 带认证的Web搜索工具
"""

"""
带身份认证的网络访问工具
支持Cookie持久化，可爬取需要登录的网站（如淘宝服务市场）
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
import time
from urllib.parse import urlparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = get_logger(__name__)


class AuthenticatedWebTools:
    """
    带身份认证的网络爬取工具
    
    功能：
    1. Cookie管理（保存/加载）
    2. 支持手动登录并保存Cookie
    3. 使用保存的Cookie进行后续爬取
    4. 自动检测Cookie过期
    """
    
    def __init__(self, cookies_dir: str = None):
        """
        初始化
        
        Args:
            cookies_dir: Cookie保存目录，默认为 ~/.cache/web_scraper/cookies/
        """
        if cookies_dir is None:
            cookies_dir = Path.home() / ".cache" / "web_scraper" / "cookies"
        
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"认证网络工具初始化 - Cookie目录: {self.cookies_dir}")
    
    def _get_cookie_file(self, domain: str) -> Path:
        """获取指定域名的Cookie文件路径"""
        # 将域名转换为安全的文件名
        safe_domain = domain.replace('/', '_').replace(':', '_')
        return self.cookies_dir / f"{safe_domain}.json"
    
    def login_and_save_cookies(self, url: str, domain: str = None) -> Dict[str, Any]:
        """
        打开浏览器让用户手动登录，然后保存Cookie
        
        Args:
            url: 登录页面URL（如淘宝首页）
            domain: 域名标识（用于保存Cookie），默认从URL提取
            
        Returns:
            {"success": bool, "cookies_file": str, "cookies_count": int}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"error": "Playwright未安装"}
        
        if domain is None:
            domain = urlparse(url).netloc
        
        cookie_file = self._get_cookie_file(domain)
        
        logger.info(f"开始登录流程 - 域名: {domain}")
        logger.info(f"Cookie将保存到: {cookie_file}")
        
        try:
            with sync_playwright() as p:
                # 启动浏览器（有头模式，让用户登录）
                browser = p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN'
                )
                
                page = context.new_page()
                
                # 移除webdriver标志
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # 访问登录页面
                logger.info(f"访问页面: {url}")
                page.goto(url, wait_until='networkidle')
                
                # 等待用户手动登录
                print("\n" + "="*70)
                print("🔐 请在打开的浏览器中完成登录")
                print("="*70)
                print("✅ 登录完成后，请按 [回车键] 继续...")
                input()
                
                # 验证登录状态
                current_url = page.url
                if 'login' in current_url.lower():
                    logger.warning("检测到仍在登录页面，可能登录失败")
                    print("\n⚠️  检测到仍在登录页面")
                    confirm = input("是否仍要保存Cookie？(y/n): ")
                    if confirm.lower() != 'y':
                        browser.close()
                        return {"success": False, "error": "用户取消"}
                
                # 保存Cookie
                cookies = context.cookies()
                cookie_data = {
                    "domain": domain,
                    "url": url,
                    "saved_at": time.time(),
                    "cookies": cookies
                }
                
                cookie_file.write_text(json.dumps(cookie_data, ensure_ascii=False, indent=2))
                
                logger.info(f"✅ Cookie已保存: {cookie_file}")
                logger.info(f"✅ 共保存 {len(cookies)} 个Cookie")
                
                browser.close()
                
                return {
                    "success": True,
                    "cookies_file": str(cookie_file),
                    "cookies_count": len(cookies),
                    "domain": domain
                }
                
        except Exception as e:
            logger.error(f"登录保存Cookie失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _load_cookies(self, domain: str) -> Optional[list]:
        """加载指定域名的Cookie"""
        cookie_file = self._get_cookie_file(domain)
        
        if not cookie_file.exists():
            logger.warning(f"Cookie文件不存在: {cookie_file}")
            return None
        
        try:
            cookie_data = json.loads(cookie_file.read_text())
            cookies = cookie_data.get("cookies", [])
            saved_at = cookie_data.get("saved_at", 0)
            
            # 检查Cookie年龄（超过7天提示）
            age_days = (time.time() - saved_at) / 86400
            if age_days > 7:
                logger.warning(f"Cookie已保存 {age_days:.1f} 天，可能已过期")
            
            logger.info(f"加载Cookie: {len(cookies)} 个，保存时间: {age_days:.1f} 天前")
            return cookies
            
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return None
    
    def fetch_authenticated_url(
        self,
        url: str,
        domain: str = None,
        wait_time: int = 5,
        extract_main: bool = True,
        scroll_to_bottom: bool = True,
        screenshot: bool = False,
        auto_login: bool = False
    ) -> Dict[str, Any]:
        """
        使用保存的Cookie访问需要认证的URL
        
        Args:
            url: 目标URL
            domain: Cookie域名，默认从URL提取
            wait_time: 等待时间（秒）
            extract_main: 是否只提取主要内容
            scroll_to_bottom: 是否滚动到底部
            screenshot: 是否截图
            auto_login: 如果Cookie不存在，是否自动打开登录流程
            
        Returns:
            {"success": bool, "content": str, ...}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"error": "Playwright未安装"}
        
        if domain is None:
            domain = urlparse(url).netloc
        
        # 加载Cookie
        cookies = self._load_cookies(domain)
        
        if cookies is None:
            if auto_login:
                logger.info("Cookie不存在，启动登录流程...")
                login_url = f"https://{domain}/"
                result = self.login_and_save_cookies(login_url, domain)
                if not result.get("success"):
                    return {"error": f"登录失败: {result.get('error')}"}
                cookies = self._load_cookies(domain)
            else:
                return {
                    "error": f"Cookie不存在，请先运行 login_and_save_cookies('https://{domain}/', '{domain}')"
                }
        
        logger.info(f"使用认证Cookie访问: {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN'
                )
                
                # 添加Cookie
                context.add_cookies(cookies)
                
                page = context.new_page()
                
                # 移除webdriver标志
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                try:
                    # 访问页面
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # 等待加载
                    logger.info(f"等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    
                    # 滚动页面
                    if scroll_to_bottom:
                        logger.info("滚动页面...")
                        for i in range(3):
                            page.evaluate('window.scrollBy(0, 500)')
                            time.sleep(0.5)
                        page.evaluate('window.scrollTo(0, 0)')
                        time.sleep(1)
                    
                    # 获取标题
                    title = page.title()
                    
                    # 获取HTML
                    html_content = page.content()
                    
                    # 截图
                    screenshot_path = None
                    if screenshot:
                        screenshot_path = f"/tmp/{domain.replace('.', '_')}_screenshot.png"
                        page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"截图保存: {screenshot_path}")
                    
                    # 解析内容
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 移除脚本和样式
                    for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                        script.decompose()
                    
                    # 提取文本
                    if extract_main:
                        main = soup.find('main') or soup.find('article') or soup.find('body')
                        text = main.get_text(separator='\n', strip=True) if main else soup.get_text(separator='\n', strip=True)
                    else:
                        text = soup.get_text(separator='\n', strip=True)
                    
                    # 清理文本
                    import re
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    logger.info(f"✅ 成功获取内容，长度: {len(text)} 字符")
                    
                    result = {
                        "success": True,
                        "url": url,
                        "title": title,
                        "content": text,
                        "content_length": len(text),
                        "screenshot": screenshot_path,
                        "method": "authenticated_playwright"
                    }
                    
                    browser.close()
                    return result
                    
                except PlaywrightTimeout:
                    logger.error(f"页面加载超时: {url}")
                    browser.close()
                    return {"error": "页面加载超时"}
                    
        except Exception as e:
            logger.error(f"访问失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    def list_saved_cookies(self) -> list:
        """列出所有已保存的Cookie"""
        cookies = []
        for file in self.cookies_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                cookies.append({
                    "domain": data.get("domain"),
                    "file": file.name,
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data.get("saved_at", 0))),
                    "age_days": (time.time() - data.get("saved_at", 0)) / 86400,
                    "cookies_count": len(data.get("cookies", []))
                })
            except Exception as e:
                logger.warning(f"解析Cookie文件失败 {file}: {e}")
        
        return cookies
    
    def delete_cookies(self, domain: str) -> bool:
        """删除指定域名的Cookie"""
        cookie_file = self._get_cookie_file(domain)
        if cookie_file.exists():
            cookie_file.unlink()
            logger.info(f"已删除Cookie: {domain}")
            return True
        return False


# 使用示例
if __name__ == "__main__":
    from config.logging_config import setup_logging
    
    setup_logging()
    
    auth_tools = AuthenticatedWebTools()
    
    # 示例1: 列出已保存的Cookie
    print("\n已保存的Cookie:")
    print("="*70)
    saved = auth_tools.list_saved_cookies()
    for item in saved:
        print(f"域名: {item['domain']}")
        print(f"  保存时间: {item['saved_at']} ({item['age_days']:.1f}天前)")
        print(f"  Cookie数: {item['cookies_count']}")
        print()
    
    if not saved:
        print("暂无保存的Cookie\n")
        print("使用方法:")
        print("  1. 先登录并保存Cookie:")
        print("     auth_tools.login_and_save_cookies('https://fuwu.taobao.com/', 'fuwu.taobao.com')")
        print()
        print("  2. 使用Cookie访问:")
        print("     result = auth_tools.fetch_authenticated_url('产品详情URL', 'fuwu.taobao.com')")
