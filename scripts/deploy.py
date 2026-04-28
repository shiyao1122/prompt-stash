"""
Git 部署脚本 - 将 outputs/site/ 推送到 GitHub 触发 Cloudflare Pages
Token 从环境变量读取，不在代码中硬编码
"""
import os
import sys
import subprocess
from datetime import datetime


def get_env(key, default=''):
    return os.environ.get(key, default)


GITHUB_TOKEN = get_env('GITHUB_TOKEN')
GITHUB_REPO = get_env('GITHUB_REPO', 'shiyao1122/prompt-stash')
BRANCH = get_env('GITHUB_BRANCH', 'main')


def run_cmd(cmd, check=True):
    """执行 shell 命令"""
    print(f"[deploy] Running: {cmd[:80]}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.split('\n')[:5]:
            print(f"  {line}")
    if result.returncode != 0 and check:
        print(f"[deploy] Command failed: {result.stderr[:200]}")
        raise Exception(f"Command failed with code {result.returncode}")
    return result


def deploy():
    """主函数"""
    if not GITHUB_TOKEN:
        print("[deploy] ERROR: GITHUB_TOKEN not set in environment")
        print("[deploy] Set it with: set GITHUB_TOKEN=your_token")
        print("[deploy] Or add to .env file")
        sys.exit(1)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    site_dir = os.path.join(project_root, 'outputs', 'site')
    repo_dir = os.path.join(project_root, 'outputs', 'site-git')

    print(f"[deploy] Starting deploy at {datetime.now().isoformat()}")

    # Step 1: Clone the repo
    if os.path.exists(repo_dir):
        print("[deploy] Pulling latest from repo...")
        run_cmd(f'cd /d "{repo_dir}" && git pull origin {BRANCH}', check=False)
    else:
        print("[deploy] Cloning repo...")
        git_url = f'https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git'
        run_cmd(f'git clone --branch {BRANCH} --single-branch {git_url} "{repo_dir}"')

    # Step 2: Copy generated site files into the cloned repo
    import shutil
    for f in os.listdir(site_dir):
        src = os.path.join(site_dir, f)
        dst = os.path.join(repo_dir, f)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # Step 3: Git add / commit / push
    os.chdir(repo_dir)
    run_cmd('git config user.email "bot@promptstash.com"')
    run_cmd('git config user.name "PromptStash Bot"')
    run_cmd('git add -A')

    result = subprocess.run('git status --porcelain', shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        print("[deploy] No changes to commit, skipping push")
        return "No changes"

    run_cmd(f'git commit -m "Auto-deploy {datetime.now().strftime("%Y-%m-%d %H:%M")}"')
    run_cmd(f'git push origin {BRANCH}')

    print(f"[deploy] Deploy complete!")
    return "Deployed successfully"


if __name__ == '__main__':
    try:
        result = deploy()
        print(f"[deploy] Result: {result}")
    except Exception as e:
        print(f"[deploy] FAILED: {e}")
        sys.exit(1)
