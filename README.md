# Daily Paper Scraper

Daily research paper tracker with arXiv + HuggingFace scraping, Notion sync, Chinese AI summaries, and a HuggingFace-style web viewer.

**Live Site**: https://daily-paper-scraper-inky.vercel.app

## Features

- **Auto scraping**: Daily fetch from arXiv (by category + keywords) and HuggingFace Daily Papers
- **Smart filtering**: Keyword matching + AI semantic filtering across 3 research lines
- **Chinese summaries**: AI-generated structured summaries (title, contribution, method, results)
- **Notion sync**: Papers with metadata, research line tags, evolution notes, follow/favorite
- **Web viewer**: HuggingFace-style card layout with live Notion data and interactive buttons
- **Evolution tracking**: "Builds On" relation links + evolution notes showing paper lineage
- **Scheduled**: Remote Trigger runs daily at 08:00 Beijing time

## Research Lines

| Line | Focus |
|------|-------|
| 🧬 Body Models | SMPL, SMPL-X, parametric body, neural implicit bodies |
| 👁️ HPE→Mesh | Human pose estimation, 3D mesh recovery from images |
| ⚡ Motion-Physics | Motion generation, physics-based character animation, diffusion policy |

## Architecture

```
Remote Trigger (daily 08:00 CST)
  → arXiv API + HF API → keyword filter → semantic filter
  → AI generates Chinese summaries + research line classification
  → Notion Database (structured knowledge base)
  → Rebuild static site → git push → Vercel auto-deploy
```

## Setup

```bash
# Install
pip install -e .

# Set credentials
cp .env.example .env
# Edit .env with your NOTION_TOKEN and NOTION_DATABASE_ID

# Daily fetch
python scripts/fetch_and_filter.py --output papers.json

# Sync to Notion
python scripts/bulk_sync.py papers.json

# Local web viewer
python web/app.py  # http://localhost:5555

# Build static site
python scripts/build_site.py  # outputs docs/index.html
```

## Scripts

| Script | Purpose |
|--------|---------|
| `fetch_and_filter.py` | Fetch papers from arXiv/HF, filter by keywords |
| `bulk_sync.py` | Sync papers to Notion database |
| `build_site.py` | Generate static HTML from Notion data |
| `seed_seminal.py` | Seed landmark papers with evolution chains |
| `create_roadmap_page.py` | Create research evolution roadmap in Notion |
| `setup_notion_db.py` | One-time database schema creation |

---

# 每日论文抓取器

自动追踪 arXiv + HuggingFace 论文，同步到 Notion，生成中文智能摘要，提供 HuggingFace 风格的 Web 浏览器。

**在线地址**: https://daily-paper-scraper-inky.vercel.app

## 功能

- **自动抓取**: 每日从 arXiv（按分类+关键词）和 HuggingFace Daily Papers 抓取
- **智能过滤**: 关键词匹配 + AI 语义过滤，聚焦三条研究线
- **中文摘要**: AI 生成结构化摘要（标题、贡献、方法、结果）
- **Notion 同步**: 论文元数据、研究线标签、演化笔记、关注/收藏
- **Web 浏览器**: HuggingFace 风格卡片布局，实时 Notion 数据，可交互按钮
- **演化追踪**: "Builds On" 关系链接 + 演化笔记展示论文传承
- **定时运行**: Remote Trigger 每天北京时间 08:00 自动运行

## 研究线

| 研究线 | 方向 |
|--------|------|
| 🧬 Body Models | SMPL/SMPL-X、参数化人体模型、神经隐式人体表示 |
| 👁️ HPE→Mesh | 人体姿态估计、从图像恢复3D人体网格 |
| ⚡ Motion-Physics | 运动生成、物理仿真角色动画、扩散策略 |

## 架构

```
AI 定时触发器 (每天 08:00 北京时间)
  → arXiv API + HF API → 关键词过滤 → 语义过滤
  → AI 生成中文摘要 + 研究线分类
  → Notion 数据库 (结构化知识库)
  → 重建静态网站 → git push → Vercel 自动部署
```
