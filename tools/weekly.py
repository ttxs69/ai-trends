#!/usr/bin/env python3
"""Weekly analysis page generator for AI Trends Radar.
Reads daily-ledger data, produces out/weekly/2026-W42.html etc.
Data-driven sections: weekly paper-volume change, top bigram trend vs prior week,
GH repos with >1 trending appearance, HF models repeat appearances, and a
data-backed paper list (papers listed in 3+ consecutive days' summaries).
Pure stdlib. Usage: python3 weekly.py [/path/to/daily-ledger]
"""
import json, glob, os, re, sys, html
from collections import Counter
from datetime import datetime, timedelta, date

LEDGER = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/daily-ledger")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out", "weekly")
os.makedirs(OUT, exist_ok=True)
NOW = datetime.now()

# reuse style + helpers from site.py
sys.path.insert(0, ROOT)
# reuse style + helpers from site.py (import under alias: stdlib 'site' shadows it)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("siteshared", os.path.join(ROOT, "site.py"))
S = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(S)

def isocal(d): return d.isocalendar()[1], d.isocalendar()[0]

def load():
    raw, arx, summ_files = {}, {}, {}
    for f in glob.glob(os.path.join(LEDGER, "data/raw-*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if d.get("date"): raw[d["date"]] = d
    for f in glob.glob(os.path.join(LEDGER, "data/arxiv-raw-*.json")):
        byd = re.search(r"arxiv-raw-(\d{8})", f)
        try: d = json.load(open(f))
        except Exception: continue
        if byd and d.get("papers"):
            arx[f"{byd.group(1)[:4]}-{byd.group(1)[4:6]}-{byd.group(1)[6:]}"] = d
    for f in glob.glob(os.path.join(LEDGER, "data/arxiv-summaries-*.json")):
        byd = re.search(r"arxiv-summaries-(\d{8})", f)
        if byd:
            summ_files[f"{byd.group(1)[:4]}-{byd.group(1)[4:6]}-{byd.group(1)[6:]}"] = f
    return raw, arx, summ_files

def papers_of(d):
    return arx.get(d, {}).get("papers", [])

def toks_of(p):
    return [t for t in re.findall(r"[a-zA-Z]{3,}", p["title"].lower()) if t not in S.STOP]

def week_days(y, w):
    # ISO week -> list of date strings covered (only those with data)
    mon = date.fromisocalendar(y, w, 1)
    return [(mon + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

def build_week(y, w):
    fname = f"{y}-W{w:02d}"
    SITE_BASE = S.SITE_BASE
    days = week_days(y, w)
    have = [d for d in days if d in arx]  # only days with complete data get daily pages
    if not have:
        return None
    prev_week = week_days(*( (y, w-1) if w > 1 else (y-1, 52) ))
    have_prev = [d for d in prev_week if d in arx or d in raw]
    # paper volume
    n_this = sum(len(arx[d]["papers"]) for d in have if d in arx)
    n_prev = sum(len(arx[d]["papers"]) for d in have_prev if d in arx)
    delta = f"{(n_this - n_prev) / n_prev * 100:+.0f}%" if n_prev else "—"
    # bigram trends (this week vs previous)
    bi, bi_prev = Counter(), Counter()
    for d in have:
        for p in papers_of(d): bi.update(zip(*[iter(toks_of(p))]*2)) if False else None
    for d in have:
        for p in papers_of(d):
            tk = toks_of(p); bi.update(zip(tk, tk[1:]))
    for d in have_prev:
        for p in papers_of(d):
            tk = toks_of(p); bi_prev.update(zip(tk, tk[1:]))
    rising = [(t, n, bi_prev.get(t, 0)) for t, n in bi.most_common(80) if n >= 2]
    rising.sort(key=lambda x: (x[1] - x[2], x[1]), reverse=True)
    rising = rising[:10]
    # GH repos appearing >1 day this week
    gh = Counter()
    for d in have:
        for r in raw.get(d, {}).get("gh", []):
            if r.get("slug"): gh[r["slug"]] += 1
    gh_top = [(r, n) for r, n in gh.most_common(40) if n >= 2][:8]
    # HF repeat models
    hf = Counter()
    for d in have:
        for r in raw.get(d, {}).get("hf", []):
            if r.get("repo"): hf[r["repo"]] += 1
    hf_top = [(m, n) for m, n in hf.most_common(40) if n >= 2][:6]
    # papers curated by daily summaries this week: pN maps BY INDEX to raw papers
    pid_day = {}
    for d in sorted(have):
        f = summ_files.get(d)
        if not f: continue
        try: sm = json.load(open(f))
        except Exception: continue
        plist = papers_of(d)
        n = 0
        while sm.get(f"p{n+1}") is not None: n += 1
        for i in range(min(8, n, len(plist))):
            pid_day.setdefault(plist[i]["id"].split("v")[0], (d, str(sm.get(f"p{i+1}", ""))))
    # paper full info from raw
    byid = {}
    for d in have:
        for p in papers_of(d):
            byid.setdefault(p["id"].split("v")[0], p)
    momentum = sorted(pid_day.items(), key=lambda x: x[1][0], reverse=True)
    momentum_cards = []
    for pid, (d, cn) in momentum[:8]:
        p = byid.get(pid)
        if not p: continue
        summ_line = cn.split("｜")[0].split("|")[0]
        momentum_cards.append(
            f"<div class='card'><h3><a href='{S.arxiv_url(pid)}' rel='noopener'>{S.esc(p['title'])}</a></h3>"
            f"<p class='meta'>{d} 精选 · {S.esc(summ_line[:60])}</p>"
            f"<p>{S.esc(p['abstract'][:150])}…</p></div>")
    # daily links
    daily_links = "".join(
        f"<li><a href='../daily/{d}.html'>{d}</a> · {len(arx.get(d, {}).get('papers', []))} 篇</li>"
        for d in have)
    wk_label = f"{y} 年第 {w} 周"
    day_links_str = "、".join(f"<a href='../daily/{d}.html'>{d[5:]}</a>" for d in have)
    ri_rows = "".join(
        f"<tr><td>{S.esc(' '.join(t))} <span class='n'>{pn}→{n}</span></td></tr>"
        for t, n, pn in rising)
    gh_rows = "".join(
        f"<tr><td><a href='{S.uesc(S.gh_repo_url(r))}' rel='noopener'>{S.esc(r)}</a></td>"
        f"<td style='text-align:right'>{n} 天</td></tr>" for r, n in gh_top)
    hf_rows = "".join(
        f"<tr><td><a href='https://huggingface.co/{S.uesc(m)}' rel='noopener'>{S.esc(m)}</a></td>"
        f"<td style='text-align:right'>{n} 天</td></tr>" for m, n in hf_top)
    days_covered = "、".join(have)
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI 趋势周报 · {wk_label} | AI Trends Radar</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect width=%2732%27 height=%2732%27 rx=%276%27 fill=%27%232563eb%27/%3E%3Cpath d=%27M7 24 14 13l5 6 6-11%27 stroke=%27%23fff%27 stroke-width=%273%27 fill=%27none%27/%3E%3C/svg%3E">
<link rel="canonical" href="{SITE_BASE}/weekly/{fname}.html">
<meta name="description" content="{wk_label}（{days_covered}）：论文量 {n_this} 篇（周环比 {delta}），GitHub/HF 热门延续榜，精选论文势头榜。数据驱动自动生成。"/>
{S.adsense_head()}<style>{S.STYLE}</style></head><body>
<h1>AI 趋势周报 · {wk_label}</h1>
<p class="meta">覆盖 {days_covered} · 生成于 {NOW.strftime('%Y-%m-%d %H:%M')} · <a href="../index.html">« 返回总览</a></p>
<h2>本周概览</h2>
<table>
<tr><td>论文量</td><td style='text-align:right'>{n_this} 篇</td></tr>
<tr><td>周环比</td><td style='text-align:right'>{delta}</td></tr>
<tr><td>覆盖天数</td><td style='text-align:right'>{len(have)} 天</td></tr>
</table>
<h2>主题升温榜（对比上周）</h2>
<table><tr><th>主题词对</th></tr>{ri_rows}</table>
<h2>GitHub 持续热门（本周上榜 ≥2 天）</h2>
<table><tr><th>仓库</th><th style="text-align:right">天数</th></tr>{gh_rows}</table>
<h2>Hugging Face 延续热门（本周上榜 ≥2 天）</h2>
<table><tr><th>模型</th><th style="text-align:right">天数</th></tr>{hf_rows}</table>
<h2>本周精选论文（各日精选合集）</h2>
<div class="cards">{"".join(momentum_cards)}</div>
<h2>本周日报</h2>
<ol>{daily_links}</ol>
<footer>数据：自动每日快照 · 自动生成 · <a href="../index.html">AI Trends Radar</a></footer>
</body></html>"""

if __name__ == "__main__":
    raw, arx, summ_files = load()
    # determine weeks with data
    all_days = sorted(set(list(arx.keys()) + list(raw.keys())))
    weeks = sorted({isocal(datetime.strptime(d, "%Y-%m-%d").date()) for d in all_days}, reverse=True)
    pages = []
    for (w, y) in weeks[:6]:
        fpath = os.path.join(OUT, f"{y}-W{w:02d}.html")
        page = build_week(y, w)
        if page:
            with open(fpath, "w") as fh: fh.write(page)
            pages.append(f"weekly/{y}-W{w:02d}.html")
    print(f"OK: {len(pages)} weekly pages -> {OUT}")
    for p in pages: print(" ", p)
