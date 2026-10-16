#!/usr/bin/env python3
"""Build publish-grade static AI-trends site from daily-ledger data.
Outputs to out/: index.html, daily/2026-10-15.html, rss.xml, sitemap.xml, CNAME.placeholder
Zero dependencies (stdlib only). Usage: python3 site.py [/path/to/daily-ledger]
"""
import json, glob, os, re, sys, html
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

LEDGER = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/daily-ledger")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
os.makedirs(os.path.join(OUT, "daily"), exist_ok=True)
NOW = datetime.now()

# --- config: fill in after deployment (approved) ---
SITE_URL = os.environ.get("SITE_URL", "")  # e.g. https://ttxs69.github.io/ai-trends
SITE_BASE = SITE_URL.rstrip("/") if SITE_URL else ""

STOP = set("""a an the and or of for in on to with via from into using based toward towards
agent agents model models learning language multi task tasks new open end-to-end general
study framework survey benchmark can how why what we our their its this that these those
is are be been was were it as at by not no than then when which who will would could should
have has had do does did more most other such only over under between without within
large small data training text vision cross self low high true real world human humans""".split())

def esc(s): return html.escape(str(s if s is not None else ""), quote=True)
def uesc(s): return esc(s).replace("'", "&#39;")

def load_days():
    raw, arx = {}, {}
    for f in glob.glob(os.path.join(LEDGER, "data/raw-*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if d.get("date"): raw[d["date"]] = d
    for f in glob.glob(os.path.join(LEDGER, "data/arxiv-raw-*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if d.get("date") and d.get("papers"): arx[d["date"]] = d
    return raw, arx

def summaries_for(date):
    f = os.path.join(LEDGER, f"data/arxiv-summaries-{date.replace('-','')}.json")
    if os.path.exists(f):
        try: return json.load(open(f))
        except Exception: pass
    return None

def cat_name(c):
    m = {"cs.AI": "人工智能", "cs.CL": "计算语言学", "cs.LG": "机器学习", "cs.RO": "机器人",
         "cs.CV": "计算机视觉", "cs.MA": "多智能体系统", "cs.HC": "人机交互", "cs.CR": "安全密码学",
         "cs.SE": "软件工程", "cs.NI": "网络", "stat.ML": "统计学习", "eess.SY": "系统控制"}
    return m.get(c, c)

STYLE = """
body{font-family:system-ui,-apple-system,'Noto Sans SC',sans-serif;max-width:780px;margin:2rem auto;padding:0 1rem;color:#222;background:#fafafa}
h1{font-size:1.45rem} h2{font-size:1.12rem;margin-top:2.2rem} h3{font-size:1rem}
a{color:#2563eb;text-decoration:none} a:hover{text-decoration:underline}
.meta{color:#888;font-size:.85rem} .n{color:#888;font-size:.85em}
table{border-collapse:collapse;width:100%} td,th{padding:.35rem .5rem;border-bottom:1px solid #eee;text-align:left;vertical-align:top}
code{background:#f0f0f0;padding:0 .3em;border-radius:3px;font-size:.88em}
ol{padding-left:1.2rem} .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:.8rem}
.card{border:1px solid #e5e5e5;border-radius:8px;padding:.8rem;background:#fff}
.card h3{margin:.1rem 0 .3rem} .card p{margin:.2rem 0;font-size:.88rem;color:#444}
.tag{display:inline-block;font-size:.72rem;background:#eef2ff;color:#3730a3;border-radius:4px;padding:.05rem .35rem;margin-right:.25rem}
.spark{width:100%;height:auto}
footer{margin-top:3rem;border-top:1px solid #eee;padding-top:.8rem;color:#999;font-size:.8rem}
"""

def sparkline_svg(points, labels, w=720, h=90, color="#4f8ef7", link_base=None):
    if len(points) < 2: return "<p class='meta'>not enough data</p>"
    mx, mn = max(points), min(points); rng = (mx - mn) or 1
    step = w / (len(points) - 1)
    coords = [(i * step, h - 8 - (p - mn) / rng * (h - 22)) for i, p in enumerate(points)]
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
    dots = []
    for i, (x, y) in enumerate(coords):
        d = labels[i]
        inner = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>'
        dots.append(f'<a href="{link_base}{d}.xhtml"' if False else inner)
    area = path + f" L {w} {h} L 0 {h} Z"
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img">'
            f'<path d="{area}" fill="{color}" opacity="0.12"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>' + "".join(dots) + "</svg>")

def gh_repo_url(slug): return f"https://github.com/{slug}"
def arxiv_url(pid): return f"https://arxiv.org/abs/{pid.split('v')[0]}"

def build_daily_page(date, raw, arx, summ):
    d = date.replace("-", "/")
    gh = raw.get("gh", [])[:12]
    hf = raw.get("hf", [])[:6]
    gh_rows = "".join(
        f"<tr><td><a href='{uesc(gh_repo_url(r['slug']))}' rel='noopener'>{esc(r['slug'])}</a></td>"
        f"<td>{esc(r.get('lang') or '')}</td><td style='text-align:right'>+{r.get('stars_today',0):,}</td></tr>"
        for r in gh)
    hf_cards = "".join(
        f"<div class='card'><h3><a href='https://huggingface.co/{uesc(r['repo'])}' rel='noopener'>{esc(r['repo'])}</a></h3>"
        f"<p><span class='tag'>{esc(r.get('tag',''))}</span></p>"
        f"<p>⬇ {esc(r.get('downloads_fmt','?'))} · ❤ {r.get('likes',0):,}</p></div>"
        for r in hf)
    # pick up to 6 notable papers: summaries pN maps 1:1 BY INDEX to raw papers
    # (verified 20261013/20261015: p1|id|title order == papers list order)
    papers = arx.get("papers", [])
    picked = []  # (paper, chinese_one_liner)
    if summ:
        for k in ["p1", "p2", "p3", "p4", "p5", "p6"]:
            line = summ.get(k)
            if line is None: break
            i = int(k[1:]) - 1
            if 0 <= i < len(papers): picked.append((papers[i], str(line)))
    if len(picked) < 3:
        have = {p["id"].split("v")[0] for p, _ in picked}
        picked += [(p, "") for p in papers if p["id"].split("v")[0] not in have][:6 - len(picked)]
    paper_cards = "".join(
        f"<div class='card'><h3><a href='{arxiv_url(p['id'])}' rel='noopener'>{esc(p['title'])}</a></h3>"
        f"<p class='meta'>{esc(p.get('primary',''))} · {esc(p.get('date',''))} · {', '.join(p.get('authors',[])[:3])}{' et al.' if len(p.get('authors',[]))>3 else ''}</p>"
        + (f"<p><b>{esc(cn)}</b></p>" if cn else "")
        + f"<p>{esc(p['abstract'][:180])}…</p></div>"
        for p, cn in picked)
    top_line = esc((summ or {}).get("top", f"今日 {len(papers)} 篇 AI 论文。"))
    nav_prev = f"{SITE_BASE}/daily/{prev_day(date)}.xhtml" if False else f"{prev_day(date)}.xhtml"
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 日报 · {date} | AI Trends Radar</title>
<meta name="description" content="{top_line}">
<style>{STYLE}</style></head><body>
<h1>AI 日报 · {date}</h1>
<p class="meta">{top_line} · <a href="index.xhtml">« 返回总览</a></p>
<h2>今日精选论文（arXiv）</h2>
<div class="cards">{paper_cards}</div>
<h2>GitHub Trending TOP</h2>
<table><tr><th>仓库</th><th>语言</th><th style="text-align:right">今日星</th></tr>{gh_rows}</table>
<h2>Hugging Face 热门模型</h2>
<div class="cards">{hf_cards}</div>
<footer>数据：自动每日快照 · 自动生成，持续更新 · <a href="index.xhtml">AI Trends Radar</a></footer>
</body></html>"""

def prev_day(date):
    y, m, dd = map(int, date.split("-"))
    t = datetime(y, m, dd) - timedelta(days=1)
    return t.strftime("%Y-%m-%d")

def build_index(days, raw, arx):
    counts = sorted((d, len(a["papers"])) for d, a in arx.items())
    labels = [c[0] for c in counts]; vals = [c[1] for c in counts]
    cats = Counter()
    for a in arx.values():
        for c, n in a.get("cat_counts", {}).items(): cats[c] += n
    uni = Counter(); bi = Counter()
    for a in arx.values():
        for p in a["papers"]:
            toks = [t for t in re.findall(r"[a-zA-Z]{3,}", p["title"].lower()) if t not in STOP]
            uni.update(toks); bi.update(zip(toks, toks[1:]))
    gh = Counter()
    for r in raw.values():
        for x in r.get("gh", []):
            if x.get("slug"): gh[x["slug"]] += 1
    # recent 5 daily links + weekly links
    recent = sorted(raw.keys())[-5:][::-1]
    recent_links = "".join(f"<li><a href='daily/{d}.xhtml'>{d} 日报</a></li>" for d in recent)
    weekly_links = "".join(
        f"<li><a href='weekly/{y}-W{w:02d}.xhtml'>{y} 年第 {w} 周</a></li>"
        for y, w in WEEKS)
    term_rows = "".join(
        f"<li>{esc(' '.join(t))} <span class='n'>×{n}</span></li>"
        for t, n in bi.most_common(18) if n >= 4)
    cat_rows = "".join(
        f"<tr><td><code>{esc(c)}</code> {esc(cat_name(c))}</td><td style='text-align:right'>{n}</td></tr>"
        for c, n in cats.most_common(10))
    repo_rows = "".join(
        f"<tr><td><a href='{uesc(gh_repo_url(r))}' rel='noopener'>{esc(r)}</a></td><td style='text-align:right'>{n} 次</td></tr>"
        for r, n in gh.most_common(12))
    days_str = labels[0].replace("-", "/") + "/" + labels[-1].replace("-", "/")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Trends Radar · arXiv × GitHub 每日趋势雷达</title>
<meta name="description" content="每日自动追踪 arXiv AI 论文趋势与 GitHub Trending：论文量、热门主题、分类分布、开源项目热度。数据驱动，持续更新。">
<style>{STYLE}</style></head><body>
<h1>AI Trends Radar</h1>
<p class="meta">arXiv × GitHub 每日趋势雷达 · 覆盖 {days_str} · 生成于 {NOW.strftime('%Y-%m-%d %H:%M')} UTC+8 · 纯静态零依赖</p>
<h2>近期日报</h2><ol>{recent_links}</ol>
<h2>趋势周报</h2><ol>{weekly_links}</ol>
<h2>每日 AI 论文数量（arXiv，{len(counts)} 天）</h2>
{sparkline_svg(vals, labels)}
<p class="meta">{labels[0]} → {labels[-1]}，峰值 {max(vals)} 篇，近 7 日均值 {sum(vals[-7:])/min(7,len(vals)):.1f} 篇</p>
<h2>热门主题（标题高频词对）</h2><ol style="columns:2">{term_rows}</ol>
<h2>分类分布（累计）</h2><table><tr><th>分类</th><th style="text-align:right">篇数</th></tr>{cat_rows}</table>
<h2>GitHub Trending 常客（4 周上榜次数）</h2><table><tr><th>仓库</th><th style="text-align:right">上榜</th></tr>{repo_rows}</table>
<footer>由 <a href="https://github.com/ttxs69" rel="noopener">ttxs69</a> 自动生成 · 数据仅供研究 · 每日更新</footer>
</body></html>"""

def build_rss(days_desc):
    items = []
    for d in days_desc[:10]:
        a = arx.get(d, {}); r = raw.get(d, {})
        n = len(a.get("papers", []))
        summ = summaries_for(d)
        top = (summ or {}).get("top", f"{n} papers")
        link = f"{SITE_BASE}/daily/{d}.xhtml" if SITE_BASE else f"/daily/{d}.xhtml"
        items.append(f"""<item><title>AI 日报 {d}</title><link>{link}</link>
<guid isPermaLink="false">ai-trends-{d}</guid>
<pubDate>{rfc822(d)}</pubDate><description>{esc(top)} · GitHub TOP: {esc(', '.join(x['slug'] for x in r.get('gh',[])[:3]))}</description></item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>AI Trends Radar</title>
<link>{SITE_BASE}/index.xhtml</link>
<description>每日 arXiv × GitHub AI 趋势</description>
<language>zh-cn</language><lastBuildDate>{NOW.strftime('%a, %d %b %Y %H:%M:%S +0800')}</lastBuildDate>
{"".join(items)}</channel></rss>"""

def rfc822(date):
    y, m, dd = map(int, date.split("-"))
    return datetime(y, m, dd, 9, 37, tzinfo=timezone(timedelta(hours=8))).strftime("%a, %d %b %Y %H:%M:%S +0800")

def build_sitemap(pages):
    urls = "".join(
        f"<url><loc>{SITE_BASE}/{p}</loc><lastmod>{NOW.strftime('%Y-%m-%d')}</lastmod></url>"
        for p in pages)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'

if __name__ == "__main__":
    raw, arx = load_days()
    all_days = sorted(set(list(arx.keys()) + list(raw.keys())))
    from datetime import datetime as _dt
    WEEKS = sorted({(_dt.strptime(d, "%Y-%m-%d").isocalendar()[0],
                     _dt.strptime(d, "%Y-%m-%d").isocalendar()[1]) for d in all_days})[-6:][::-1]
    pages = ["index.xhtml"]
    for d in sorted(raw.keys()):
        if d in arx or raw[d].get("gh"):
            page = build_daily_page(d, raw[d], arx.get(d, {}), summaries_for(d))
            with open(os.path.join(OUT, "daily", d + ".xhtml"), "w") as f:
                f.write(page)
            pages.append(f"daily/{d}.xhtml")
    pages += [f"weekly/{y}-W{w:02d}.xhtml" for y, w in WEEKS]
    with open(os.path.join(OUT, "index.xhtml"), "w") as f:
        f.write(build_index(sorted(arx.keys()), raw, arx))
    with open(os.path.join(OUT, "rss.xml"), "w") as f:
        f.write(build_rss(sorted(raw.keys())[::-1]))
    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write(build_sitemap(pages))
    print(f"OK: {len(pages)} pages -> {OUT} (index + {len(pages)-1} daily), rss.xml, sitemap.xml")
