"""
YouMind 爬虫 - 抓取 youmind.com 的 GPT Image prompts
从 Next.js __next_f.push 序列化的 React 状态中提取 X.com 推文内容
Python 3.7 兼容
"""
import requests
import re
import json
import time
import os
import sys
import hashlib
import subprocess

# 项目根目录（scripts/crawlers/ → project root）
_script_abspath = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath('scripts/crawlers')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_script_abspath)))

try:
    _git_root = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=PROJECT_ROOT,
        stderr=subprocess.DEVNULL
    ).decode().strip()
    if _git_root:
        PROJECT_ROOT = _git_root
except Exception:
    pass

sys.path.insert(0, PROJECT_ROOT)


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def fetch_page(url, timeout=15):
    headers = {'User-Agent': USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[youmind] Failed to fetch {url}: {e}")
        return None


def infer_category(title, description, prompt_text):
    text = f"{title} {description} {prompt_text}".lower()
    if any(k in text for k in ['avatar', 'profile', 'portrait', 'selfie', 'headshot']):
        return 'avatar'
    elif any(k in text for k in ['social media', 'instagram', 'facebook', 'post ', 'feed']):
        return 'social-media'
    elif any(k in text for k in ['infographic', 'education', 'edu visual', 'chart', 'diagram']):
        return 'infographic'
    elif any(k in text for k in ['youtube', 'thumbnail', 'yt thumbnail']):
        return 'youtube-thumbnail'
    elif any(k in text for k in ['comic', 'storyboard', 'manga', 'illustration']):
        return 'comic-storyboard'
    elif any(k in text for k in ['poster', 'flyer', 'brochure']):
        return 'poster-flyer'
    elif any(k in text for k in ['app ', 'web design', 'ui ', 'ux ', 'website']):
        return 'app-web-design'
    else:
        return 'avatar'


def parse_youmind_prompts(html_content, source_url):
    """
    从 youmind.com Next.js 页面中解析 prompt。
    Prompts 存储在 __next_f.push 序列化块中，格式为 X.com 推文嵌入数据。
    """
    if not html_content:
        return []

    pattern = r'self\.__next_f\.push\(\[1,"(.*?)"\]\)'
    matches = re.findall(pattern, html_content, re.DOTALL)

    prompts = []
    seen = set()

    for raw_m in matches:
        try:
            decoded = raw_m.encode().decode('unicode_escape', 'ignore')
        except Exception:
            decoded = raw_m

        if '"content"' not in decoded or '"sourceLink"' not in decoded:
            continue

        # Extract content value: find "content":"VALUE" ending at ","translatedContent"
        idx = decoded.find('"content":"')
        if idx == -1:
            continue

        start = idx + len('"content":"')
        end_marker = '","translatedContent"'
        end = decoded.find(end_marker, start)
        if end == -1:
            continue

        content = decoded[start:end]
        if len(content) < 15:
            continue

        # Extract source URL
        link_idx = decoded.find('"sourceLink":"')
        if link_idx != -1:
            link_start = link_idx + len('"sourceLink":"')
            link_end = decoded.find('"', link_start)
            src_url = decoded[link_start:link_end]
        else:
            src_url = ''

        # Extract author name
        author_name = 'Anonymous'
        author_idx = decoded.find('"author":{"name":"')
        if author_idx != -1:
            a_start = author_idx + len('"author":{"name":"')
            a_end = decoded.find('"', a_start)
            author_name = decoded[a_start:a_end]

        # Dedupe by content hash
        h = hashlib.md5(content.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)

        title = content[:50].replace('\n', ' ').strip() + '...'
        category = infer_category(title, '', content)

        prompts.append({
            'title': title,
            'prompt_text': content,
            'author': author_name,
            'source': 'youmind',
            'source_url': src_url or source_url,
            'category': category,
            'date': ''
        })

    return prompts


def crawl_youmind():
    results = []
    config_path = os.path.join(PROJECT_ROOT, 'config', 'sources.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    youmind_config = sources.get('youmind', {})
    if not youmind_config.get('enabled', True):
        print("[youmind] Disabled in config")
        return results

    for url in youmind_config.get('urls', []):
        print(f"[youmind] Crawling: {url}")
        html = fetch_page(url)
        prompts = parse_youmind_prompts(html, url)
        print(f"[youmind] Found {len(prompts)} prompts from {url}")
        results.extend(prompts)

        rate_limit = youmind_config.get('rate_limit_seconds', 5)
        time.sleep(rate_limit)

    return results


if __name__ == '__main__':
    output_path = os.path.join(PROJECT_ROOT, 'data', 'raw_youmind.json')
    prompts = crawl_youmind()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"[youmind] Saved {len(prompts)} prompts to {output_path}")
