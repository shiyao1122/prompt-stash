"""
YouMind 爬虫 - 抓取 youmind.com 的 GPT Image prompts
Python 3.7 兼容
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import sys

import subprocess

# 项目根目录（scripts/crawlers/ → project root）
# 往上走 3 层：crawlers/ → crawlers/../ → scripts/../ → root
_script_abspath = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath('scripts/crawlers')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_script_abspath)))

# 保险机制：用 git rev-parse 确保拿到真实 repo 根目录
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


def load_config():
    """加载配置文件"""
    config_path = os.path.join(PROJECT_ROOT, 'config', 'sources.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def fetch_page(url, timeout=15):
    """抓取单个页面"""
    headers = {'User-Agent': USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[youmind] Failed to fetch {url}: {e}")
        return None


def parse_youmind_prompts(html_content, source_url):
    """解析 youmind 页面，提取 prompt 列表"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    prompts = []

    main_content = soup.select_one('main') or soup
    prompt_elements = main_content.find_all(['div', 'article'], recursive=True)

    for el in prompt_elements:
        # 查找 prompt 文本
        prompt_text_el = el.select_one('code') or el.select_one('pre') or el.select_one('[class*="prompt-text"]')
        if not prompt_text_el:
            continue

        prompt_text = prompt_text_el.get_text(strip=True)
        if len(prompt_text) < 10:
            continue

        # 标题
        title_el = el.select_one('h3') or el.select_one('h2') or el.select_one('[class*="title"]')
        title = title_el.get_text(strip=True) if title_el else prompt_text[:50] + '...'

        # 作者
        author_el = el.select_one('[class*="author"]') or el.select_one('a[href*="/@"]')
        author = author_el.get_text(strip=True).replace('@', '') if author_el else 'Anonymous'

        # 日期
        date_el = el.select_one('time') or el.select_one('[class*="date"]')
        date = date_el.get_text(strip=True) if date_el else ''

        # 描述
        desc_el = el.select_one('p')
        description = desc_el.get_text(strip=True) if desc_el else ''

        # 分类
        category = infer_category(title, description, prompt_text)

        prompts.append({
            'title': title,
            'prompt_text': prompt_text,
            'author': author,
            'date': date,
            'description': description,
            'category': category,
            'source': 'youmind',
            'source_url': source_url
        })

    return prompts


def infer_category(title, description, prompt_text):
    """根据标题/描述推断分类"""
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


def crawl_youmind():
    """主采集函数"""
    results = []
    sources = load_config()
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
