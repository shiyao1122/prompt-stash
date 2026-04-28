"""
静态站点生成器 - 读取 prompts.db，生成静态 HTML 页面
Python 3.7 兼容
"""
import os
import sys
import sqlite3
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def get_db_path():
    return os.path.join(PROJECT_ROOT, 'data', 'prompts.db')


def get_output_path():
    return os.path.join(PROJECT_ROOT, 'outputs', 'site')


def load_site_config():
    config_path = os.path.join(PROJECT_ROOT, 'config', 'site.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_categories():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT DISTINCT category, COUNT(*) as cnt FROM prompts GROUP BY category ORDER BY cnt DESC')
    rows = c.fetchall()
    conn.close()

    categories = []
    for row in rows:
        slug = row['category'] or 'all'
        categories.append({
            'slug': slug,
            'name': slug.replace('-', ' ').title(),
            'count': row['cnt']
        })
    return categories


def load_prompts_by_category(category=None, limit=300):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if category and category != 'all':
        c.execute(
            'SELECT * FROM prompts WHERE category = ? ORDER BY last_seen DESC LIMIT ?',
            (category, limit)
        )
    else:
        c.execute('SELECT * FROM prompts ORDER BY last_seen DESC LIMIT ?', (limit,))

    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def generate_prompt_card(prompt, try_url):
    title = prompt.get('title', 'Untitled') or 'Untitled'
    prompt_text = prompt.get('prompt_text', '')
    author = prompt.get('author', 'Anonymous') or 'Anonymous'
    category = prompt.get('category', 'all') or 'all'
    date = prompt.get('last_seen', '')[:10] if prompt.get('last_seen') else ''

    preview = prompt_text[:150] + ('...' if len(prompt_text) > 150 else '')

    def esc(s):
        return (s or '')
    esc = lambda s: (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    return f'''
    <div class="prompt-card" data-category="{esc(category)}">
        <div class="prompt-card-header">
            <span class="prompt-category-tag">{esc(category.replace('-',' '))}</span>
            <span class="prompt-author">@{esc(author)}</span>
        </div>
        <h3 class="prompt-title">{esc(title[:80])}</h3>
        <p class="prompt-desc">{esc(preview)}</p>
        <div class="prompt-text-block">
            <code class="prompt-text">{esc(prompt_text[:300])}{'...' if len(prompt_text)>300 else ''}</code>
        </div>
        <div class="prompt-card-footer">
            <span class="prompt-date">{esc(date)}</span>
            <a href="{esc(try_url)}" class="btn-try" target="_blank" rel="noopener">Try it now →</a>
        </div>
    </div>'''


def generate_page(prompts, categories, config):
    try_url = config.get('try_it_now_url', '#')
    prompt_cards_html = '\n'.join([generate_prompt_card(p, try_url) for p in prompts])

    total_count = sum(c['count'] for c in categories) if categories else len(prompts)
    filter_buttons = ''.join([
        f'<button class="filter-btn {"active" if cat["slug"]=="all" else ""}" data-category="{cat["slug"]}">'
        f'{cat["name"]} <span class="count">{cat["count"]}</span></button>'
        for cat in [{'slug':'all','name':'All','count':total_count}] + categories
    ])

    site_name = config.get('name', 'PromptStash')
    tagline = config.get('tagline', '')
    description = config.get('description', '')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_name} — {tagline}</title>
    <meta name="description" content="{description}">
    <meta property="og:title" content="{site_name}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <link rel="canonical" href="https://promptstash.com">
    <style>
        :root {{
            --color-primary: #4F46E5;
            --color-primary-dark: #4338CA;
            --color-secondary: #10B981;
            --color-bg: #F9FAFB;
            --color-surface: #FFFFFF;
            --color-text: #111827;
            --color-text-muted: #6B7280;
            --color-border: #E5E7EB;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            --font-heading: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--font-body); background: var(--color-bg); color: var(--color-text); line-height: 1.6; }}
        .hero {{
            background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%);
            padding: 80px 20px 60px; text-align: center; color: white;
        }}
        .hero h1 {{ font-size: 2.5rem; font-weight: 800; margin-bottom: 16px; letter-spacing: -0.02em; }}
        .hero p {{ font-size: 1.125rem; opacity: 0.9; max-width: 600px; margin: 0 auto 32px; }}
        .hero-badge {{ display: inline-block; background: rgba(255,255,255,0.15); padding: 6px 16px; border-radius: 100px; font-size: 0.875rem; margin-bottom: 20px; backdrop-filter: blur(8px); }}
        .hero-cta {{
            display: inline-flex; align-items: center; gap: 8px;
            background: var(--color-secondary); color: white;
            padding: 14px 28px; border-radius: var(--radius-md); font-weight: 600;
            text-decoration: none; transition: all 0.2s;
        }}
        .hero-cta:hover {{ background: #059669; transform: translateY(-1px); box-shadow: var(--shadow-lg); }}
        .filter-bar {{ background: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: 16px 20px; position: sticky; top: 0; z-index: 100; backdrop-filter: blur(10px); background: rgba(255,255,255,0.95); }}
        .filter-bar-inner {{ max-width: 1200px; margin: 0 auto; display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }}
        .filter-btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: 1px solid var(--color-border); border-radius: 100px; background: var(--color-surface); color: var(--color-text-muted); font-size: 0.875rem; font-weight: 500; cursor: pointer; white-space: nowrap; transition: all 0.2s; }}
        .filter-btn:hover {{ border-color: var(--color-primary); color: var(--color-primary); }}
        .filter-btn.active {{ background: var(--color-primary); border-color: var(--color-primary); color: white; }}
        .filter-btn .count {{ background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 100px; font-size: 0.75rem; }}
        .filter-btn.active .count {{ background: rgba(255,255,255,0.2); }}
        .main-content {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .prompts-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
        .prompt-card {{ background: var(--color-surface); border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow-sm); border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 12px; transition: all 0.2s; }}
        .prompt-card:hover {{ box-shadow: var(--shadow-md); transform: translateY(-2px); }}
        .prompt-card-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .prompt-category-tag {{ background: #EEF2FF; color: var(--color-primary); padding: 4px 10px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; text-transform: capitalize; }}
        .prompt-author {{ color: var(--color-text-muted); font-size: 0.8rem; }}
        .prompt-title {{ font-size: 1rem; font-weight: 600; color: var(--color-text); line-height: 1.4; }}
        .prompt-desc {{ font-size: 0.875rem; color: var(--color-text-muted); line-height: 1.5; }}
        .prompt-text-block {{ background: #F3F4F6; border-radius: var(--radius-sm); padding: 12px; border: 1px solid var(--color-border); }}
        .prompt-text {{ font-family: 'SF Mono','Monaco','Inconsolata',monospace; font-size: 0.8rem; color: #374151; word-break: break-word; display: block; line-height: 1.6; }}
        .prompt-card-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 8px; border-top: 1px solid var(--color-border); }}
        .prompt-date {{ font-size: 0.75rem; color: var(--color-text-muted); }}
        .btn-try {{ background: var(--color-primary); color: white; padding: 8px 16px; border-radius: var(--radius-sm); font-size: 0.875rem; font-weight: 500; text-decoration: none; transition: all 0.2s; }}
        .btn-try:hover {{ background: var(--color-primary-dark); }}
        .footer {{ border-top: 1px solid var(--color-border); padding: 40px 20px; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; margin-top: 60px; }}
        .footer a {{ color: var(--color-primary); text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
        .stats-bar {{ background: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: 12px 20px; }}
        .stats-bar-inner {{ max-width: 1200px; margin: 0 auto; display: flex; gap: 24px; font-size: 0.875rem; color: var(--color-text-muted); }}
        .stat-item strong {{ color: var(--color-text); }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: var(--color-text-muted); }}
        .empty-state h3 {{ font-size: 1.25rem; margin-bottom: 8px; color: var(--color-text); }}
        @media (max-width: 768px) {{ .hero h1 {{ font-size: 1.75rem; }} .prompts-grid {{ grid-template-columns: 1fr; }} }}
        @media (prefers-color-scheme: dark) {{ body {{ background: #111827; color: #F9FAFB; }} .prompt-card {{ background: #1F2937; border-color: #374151; }} .filter-bar {{ background: rgba(31,41,55,0.95); }} .filter-btn {{ background: #1F2937; color: #9CA3AF; border-color: #374151; }} .prompt-text-block {{ background: #111827; border-color: #374151; }} .stats-bar {{ background: #1F2937; }} }}
    </style>
</head>
<body>
    <section class="hero">
        <div class="hero-badge">GPT Image Prompts Collection</div>
        <h1>{site_name}</h1>
        <p>{description}</p>
        <a href="#" class="hero-cta" id="hero-cta">Try it now — it's free <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></a>
    </section>
    <div class="stats-bar">
        <div class="stats-bar-inner">
            <span class="stat-item"><strong id="total-count">{len(prompts)}</strong> prompts</span>
            <span class="stat-item">Updated <strong>{datetime.now().strftime("%Y-%m-%d %H:%M")}</strong></span>
            <span class="stat-item">Source: <strong>youmind</strong> + <strong>reddit</strong></span>
        </div>
    </div>
    <div class="filter-bar">
        <div class="filter-bar-inner" id="filter-bar">{filter_buttons}</div>
    </div>
    <main class="main-content">
        <div class="prompts-grid" id="prompts-grid">
            {prompt_cards_html if prompt_cards_html else '<div class="empty-state"><h3>No prompts yet</h3><p>Run the crawler scripts to populate the database.</p></div>'}
        </div>
    </main>
    <footer class="footer">
        <p>&copy; {datetime.now().year} <a href="/">{site_name}</a> — {tagline}</p>
        <p style="margin-top:8px; opacity:0.7;">Curated GPT Image prompts for creators</p>
    </footer>
    <script>
    (function() {{
        var tryUrl = "{try_url}";
        if (tryUrl && tryUrl !== '#') document.getElementById('hero-cta').href = tryUrl;

        var filterBar = document.getElementById('filter-bar');
        var grid = document.getElementById('prompts-grid');
        var cards = grid ? Array.from(grid.querySelectorAll('.prompt-card')) : [];

        filterBar.addEventListener('click', function(e) {{
            var btn = e.target.closest('.filter-btn');
            if (!btn) return;
            var cat = btn.dataset.category;

            filterBar.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
            btn.classList.add('active');

            var visible = 0;
            cards.forEach(function(card) {{
                var show = cat === 'all' || card.dataset.category === cat;
                card.style.display = show ? '' : 'none';
                if (show) visible++;
            }});

            var totalEl = document.getElementById('total-count');
            if (totalEl) totalEl.textContent = visible;
        }});
    }})();
    </script>
</body>
</html>'''
    return html


def generate_site():
    print("[generator] Generating static site...")
    config = load_site_config()
    categories = load_categories()
    prompts = load_prompts_by_category()

    output_dir = get_output_path()
    os.makedirs(output_dir, exist_ok=True)

    html = generate_page(prompts, categories, config)

    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[generator] Done — {len(prompts)} prompts, {len(categories)} categories")
    print(f"[generator] Output: {output_path}")
    return output_path


if __name__ == '__main__':
    generate_site()
