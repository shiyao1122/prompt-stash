"""
自动化运行脚本 - Windows 定时任务入口
双击此文件 或 从 run.bat 调用
"""
import os
import sys
import json
from datetime import datetime

# 确保在正确目录运行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run_step(name, func):
    log(f"Step: {name}")
    try:
        result = func()
        log(f"Step OK: {name} — {result}")
    except Exception as e:
        log(f"Step FAILED: {name} — {e}")
        raise


def main():
    log("=== PromptStash Crawler Run Started ===")
    log(f"Working dir: {PROJECT_ROOT}")

    # Step 1: Crawl YouMind
    run_step("Crawl YouMind", lambda: (
        os.system(f'cd /d {PROJECT_ROOT} && python scripts/crawlers/youmind_crawler.py'),
        "youmind done"
    )[1])

    # Step 2: Crawl Reddit
    run_step("Crawl Reddit", lambda: (
        os.system(f'cd /d {PROJECT_ROOT} && python scripts/crawlers/reddit_crawler.py'),
        "reddit done"
    )[1])

    # Step 3: Dedupe
    run_step("Dedupe & Insert", lambda: (
        os.system(f'cd /d {PROJECT_ROOT} && python scripts/dedupe/dedupe.py'),
        "dedupe done"
    )[1])

    # Step 4: Generate static site
    run_step("Generate static site", lambda: (
        os.system(f'cd /d {PROJECT_ROOT} && python scripts/publisher/generate_site.py'),
        "site generated"
    )[1])

    # Step 5: Git commit & push
    run_step("Git deploy", lambda: (
        os.system(f'cd /d {PROJECT_ROOT} && python scripts/deploy.py'),
        "deployed"
    )[1])

    log("=== Run Complete ===")


if __name__ == '__main__':
    main()
