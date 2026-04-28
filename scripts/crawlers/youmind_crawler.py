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

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import configparser

# 如果在 Python 3.7 环境没有 configparser，用 json 代替
try:
    import configparser
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sources.json'), 'r') as f:
        SOURCES = json.load(f)
except:
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sources.json'), 'r') as f:
        SOURCES = json.load(f)


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

    # 尝试多种选择器适配页面结构变化
    # 基于已知的页面结构：prompt 内容在 article 或特定容器内
    cards = soup.select('article') or soup.select('.prompt-item') or soup.select('[class*="prompt"]')

    # 尝试找主内容区
    main_content = soup.select_one('main') or soup

    # 查找所有可能包含 prompt 的元素
    # 基于已扒页面：每个 prompt 是独立的文本块，包含 "Prompt" 关键词
    prompt_elements = main_content.find_all(['div', 'article'], recursive=True)

    for el in prompt_elements:
        # 查找 prompt 文本：通常在 <code>, <pre>, 或特定 class 中
        prompt_text_el = el.select_one('code') or el.select_one('pre') or el.select_one('[class*="prompt-text"]')
        if not prompt_text_el:
            # 尝试找包含 "Prompt" 标签的下一个兄弟元素
            prompt_label = el.find(string=lambda t: t and 'Prompt' in t and ':' in t)
            if prompt_label:
                parent = prompt_label.find_parent()
                if parent:
                    prompt_text_el = parent.find_next_sibling()

        if not prompt_text_el:
            continue

        prompt_text = prompt_text_el.get_text(strip=True)
        if len(prompt_text) < 10:  # 太短的不是真正 prompt
            continue

        # 提取标题（通常是相邻的 h3 或前面的标题元素）
        title_el = el.select_one('h3') or el.select_one('h2') or el.select_one('[class*="title"]')
        title = title_el.get_text(strip=True) if title_el else prompt_text[:50] + '...'

        # 提取作者
        author_el = el.select_one('[class*="author"]') or el.select_one('[class*="by"]') or el.select_one('a[href*="/@"]')
        author = author_el.get_text(strip=True).replace('@', '') if author_el else 'Anonymous'

        # 提取日期
        date_el = el.select_one('time') or el.select_one('[class*="date"]') or el.select_one('[class*="time"]')
        date = date_el.get_text(strip=True) if date_el else ''

        # 提取描述
        desc_el = el.select_one('p')
        description = desc_el.get_text(strip=True) if desc_el else ''

        # 判断分类
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
    elif any(k in text for k in ['social media', 'instagram', 'facebook', 'twitter', 'post ', 'feed']):
        return 'social-media'
    elif any(k in text for k in ['infographic', 'education', 'edu visual', 'chart', 'diagram']):
        return 'infographic'
    elif any(k in text for k in ['youtube', 'thumbnail', 'yt thumbnail']):
        return 'youtube-thumbnail'
    elif any(k in text for k in ['comic', 'storyboard', 'manga', 'illustration']):
        return 'comic-storyboard'
    elif any(k in text for k in ['poster', 'flyer', 'brochure']):
        return 'poster-flyer'
    elif any(k in text for k in ['app ', 'web design', 'ui ', 'ux ', 'website', 'landing']):
        return 'app-web-design'
    else:
        return 'avatar'  # 默认分类


def crawl_youmind():
    """主采集函数"""
    results = []
    youmind_config = SOURCES.get('youmind', {})

    if not youmind_config.get('enabled', True):
        print("[youmind] Disabled in config")
        return []

    for url in youmind_config.get('urls', []):
        print(f"[youmind] Crawling: {url}")
        html = fetch_page(url)
        prompts = parse_youmind_prompts(html, url)
        print(f"[youmind] Found {len(prompts)} prompts from {url}")
        results.extend(prompts)

        # 礼貌限速
        rate_limit = youmind_config.get('rate_limit_seconds', 5)
        time.sleep(rate_limit)

    return results


if __name__ == '__main__':
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw_youmind.json')
    prompts = crawl_youmind()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"[youmind] Saved {len(prompts)} prompts to {output_path}")
