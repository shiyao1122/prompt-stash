"""
静态站点生成器 - 读取 prompts.db，生成 HitPaw 风格的静态 HTML 页面
Design DNA: HitPaw OneClaw aesthetic — SaaS product landing page
"""
import os
import sys
import sqlite3
import json
from datetime import datetime

import subprocess

_script_abspath = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath('scripts/publisher')
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
    return [{'slug': row['category'] or 'all', 'name': (row['category'] or 'all').replace('-', ' ').title(), 'count': row['cnt']} for row in rows]


def load_prompts_by_category(category=None, limit=300):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if category and category != 'all':
        c.execute('SELECT * FROM prompts WHERE category = ? ORDER BY last_seen DESC LIMIT ?', (category, limit))
    else:
        c.execute('SELECT * FROM prompts ORDER BY last_seen DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def esc(s):
    return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'", '&#39;')


def generate_prompt_card(prompt, try_url):
    title = esc((prompt.get('title') or 'Untitled')[:80])
    prompt_text = prompt.get('prompt_text', '')
    author = esc(prompt.get('author') or 'Anonymous')
    category = esc(prompt.get('category') or 'all')
    date = esc((str(prompt.get('last_seen') or '')[:10]))
    preview = esc(prompt_text[:120] + ('...' if len(prompt_text) > 120 else ''))
    text_esc = esc(prompt_text[:300] + ('...' if len(prompt_text) > 300 else ''))

    return f'''
    <article class="prompt-card" data-category="{category}">
        <div class="card-header">
            <span class="card-tag">{category.replace('-', ' ')}</span>
            <span class="card-author">@{author}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-preview">{preview}</p>
        <div class="card-text-block">
            <code class="card-text">{text_esc}</code>
        </div>
        <div class="card-footer">
            <span class="card-date">{date}</span>
            <a href="{esc(try_url)}" class="btn-copy" target="_blank" rel="noopener">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                Copy
            </a>
        </div>
    </article>'''


def generate_page(prompts, categories, config):
    try_url = config.get('try_it_now_url', '#')
    total_count = sum(c['count'] for c in categories) if categories else len(prompts)
    filter_buttons = ''.join([
        f'<button class="filter-btn{" active" if cat["slug"]=="all" else ""}" data-category="{cat["slug"]}">'
        f'{cat["name"]} <span class="count">{cat["count"]}</span></button>'
        for cat in [{'slug':'all','name':'All','count':total_count}] + categories
    ])

    site_name = esc(config.get('name', 'PromptStash'))
    tagline = esc(config.get('tagline', ''))
    description = esc(config.get('description', ''))

    prompt_cards_html = '\n'.join([generate_prompt_card(p, try_url) for p in prompts])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_name} — {tagline}</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="https://promptstash.com">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        /* ===== HitPaw OneClaw Design DNA — CSS Custom Properties ===== */
        :root {{
            /* Color — SaaS purple palette */
            --color-primary: #7B61FF;
            --color-primary-dark: #6D28D9;
            --color-secondary: #9484E8;
            --color-accent: #FF6B00;
            --color-bg: #F8F9FF;
            --color-bg-alt: #E0E7FF;
            --color-surface: #FFFFFF;
            --color-text: #111827;
            --color-text-muted: #6B7283;
            --color-border: #E5E7EB;
            --color-nav: #0B0B0E;

            /* Elevation — soft diffused shadows */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.10);
            --shadow-lg: 0 8px 32px rgba(0,0,0,0.14);

            /* Shape — consistent border radius */
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 20px;
            --radius-pill: 9999px;

            /* Typography */
            --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        /* ===== Reset & Base ===== */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font);
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        /* ===== Top Navigation ===== */
        .nav {{
            position: sticky; top: 0; z-index: 100;
            background: var(--color-nav);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .nav-inner {{
            max-width: 1200px; margin: 0 auto;
            padding: 0 24px;
            height: 60px;
            display: flex; align-items: center; justify-content: space-between;
        }}
        .nav-logo {{ color: white; font-size: 1rem; font-weight: 700; text-decoration: none; letter-spacing: -0.01em; }}
        .nav-logo span {{ color: var(--color-primary); }}
        .nav-links {{ display: flex; gap: 32px; list-style: none; }}
        .nav-links a {{ color: rgba(255,255,255,0.7); text-decoration: none; font-size: 0.875rem; font-weight: 500; transition: color 0.2s; }}
        .nav-links a:hover {{ color: white; }}
        .nav-cta {{
            display: inline-flex; align-items: center; gap: 6px;
            background: var(--color-primary); color: white;
            padding: 8px 18px; border-radius: var(--radius-md);
            font-size: 0.875rem; font-weight: 600;
            text-decoration: none; transition: all 0.2s;
        }}
        .nav-cta:hover {{ background: var(--color-primary-dark); transform: translateY(-1px); }}

        /* ===== Hero Section ===== */
        .hero {{
            background: linear-gradient(180deg, #F8F9FF 0%, #E8EFFF 100%);
            padding: 80px 24px 72px;
            text-align: center;
        }}
        .hero-inner {{ max-width: 720px; margin: 0 auto; }}
        .hero-badge {{
            display: inline-block;
            background: rgba(123,97,255,0.10);
            border: 1px solid rgba(123,97,255,0.2);
            color: var(--color-primary);
            padding: 5px 14px; border-radius: var(--radius-pill);
            font-size: 0.8rem; font-weight: 600;
            letter-spacing: 0.04em; text-transform: uppercase;
            margin-bottom: 24px;
        }}
        .hero h1 {{
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 800; line-height: 1.08;
            letter-spacing: -0.03em;
            color: var(--color-text);
            margin-bottom: 20px;
        }}
        .hero h1 span {{ color: var(--color-primary); }}
        .hero p {{
            font-size: 1.125rem; color: var(--color-text-muted);
            line-height: 1.65; max-width: 560px;
            margin: 0 auto 36px;
        }}
        .hero-actions {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
        .btn-primary {{
            display: inline-flex; align-items: center; gap: 8px;
            background: var(--color-primary); color: white;
            padding: 12px 28px; border-radius: var(--radius-md);
            font-size: 0.9375rem; font-weight: 600;
            text-decoration: none; transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
            box-shadow: 0 4px 14px rgba(123,97,255,0.35);
        }}
        .btn-primary:hover {{ background: var(--color-primary-dark); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(123,97,255,0.45); }}
        .btn-secondary {{
            display: inline-flex; align-items: center; gap: 8px;
            background: transparent; color: var(--color-text);
            padding: 12px 28px; border-radius: var(--radius-md);
            border: 1.5px solid var(--color-border);
            font-size: 0.9375rem; font-weight: 500;
            text-decoration: none; transition: all 0.25s;
        }}
        .btn-secondary:hover {{ border-color: var(--color-primary); color: var(--color-primary); background: rgba(123,97,255,0.04); }}

        /* ===== Stats Bar ===== */
        .stats-bar {{
            background: var(--color-surface);
            border-bottom: 1px solid var(--color-border);
            padding: 14px 24px;
        }}
        .stats-bar-inner {{
            max-width: 1200px; margin: 0 auto;
            display: flex; gap: 32px; flex-wrap: wrap;
            font-size: 0.875rem; color: var(--color-text-muted);
        }}
        .stat-item strong {{ color: var(--color-text); font-weight: 600; }}
        .stat-item {{ display: flex; gap: 6px; align-items: center; }}
        .stat-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--color-primary); flex-shrink: 0; }}

        /* ===== Filter Bar ===== */
        .filter-bar {{
            background: rgba(255,255,255,0.92);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--color-border);
            padding: 14px 24px;
            position: sticky; top: 60px; z-index: 90;
        }}
        .filter-bar-inner {{
            max-width: 1200px; margin: 0 auto;
            display: flex; gap: 8px; overflow-x: auto;
            padding-bottom: 2px;
        }}
        .filter-btn {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 7px 16px; border-radius: var(--radius-pill);
            border: 1.5px solid var(--color-border);
            background: var(--color-surface);
            color: var(--color-text-muted);
            font-size: 0.8125rem; font-weight: 500;
            cursor: pointer; white-space: nowrap;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{ border-color: var(--color-primary); color: var(--color-primary); background: rgba(123,97,255,0.04); }}
        .filter-btn.active {{ background: var(--color-primary); border-color: var(--color-primary); color: white; }}
        .filter-btn .count {{ font-size: 0.75rem; opacity: 0.7; }}

        /* ===== Main Content ===== */
        .main {{ max-width: 1200px; margin: 0 auto; padding: 48px 24px 80px; }}
        .section-label {{
            font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.08em; color: var(--color-text-muted);
            margin-bottom: 24px;
        }}

        /* ===== Prompt Grid ===== */
        .prompts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .prompt-card {{
            background: var(--color-surface);
            border-radius: var(--radius-lg);
            border: 1px solid var(--color-border);
            padding: 24px;
            display: flex; flex-direction: column; gap: 14px;
            box-shadow: var(--shadow-sm);
            transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
        }}
        .prompt-card:hover {{
            box-shadow: var(--shadow-md);
            transform: translateY(-3px);
            border-color: rgba(123,97,255,0.25);
        }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .card-tag {{
            background: rgba(123,97,255,0.08);
            color: var(--color-primary);
            padding: 4px 10px; border-radius: var(--radius-sm);
            font-size: 0.75rem; font-weight: 600;
            text-transform: capitalize;
        }}
        .card-author {{ color: var(--color-text-muted); font-size: 0.8rem; }}
        .card-title {{
            font-size: 1rem; font-weight: 600;
            color: var(--color-text); line-height: 1.4;
        }}
        .card-preview {{ font-size: 0.875rem; color: var(--color-text-muted); line-height: 1.55; }}
        .card-text-block {{
            background: #F5F6FA;
            border-radius: var(--radius-sm);
            padding: 12px 14px;
            border: 1px solid var(--color-border);
            flex: 1;
        }}
        .card-text {{
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            font-size: 0.775rem; color: #4B5563;
            line-height: 1.65; word-break: break-word;
            display: block;
        }}
        .card-footer {{
            display: flex; justify-content: space-between; align-items: center;
            padding-top: 12px; border-top: 1px solid var(--color-border);
        }}
        .card-date {{ font-size: 0.75rem; color: var(--color-text-muted); }}
        .btn-copy {{
            display: inline-flex; align-items: center; gap: 5px;
            background: rgba(123,97,255,0.08);
            color: var(--color-primary);
            padding: 6px 14px; border-radius: var(--radius-sm);
            font-size: 0.8rem; font-weight: 600;
            text-decoration: none; transition: all 0.2s;
            border: 1px solid rgba(123,97,255,0.15);
        }}
        .btn-copy:hover {{ background: var(--color-primary); color: white; border-color: var(--color-primary); }}

        /* ===== CTA Section ===== */
        .cta-section {{
            background: linear-gradient(135deg, #4C39B5 0%, #6D28D9 40%, #7B61FF 70%, #9484E8 100%);
            padding: 96px 24px;
            text-align: center;
            position: relative; overflow: hidden;
        }}
        .cta-section::before {{
            content: ''; position: absolute; inset: 0;
            background: radial-gradient(ellipse at 50% 120%, rgba(255,255,255,0.12) 0%, transparent 70%);
            pointer-events: none;
        }}
        .cta-inner {{ max-width: 640px; margin: 0 auto; position: relative; }}
        .cta-section h2 {{
            font-size: clamp(1.5rem, 4vw, 2.25rem);
            font-weight: 800; color: white;
            line-height: 1.1; letter-spacing: -0.025em;
            margin-bottom: 16px;
        }}
        .cta-section p {{ font-size: 1.0625rem; color: rgba(255,255,255,0.8); margin-bottom: 36px; line-height: 1.6; }}
        .cta-actions {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
        .btn-cta-primary {{
            display: inline-flex; align-items: center; gap: 8px;
            background: white; color: #4C39B5;
            padding: 14px 32px; border-radius: var(--radius-md);
            font-size: 1rem; font-weight: 700;
            text-decoration: none; transition: all 0.25s;
        }}
        .btn-cta-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }}
        .btn-cta-secondary {{
            display: inline-flex; align-items: center; gap: 8px;
            background: transparent; color: white;
            padding: 14px 32px; border-radius: var(--radius-md);
            border: 1.5px solid rgba(255,255,255,0.4);
            font-size: 1rem; font-weight: 600;
            text-decoration: none; transition: all 0.25s;
        }}
        .btn-cta-secondary:hover {{ border-color: white; background: rgba(255,255,255,0.1); }}

        /* ===== Footer ===== */
        .footer {{
            background: var(--color-nav);
            padding: 48px 24px;
            text-align: center;
        }}
        .footer p {{ color: rgba(255,255,255,0.5); font-size: 0.875rem; }}
        .footer a {{ color: rgba(255,255,255,0.8); text-decoration: none; }}
        .footer a:hover {{ color: white; }}
        .footer-brand {{ font-size: 1rem; font-weight: 700; color: white; margin-bottom: 12px; display: block; }}
        .footer-brand span {{ color: var(--color-primary); }}

        /* ===== Empty State ===== */
        .empty-state {{ text-align: center; padding: 80px 24px; }}
        .empty-state h3 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 8px; color: var(--color-text); }}
        .empty-state p {{ color: var(--color-text-muted); font-size: 0.9375rem; }}

        /* ===== Responsive ===== */
        @media (max-width: 768px) {{
            .nav-links {{ display: none; }}
            .hero {{ padding: 56px 24px 48px; }}
            .hero h1 {{ font-size: 1.875rem; }}
            .prompts-grid {{ grid-template-columns: 1fr; }}
            .stats-bar-inner {{ gap: 16px; }}
            .cta-section {{ padding: 64px 24px; }}
        }}

        /* ===== Dark Mode ===== */
        @media (prefers-color-scheme: dark) {{
            body {{ background: #0F0F1A; color: #F3F4F6; }}
            .nav {{ background: rgba(11,11,14,0.95); }}
            .hero {{ background: linear-gradient(180deg, #0F0F1A 0%, #1A1333 100%); }}
            .hero h1 {{ color: #F3F4F6; }}
            .hero p {{ color: rgba(255,255,255,0.6); }}
            .filter-bar {{ background: rgba(15,15,26,0.92); }}
            .prompt-card {{ background: #1A1A2E; border-color: #2D2D4A; }}
            .card-text-block {{ background: #12121F; border-color: #2D2D4A; }}
            .card-text {{ color: #C5CAE9; }}
            .prompt-title {{ color: #E8EAF6; }}
            .stats-bar {{ background: #1A1A2E; }}
            .stats-bar-inner {{ color: rgba(255,255,255,0.5); }}
            .stat-item strong {{ color: #F3F4F6; }}
        }}
    </style>
</head>
<body>

    <!-- Navigation -->
    <nav class="nav">
        <div class="nav-inner">
            <a href="/" class="nav-logo">Prompt<span>Stash</span></a>
            <ul class="nav-links">
                <li><a href="#prompts">Prompts</a></li>
                <li><a href="#about">About</a></li>
            </ul>
            <a href="{esc(try_url)}" class="nav-cta">Try it Free</a>
        </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
        <div class="hero-inner">
            <div class="hero-badge">GPT Image Prompts Collection</div>
            <h1>Discover the Best <span>GPT Image</span> Prompts</h1>
            <p>Curated, high-quality prompts for avatar, social media, infographics, and more — updated automatically from top sources.</p>
            <div class="hero-actions">
                <a href="#prompts" class="btn-primary">Browse Prompts →</a>
                <a href="{esc(try_url)}" class="btn-secondary">Try in YouMind</a>
            </div>
        </div>
    </section>

    <!-- Stats Bar -->
    <div class="stats-bar">
        <div class="stats-bar-inner">
            <span class="stat-item"><span class="stat-dot"></span><strong id="total-count">{total_count}</strong> prompts</span>
            <span class="stat-item">Updated <strong>{datetime.now().strftime("%Y-%m-%d")}</strong></span>
            <span class="stat-item">Source: <strong>YouMind</strong></span>
        </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar" id="filter-bar-wrapper">
        <div class="filter-bar-inner" id="filter-bar">{filter_buttons}</div>
    </div>

    <!-- Main Content -->
    <main class="main" id="prompts">
        <p class="section-label">All Prompts</p>
        <div class="prompts-grid" id="prompts-grid">
            {prompt_cards_html if prompt_cards_html else '<div class="empty-state"><h3>No prompts yet</h3><p>Run the crawler scripts to populate the database.</p></div>'}
        </div>
    </main>

    <!-- CTA Section -->
    <section class="cta-section" id="about">
        <div class="cta-inner">
            <h2>Ready to create something amazing?</h2>
            <p>Use these prompts with GPT Image in YouMind — your all-in-one AI creation workspace.</p>
            <div class="cta-actions">
                <a href="{esc(try_url)}" class="btn-cta-primary" target="_blank" rel="noopener">Try in YouMind →</a>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <span class="footer-brand">Prompt<span>Stash</span></span>
        <p>&copy; {datetime.now().year} PromptStash &mdash; Curated GPT Image prompts for creators</p>
    </footer>

    <!-- Filter Interaction Script -->
    <script>
    (function() {{
        var filterBar = document.getElementById('filter-bar');
        var grid = document.getElementById('prompts-grid');
        if (!filterBar || !grid) return;
        var cards = Array.from(grid.querySelectorAll('.prompt-card'));

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

            var sectionLabel = document.querySelector('.section-label');
            if (sectionLabel) {{
                sectionLabel.textContent = cat === 'all' ? 'All Prompts' : btn.textContent.trim().replace(/\\s+\\d+$/, '') + ' Prompts';
            }}
        }});

        // Copy button — write prompt text to clipboard
        grid.addEventListener('click', function(e) {{
            var btn = e.target.closest('.btn-copy');
            if (!btn) return;
            var card = btn.closest('.prompt-card');
            if (!card) return;
            var textEl = card.querySelector('.card-text');
            if (!textEl) return;
            navigator.clipboard.writeText(textEl.textContent).then(function() {{
                var original = btn.innerHTML;
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
                btn.style.background = '#10B981';
                btn.style.color = 'white';
                btn.style.borderColor = '#10B981';
                setTimeout(function() {{
                    btn.innerHTML = original;
                    btn.style.background = '';
                    btn.style.color = '';
                    btn.style.borderColor = '';
                }}, 2000);
            }}).catch(function() {{}});
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

    total = sum(c['count'] for c in categories) if categories else len(prompts)
    print(f"[generator] Done — {total} prompts, {len(categories)} categories")
    print(f"[generator] Output: {output_path}")


if __name__ == '__main__':
    generate_site()
