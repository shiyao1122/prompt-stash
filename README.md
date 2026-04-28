# PromptStash

A curated collection of GPT Image prompts — SEO-driven prompt aggregator.

## Project Overview

- **Focus**: GPT Image prompts aggregation
- **Strategy**: SEO流量聚合，内容来自爬虫自动采集
- **Deployment**: Cloudflare Pages (static)
- **Crawler**: 本地 Windows 运行，定时自动采集更新

## Tech Stack

- **页面**: 纯静态 HTML (无服务端渲染)
- **爬虫**: Python 3.7+ (requests, BeautifulSoup)
- **数据库**: SQLite (本地存储)
- **部署**: GitHub → Cloudflare Pages

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/shiyao1122/prompt-stash.git
cd prompt-stash

# 2. 安装依赖
pip install -r requirements.txt

# 3. 手动运行采集
scripts\run.bat

# 4. 本地预览生成的静态页面
# 直接用浏览器打开 outputs/site/index.html
```

## Directory Structure

```
prompt-stash/
├── scripts/
│   ├── crawlers/          # 爬虫模块
│   ├── dedupe/            # 去重模块
│   ├── publisher/         # 静态页生成器
│   ├── deploy.py          # Git push 触发 Pages 构建
│   └── run.bat            # Windows 定时任务入口
├── config/
│   ├── sources.json       # 爬虫来源配置
│   └── site.json          # 站点 meta 配置
├── templates/             # HTML 模板
├── data/                  # SQLite 数据库
├── outputs/site/          # 生成的静态文件（推送到 GitHub）
└── .github/workflows/      # GitHub Actions
```

## Auto-Update Flow

```
Windows Task Scheduler (每6小时)
  → run.bat
  → crawlers (youmind + reddit)
  → dedupe (去重入库)
  → generate_site.py (生成静态 HTML)
  → deploy.py (git push)
  → Cloudflare Pages 自动构建部署
```

## Notes

- Python 3.7.7 兼容
- 所有依赖纯标准库+轻量库，无重型依赖
- 站点样式参考 HitPaw OneClaw 设计风格
