import re
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = r"c:\Users\admin\dilkush007\_e2e_probe2.txt"


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


out = []
st, final, hb = fetch("https://www.pinterest.com/strndsehsules974/ai-vide-ai/")
out.append(f"BOARD status={st} len={len(hb)}")

string_ids = re.findall(r'"id"\s*:\s*"(\d{10,})"', hb)
out.append(f'string-id matches ({len(string_ids)}): {string_ids}')

pins_url = re.findall(r"/pin/(\d{10,})/", hb)
uniq = list(dict.fromkeys(pins_url))
out.append(f"/pin/ URLs total={len(pins_url)} unique={uniq[:10]}")

for m in re.finditer(r'"id"\s*:\s*"(\d{10,})"', hb):
    s = max(0, m.start() - 90)
    ctx = hb[s:m.end() + 90].replace("\n", " ")
    out.append(f"CTX {m.group(1)}: ...{ctx}...")

imgs = re.findall(r"https://s\.pinimg\.com/[^\"']+?\.(?:jpg|jpeg|png)", hb)
out.append(f"board pinimg images first5: {list(dict.fromkeys(imgs))[:5]}")

st2, final2, ph = fetch("https://www.pinterest.com/pin/1147573617491110899/")
out.append(f"PINPAGE status={st2} len={len(ph)}")
orig = re.findall(r"https://i\.pinimg\.com/originals/[^\"']+", ph)
out.append(f"pinpage originals first3: {list(dict.fromkeys(orig))[:3]}")
media = re.findall(r"https://[a-z.]*pinimg\.com/[^\"']+?\.(?:jpg|jpeg|png|mp4)", ph)
out.append(f"pinpage pinimg media first8: {list(dict.fromkeys(media))[:8]}")
t = re.search(r"<title>([^<]*)</title>", ph, re.I)
out.append(f"pinpage title: {t.group(1) if t else None}")
head = ph[:600].replace("\n", " ")
out.append(f"pinpage head: {head}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(str(x) for x in out))
print("PROBE2 DONE")
