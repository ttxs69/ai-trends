#!/usr/bin/env python3
"""IndexNow 提交：将全部 URL 推给 IndexNow API（Bing/Yandex 等共用）。
前提：站点根有 <KEY>.txt。用法：SITE_URL=... python3 indexnow.py [--key XXXX]
"""
import json, os, re, sys, urllib.request, secrets

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("SITE_URL", "https://ttxs69.github.io/ai-trends").rstrip("/")
KEYFILE_ENV = os.environ.get("INDEXNOW_KEY", "")

def load_key():
    if KEYFILE_ENV: return KEYFILE_ENV
    # 从站点构建目录找已有 key 文件
    import glob
    for f in glob.glob(os.path.join(ROOT, "out", "*.txt")):
        base = os.path.basename(f)[:-4]
        content = open(f).read().strip()
        if base == content and len(content) in (8, 64) or (base == content and 16 <= len(content) <= 128):
            return content
    return None

def gen_key():
    k = secrets.token_hex(16)
    with open(os.path.join(ROOT, "out", f"{k}.txt"), "w") as f:
        f.write(k)
    return k

def urls_from_sitemap():
    sm = open(os.path.join(ROOT, "out", "sitemap.xml")).read()
    return re.findall(r"<loc>([^<]+)</loc>", sm)

def main():
    key = load_key() or gen_key()
    print("key:", key[:4] + "..." )
    urls = urls_from_sitemap()
    print("submitting", len(urls), "urls")
    body = json.dumps({"host": "ttxs69.github.io", "key": key, "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print("API status:", r.status, "(200=ok, 202=accepted)")
    except urllib.error.HTTPError as e:
        print("API status:", e.code, e.read()[:200])
        sys.exit(1)

if __name__ == "__main__":
    main()
