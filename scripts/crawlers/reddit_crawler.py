"""
Reddit 爬虫 - 通过 Reddit API 抓取含 GPT Image 关键词的 posts
Python 3.7 兼容
"""
import requests
import json
import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def load_config():
    config_path = os.path.join(PROJECT_ROOT, 'config', 'sources.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_reddit_subreddit(subreddit, max_posts=50):
    """通过 Reddit API 获取 subreddit 帖子"""
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    params = {'limit': max_posts, 'raw_json': 1}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[reddit] Failed to fetch r/{subreddit}: {e}")
        return None


def extract_prompts_from_reddit(data, keywords):
    """从 Reddit API 响应中提取含关键词的 prompts"""
    prompts = []
    try:
        children = data.get('data', {}).get('children', [])
    except:
        return []

    for post in children:
        post_data = post.get('data', {})
        title = post_data.get('title', '')
        selftext = post_data.get('selftext', '')
        permalink = post_data.get('permalink', '')
        author = post_data.get('author', '')
        created_utc = post_data.get('created_utc', 0)

        full_text = f"{title} {selftext}".lower()

        matched_keyword = None
        for kw in keywords:
            if kw.lower() in full_text:
                matched_keyword = kw
                break

        if not matched_keyword:
            continue

        prompt_text = ''
        if selftext:
            lines = selftext.split('\n')
            for i, line in enumerate(lines):
                if 'prompt' in line.lower() and i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                    if len(candidate) > 20:
                        prompt_text = candidate
                        break
            if not prompt_text:
                for line in lines:
                    line = line.strip()
                    if len(line) > 50 and not line.startswith('http'):
                        prompt_text = line
                        break

        if not prompt_text:
            prompt_text = title

        category = infer_category(title, selftext, prompt_text)

        prompts.append({
            'title': title[:100],
            'prompt_text': prompt_text,
            'author': author,
            'date': time.strftime('%Y-%m-%d', time.gmtime(created_utc)),
            'description': selftext[:200] if selftext else '',
            'category': category,
            'source': 'reddit',
            'source_url': f"https://reddit.com{permalink}",
            'matched_keyword': matched_keyword
        })

    return prompts


def infer_category(title, description, prompt_text):
    """根据文本推断分类"""
    text = f"{title} {description} {prompt_text}".lower()

    if any(k in text for k in ['avatar', 'profile', 'portrait', 'selfie', 'headshot']):
        return 'avatar'
    elif any(k in text for k in ['social media', 'instagram', 'facebook', 'post ', 'feed', 'ad ']):
        return 'social-media'
    elif any(k in text for k in ['infographic', 'education', 'chart', 'diagram']):
        return 'infographic'
    elif any(k in text for k in ['youtube', 'thumbnail']):
        return 'youtube-thumbnail'
    elif any(k in text for k in ['comic', 'storyboard', 'manga']):
        return 'comic-storyboard'
    elif any(k in text for k in ['poster', 'flyer', 'brochure']):
        return 'poster-flyer'
    elif any(k in text for k in ['app ', 'web design', 'ui ', 'website']):
        return 'app-web-design'
    else:
        return 'avatar'


def crawl_reddit():
    """主采集函数"""
    results = []
    sources = load_config()
    reddit_config = sources.get('reddit', {})

    if not reddit_config.get('enabled', True):
        print("[reddit] Disabled in config")
        return results

    subreddits = reddit_config.get('subreddits', ['ChatGPT'])
    keywords = reddit_config.get('keywords', ['GPT Image'])
    max_per_sub = reddit_config.get('max_per_subreddit', 50)

    for sub in subreddits:
        print(f"[reddit] Fetching r/{sub}...")
        data = fetch_reddit_subreddit(sub, max_per_sub)
        if data:
            prompts = extract_prompts_from_reddit(data, keywords)
            print(f"[reddit] Found {len(prompts)} GPT Image prompts from r/{sub}")
            results.extend(prompts)
        time.sleep(2)

    return results


if __name__ == '__main__':
    output_path = os.path.join(PROJECT_ROOT, 'data', 'raw_reddit.json')
    prompts = crawl_reddit()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"[reddit] Saved {len(prompts)} prompts to {output_path}")
