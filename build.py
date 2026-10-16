#!/usr/bin/env python3
"""Build a static AI-trends dashboard HTML from daily-ledger data files.
Zero-dependency (stdlib only). Output: out/index.html
Usage: python3 build.py [/path/to/daily-ledger]
"""
import json, glob, os, re, sys, html
from collections import Counter, defaultdict
from datetime import datetime

LEDGER = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/daily-ledger")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

STOP = set("""a an the and or of for in on to with via from into using based toward towards
agent agents model models learning language multi task tasks new open end-to-end general
study framework survey benchmark can how why what we our their its this that these those
is are be been was were it as at by not no than then when which who will would could should
have has had do does did more most other such only over under between without within
large small data training text vision cross self low high true real world human humans""".split())

def load_arxiv():
    days = []
    for f in sorted(glob.glob(os.path.join(LEDGER, "data/arxiv-raw-*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not d.get("papers"):
            continue
        days.append(d)
    return days

def load_gh():
    repos = Counter(); info = {}
    for f in sorted(glob.glob(os.path.join(LEDGER, "data/raw-*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for r in d.get("gh", []):
            name = r.get("slug") or r.get("repo") or r.get("full_name") or r.get("name")
            if not name:
                continue
            repos[name] += 1
            info[name] = r
    return repos, info

def sparkline_svg(points, w=520, h=80, color="#4f8ef7"):
    if len(points) < 2:
        return "<p>not enough data</p>"
    mx, mn = max(points), min(points)
    rng = (mx - mn) or 1
    step = w / (len(points) - 1)
    coords = [(i * step, h - 6 - (p - mn) / rng * (h - 16)) for i, p in enumerate(points)]
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
    area = path + f" L {w} {h} L 0 {h} Z"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{color}"/>' for x, y in coords)
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img">'
            f'<path d="{area}" fill="{color}" opacity="0.12"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>{dots}</svg>')

def main():
    arxiv = load_arxiv()
    counts = [(d["latest"] or d.get("date"), len(d["papers"])) for d in arxiv]
    counts.sort()

    # category aggregate
    cats = Counter()
    cat_by_day = defaultdict(dict)
    for d in arxiv:
        for c, n in d.get("cat_counts", {}).items():
            cats[c] += n
            cat_by_day[d["latest"]][c] = n

    # top terms in titles (bigram-leaning)
    uni = Counter(); bi = Counter()
    for d in arxiv:
        for p in d["papers"]:
            toks = [t for t in re.findall(r"[a-zA-Z]{3,}", p["title"].lower()) if t not in STOP]
            uni.update(toks)
            bi.update(zip(toks, toks[1:]))

    gh_repos, gh_info = load_gh()
    top_repos = gh_repos.most_common(15)

    days_labels = [c[0][5:] for c in counts]
    vals = [c[1] for c in counts]
    cat_rows = "".join(
        f"<tr><td><code>{html.escape(c)}</code></td><td>{n}</td></tr>"
        for c, n in cats.most_common(12))
    term_rows = "".join(
        f"<li>{html.escape(' '.join(t))} <span class='n'>×{n}</span></li>"
        for t, n in bi.most_common(18) if n >= 4)[:2000]
    repo_rows = "".join(
        f"<tr><td><code>{html.escape(r)}</code></td><td>{n}</td></tr>"
        for r, n in top_repos)

    doc = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Trends Dashboard · 自动生成</title>
<style>
body{{font-family:system-ui,-apple-system,'Noto Sans SC',sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222;background:#fafafa}}
h1{{font-size:1.5rem}} h2{{font-size:1.1rem;margin-top:2rem}}
.n{{color:#888;font-size:.85em}}
table{{border-collapse:collapse;width:100%}} td,th{{padding:.35rem .5rem;border-bottom:1px solid #eee;text-align:left}}
code{{background:#f0f0f0;padding:0 .3em;border-radius:3px;font-size:.9em}}
ol{{columns:2}} .meta{{color:#888;font-size:.85rem}}
</style></head><body>
<h1>AI Trends Dashboard</h1>
<p class="meta">数据源：daily-ledger 每日快照（arXiv cs.AI 等 / GitHub Trending）· 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · 纯静态、零依赖</p>

<h2>每日 AI 论文数量（arXiv，{len(counts)} 天）</h2>
{sparkline_svg(vals)}
<p class="meta">{days_labels[0]} → {days_labels[-1]}，峰值 {max(vals)} 篇（{days_labels[vals.index(max(vals))]}/{days_labels[vals.index(max(vals))]}），近 7 日均值 {sum(vals[-7:])/min(7,len(vals)):.1f} 篇</p>

<h2>热门主题（论文标题高频词对）</h2>
<ol>{term_rows}</ol>

<h2>分类分布（累计）</h2>
<table><tr><th>arXiv 分类</th><th>篇数</th></tr>{cat_rows}</table>

<h2>GitHub Trending 常客（近 4 周上榜次数）</h2>
<table><tr><th>仓库</th><th>上榜次数</th></tr>{repo_rows}</table>
</body></html>"""
    path = os.path.join(OUT, "index.html")
    open(path, "w").write(doc)
    print(f"OK wrote {path} ({len(doc)} bytes), {len(counts)} arxiv days, {len(gh_repos)} repos tracked")

if __name__ == "__main__":
    main()
