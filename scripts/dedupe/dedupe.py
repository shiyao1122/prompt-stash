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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_path():
    """获取数据库路径"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'prompts.db')


def init_db(db_path):
    """初始化数据库表"""
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            slug TEXT UNIQUE,
            display_name TEXT
        )
    ''')
    conn.commit()
    return conn


def normalize_prompt(text):
    """规范化 prompt 文本用于 hash"""
    if not text:
        return ''
    # 去除多余空白，统一小写
    return ' '.join(text.lower().split())


def compute_hash(prompt_text):
    """计算 prompt 的 MD5 hash"""
    normalized = normalize_prompt(prompt_text)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def load_raw_prompts():
    """加载所有原始采集数据"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')

    all_prompts = []
    sources = ['raw_youmind.json', 'raw_reddit.json']

    for src_file in sources:
        path = os.path.join(data_dir, src_file)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_prompts.extend(data)
                    else:
                        print(f"[dedupe] {src_file}: unexpected format, skipping")
                except json.JSONDecodeError as e:
                    print(f"[dedupe] Failed to parse {src_file}: {e}")

    print(f"[dedupe] Loaded {len(all_prompts)} raw prompts from {len(sources)} sources")
    return all_prompts


def dedupe_and_insert(all_prompts):
    """去重并插入数据库"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
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

        # 检查是否已存在
        c.execute('SELECT id FROM prompts WHERE prompt_hash = ?', (prompt_hash,))
        if c.fetchone():
            # 更新 last_seen
            c.execute(
                'UPDATE prompts SET last_seen = CURRENT_TIMESTAMP WHERE prompt_hash = ?',
                (prompt_hash,)
            )
            skipped += 1
            continue

        # 插入新记录
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
    """获取数据库统计"""
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
    return {
        'total': total,
        'by_category': by_category,
        'by_source': by_source
    }


def run_dedupe():
    """主函数"""
    print(f"[dedupe] Started at {datetime.now().isoformat()}")
    print("[dedupe] Loading raw prompts...")
    all_prompts = load_raw_prompts()

    print("[dedupe] Deduplicating and inserting...")
    inserted, skipped = dedupe_and_insert(all_prompts)

    stats = get_stats()
    print(f"[dedupe] Done. Inserted: {inserted}, Skipped (duplicate/empty): {skipped}")
    print(f"[dedupe] Total prompts in DB: {stats.get('total', 0)}")
    print(f"[dedupe] By category: {stats.get('by_category', {})}")
    print(f"[dedupe] By source: {stats.get('by_source', {})}")

    return stats


if __name__ == '__main__':
    run_dedupe()
