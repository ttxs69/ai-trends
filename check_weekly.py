import re, glob, os
h = open('out/weekly/2026-W42.xhtml').read()
print('size', len(h))
print('sections:', [s for s in ['主题升温榜','GitHub 持续热门','Hugging Face 延续热门','本周精选论文','本周日报'] if s in h])
print('momentum cards:', h.count("class='card'"))
print('rising rows:', len(re.findall(r'<span class=.n.>\d+→\d+</span>', h)))
m = re.search(r"class='card'><h3><a href='(https://arxiv.org/abs/[0-9.]+)'[^>]*>(.{10,90})</a>", h)
print('sample paper:', (m.group(1), m.group(2)[:70]) if m else None)
rows = re.findall(r'<tr><td>([^<]{3,60})<span class=.n.>(\d+→\d+)</span>', h)
print('rising list:', rows[:6])
for f in sorted(glob.glob('out/weekly/*.xhtml')):
    c = open(f).read()
    assert '<html lang="zh">' in c and '</html>' in c, f
    for l in re.findall(r"href='\.\./daily/([^']+)'", c):
        assert os.path.exists('out/daily/' + l), (f, l)
print('all weekly files: links valid, structure ok')
