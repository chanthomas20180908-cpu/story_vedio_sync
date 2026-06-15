#!/usr/bin/env python3
"""斗破苍穹 epub 按章节拆分为 markdown 文件（只取前100章）"""
import zipfile, re, os
from bs4 import BeautifulSoup

EPUB = os.path.join(os.path.dirname(__file__),
                    "../斗破苍穹 (天蚕土豆) (z-library.sk, 1lib.sk, z-lib.sk).epub")
OUT_DIR = os.path.join(os.path.dirname(__file__), "chapters")
MAX_CHAPTERS = 100


def safe_filename(title: str) -> str:
    title = title.strip()
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    return title.replace(' ', '_')


def html_to_markdown(soup: BeautifulSoup) -> str:
    lines = []
    body = soup.find('body') or soup
    for tag in body.descendants:
        if not hasattr(tag, 'name'):
            continue
        if tag.name in ('h1', 'h2', 'h3'):
            text = tag.get_text(strip=True)
            if text:
                lines.append(f"\n{'#' * int(tag.name[1])} {text}\n")
        elif tag.name == 'p':
            text = tag.get_text(strip=True)
            if text:
                lines.append(text)
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip()


def is_chapter(title: str) -> bool:
    return bool(re.match(r'第\d+章', title))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = 0
    with zipfile.ZipFile(EPUB) as z:
        htmls = sorted([n for n in z.namelist() if n.endswith(('.html', '.xhtml'))])
        for name in htmls:
            if saved >= MAX_CHAPTERS:
                break
            content = z.read(name).decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            h1 = soup.find('h1')
            if not h1:
                continue
            title = h1.get_text(strip=True)
            if not is_chapter(title):
                continue
            md = html_to_markdown(soup)
            filename = safe_filename(title) + '.md'
            with open(os.path.join(OUT_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n{md}\n")
            print(f"  {filename}")
            saved += 1
    print(f"\n共拆分 {saved} 章（上限{MAX_CHAPTERS}）→ {OUT_DIR}")


if __name__ == '__main__':
    main()
