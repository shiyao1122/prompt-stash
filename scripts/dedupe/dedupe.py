"""
去重模块 - 对所有来源的 prompt 做 hash 去重，入库 SQLite
Python 3.7 兼容
"""
import json
import os
import sys
import hashlib
import sqlite3
from datetime import datetime

import subprocess

_script_abspath = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath('scripts/dedupe')
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


def init_db(db_path):
    """初始化数据库表"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE NOT NULL,
            title TEXT,
            prompt_text TEXT NOT NULL,
            author TEXT,
            source TEXT,
            source_url TEXT,
            category TEXT DEFAULT 'all',
            model TEXT DEFAULT 'gpt-image',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn


def normalize_prompt(text):
    if not text:
        return ''
    return ' '.join(text.lower().split())


def compute_hash(prompt_text):
    normalized = normalize_prompt(prompt_text)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def load_raw_prompts():
    """加载所有原始采集数据"""
    data_dir = os.path.join(PROJECT_ROOT, 'data')
    all_prompts = []

    for src_file in ['raw_youmind.json', 'raw_reddit.json']:
        path = os.path.join(data_dir, src_file)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_prompts.extend(data)
                except json.JSONDecodeError as e:
                    print(f"[dedupe] {src_file}: parse error — {e}")

    print(f"[dedupe] Loaded {len(all_prompts)} raw prompts")
    return all_prompts


def dedupe_and_insert(all_prompts):
    db_path = get_db_path()
    conn = init_db(db_path)
    c = conn.cursor()

    inserted = 0
    skipped = 0

    for p in all_prompts:
        prompt_text = p.get('prompt_text', '').strip()
        if not prompt_text or len(prompt_text) < 10:
            skipped += 1
            continue

        prompt_hash = compute_hash(prompt_text)

        c.execute('SELECT id FROM prompts WHERE prompt_hash = ?', (prompt_hash,))
        if c.fetchone():
            c.execute(
                'UPDATE prompts SET last_seen = CURRENT_TIMESTAMP WHERE prompt_hash = ?',
                (prompt_hash,)
            )
            skipped += 1
            continue

        try:
            c.execute('''
                INSERT INTO prompts (prompt_hash, title, prompt_text, author, source, source_url, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                prompt_hash,
                p.get('title', '')[:200],
                prompt_text,
                p.get('author', 'Anonymous'),
                p.get('source', ''),
                p.get('source_url', ''),
                p.get('category', 'all')
            ))
            inserted += 1
        except Exception as e:
            print(f"[dedupe] Insert error: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def get_stats():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return {}

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM prompts')
    total = c.fetchone()[0] or 0

    c.execute('SELECT category, COUNT(*) FROM prompts GROUP BY category')
    by_category = dict(c.fetchall())

    c.execute('SELECT source, COUNT(*) FROM prompts GROUP BY source')
    by_source = dict(c.fetchall())

    conn.close()
    return {'total': total, 'by_category': by_category, 'by_source': by_source}


def run_dedupe():
    print(f"[dedupe] Started at {datetime.now().isoformat()}")
    all_prompts = load_raw_prompts()
    inserted, skipped = dedupe_and_insert(all_prompts)
    stats = get_stats()

    print(f"[dedupe] Done. Inserted: {inserted}, Skipped: {skipped}")
    print(f"[dedupe] Total in DB: {stats.get('total', 0)}")
    print(f"[dedupe] By category: {stats.get('by_category', {})}")
    print(f"[dedupe] By source: {stats.get('by_source', {})}")
    return stats


if __name__ == '__main__':
    run_dedupe()
