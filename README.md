# AI Trends Radar

每日 AI 趋势雷达：arXiv（cs.AI 等）/ GitHub Trending / Hugging Face 热门模型的自动聚合静态站点。

- 纯静态、零依赖（Python stdlib 生成）
- 每日一页精选论文卡片 + GitHub/HF 榜单
- 每周自动趋势周报（主题升温榜、精选合集）
- RSS: `/rss.xml` · Sitemap: `/sitemap.xml`

## 构建

```bash
python3 site.py  [path/to/data]      # 数据目录需含 raw-YYYYMMDD.json / arxiv-raw-*.json
python3 weekly.py [path/to/data]     # 周报页
```

构建产物在 `out/`，由 GitHub Pages 直接发布。

数据为公开信息（arXiv / GitHub Trending / Hugging Face）的每日自动快照衍生。
