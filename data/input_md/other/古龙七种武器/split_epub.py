#!/usr/bin/env python3
"""古龙七种武器 epub 按故事拆分为 markdown 文件（h3 = 故事起点）"""
import zipfile, re, os
from bs4 import BeautifulSoup

EPUB = os.path.join(os.path.dirname(__file__),
                    "../古龙文集·七种武器 (读客知识小说文库）(套装共4册) (古龙) (z-library.sk, 1lib.sk, z-lib.sk).epub")
OUT_DIR = os.path.join(os.path.dirname(__file__), "chapters")

SKIP_TITLES = {'目录', 'Contents', '版权信息', '封面'}


def safe_filename(title: str) -> str:
    title = title.strip()
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    return title.replace(' ', '_')


def html_to_text(soup: BeautifulSoup) -> str:
    lines = []
    body = soup.find('body') or soup
    for tag in body.descendants:
        if not hasattr(tag, 'name'):
            continue
        if tag.name in ('h1', 'h2', 'h3', 'h4'):
            text = tag.get_text(strip=True)
            if text:
                lines.append(f"\n## {text}\n")
        elif tag.name == 'p':
            text = tag.get_text(strip=True)
            if text:
                lines.append(text)
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    current_title = None
    current_lines = []
    saved = 0

    def flush():
        nonlocal saved
        if current_title and current_lines:
            filename = safe_filename(current_title) + '.md'
            content = '\n'.join(current_lines)
            with open(os.path.join(OUT_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(f"# {current_title}\n\n{content}\n")
            print(f"  {filename}")
            saved += 1

    with zipfile.ZipFile(EPUB) as z:
        htmls = sorted([n for n in z.namelist() if n.endswith(('.html', '.xhtml'))])
        for name in htmls:
            content = z.read(name).decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            h3 = soup.find('h3')
            if h3:
                story_title = h3.get_text(strip=True)
                if story_title not in SKIP_TITLES:
                    flush()
                    current_title = story_title
                    current_lines = [html_to_text(soup)]
                    continue
            if current_title:
                text = html_to_text(soup)
                if text:
                    current_lines.append(text)

    flush()
    print(f"\n共拆分 {saved} 个故事 → {OUT_DIR}")


if __name__ == '__main__':
    main()
