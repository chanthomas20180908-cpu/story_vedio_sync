#!/usr/bin/env python3
"""
西游记 epub 按章节拆分为 markdown 文件
输出目录：chapters/
文件名：第X回_标题.md
"""
import zipfile
import re
import os
from bs4 import BeautifulSoup

EPUB = os.path.join(os.path.dirname(__file__),
                    "西游记 (吴承恩) (z-library.sk, 1lib.sk, z-lib.sk).epub")
OUT_DIR = os.path.join(os.path.dirname(__file__), "chapters")


def safe_filename(title: str) -> str:
    """把章节标题转成合法文件名，空格替换为下划线"""
    title = title.strip()
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    title = title.replace(' ', '_')
    return title


def html_to_markdown(soup: BeautifulSoup) -> str:
    """把 BeautifulSoup 解析的正文转成简单 markdown"""
    lines = []
    body = soup.find('body') or soup
    for tag in body.descendants:
        if not hasattr(tag, 'name'):
            continue
        if tag.name in ('h1', 'h2', 'h3'):
            text = tag.get_text(strip=True)
            if text:
                level = int(tag.name[1])
                lines.append(f"\n{'#' * level} {text}\n")
        elif tag.name == 'p':
            text = tag.get_text(strip=True)
            if text:
                lines.append(text)
        elif tag.name == 'br':
            lines.append('')
    # 合并，去掉连续空行
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def is_chapter(title: str) -> bool:
    """判断是否是章节页（第X回 或 附录）"""
    return bool(re.match(r'第[零一二三四五六七八九十百]+回', title)) or title.startswith('附录')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with zipfile.ZipFile(EPUB) as z:
        htmls = sorted([n for n in z.namelist()
                        if n.startswith('text/') and n.endswith('.html')])

        saved = 0
        for name in htmls:
            content = z.read(name).decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')

            title_tag = soup.find('title')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            if not is_chapter(title):
                continue

            md_body = html_to_markdown(soup)
            filename = safe_filename(title) + '.md'
            filepath = os.path.join(OUT_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(md_body)
                f.write('\n')

            print(f"  {filename}")
            saved += 1

    print(f"\n共拆分 {saved} 个章节 → {OUT_DIR}")


if __name__ == '__main__':
    main()
