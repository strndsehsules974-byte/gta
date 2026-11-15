import re
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = r"c:\Users\admin\dilkush007\_e2e_probe.txt"


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


out = []
for pid in ["1147573617491110899", "1147573617491108562", "1147573686208243203"]:
    url = f"https://www.pinterest.com/pin/{pid}/"
    try:
        st, final, html = fetch(url)
        out.append(f"PIN {pid} status={st} final={final} len={len(html)}")
        t = re.search(r"<title>([^<]*)</title>", html, re.I)
        title = t.group(1) if t else None
        out.append(f"  title: {title}")
        for key in ("og:image", "og:video", "og:video:secure_url", "og:title"):
            m1 = re.findall(
                rf"<meta[^>]+(?:property|name)=[\"']{re.escape(key)}[\"']"
                rf"[^>]+content=[\"']([^\"']+)[\"']", html, re.I)
            m2 = re.findall(
                rf"<meta[^>]+content=[\"']([^\"']+)[\"']"
                rf"[^>]+(?:property|name)=[\"']{re.escape(key)}[\"']", html, re.I)
            out.append(f"  {key}: prop-first={m1[:3]} content-first={m2[:3]}")
        # agent's exact video regex
        agent_video = None
        for meta_name in ("og:video:secure_url", "og:video", "twitter:player"):
            m = re.search(
                rf"<meta[^>]+(?:property|name)=['\"]{re.escape(meta_name)}['\"]"
                rf"[^>]+content=['\"]([^'\"]+)['\"]", html, re.I)
            if m:
                agent_video = m.group(1)
                break
        out.append(f"  AGENT video regex -> {agent_video}")
        mp4 = re.search(r"https?://[^\"'\s<>]+\.(?:mp4|m3u8)(?:\?[^\"'\s<>]*)?",
                        html, re.I)
        out.append(f"  first mp4/m3u8 in html -> {mp4.group(0) if mp4 else None}")
        out.append(f"  'Log in to see more' present: {'Log in to see more' in html}")
        out.append(f"  'Log in' in title: {'log in' in (title or '').lower()}")
    except Exception as exc:  # noqa: BLE001
        out.append(f"PIN {pid} FAILED: {type(exc).__name__}: {exc}")

try:
    st, final, hb = fetch("https://www.pinterest.com/strndsehsules974/ai-vide-ai/")
    out.append(f"=== BOARD status={st} len={len(hb)} ===")
    m = re.search(r".{100}\"id\"\s*:\s*\"1147573617491108562\".{250}", hb, re.S)
    out.append("CONTEXT: " + (m.group(0) if m else "NO CONTEXT MATCH"))
    vids = re.findall(r"https?://[^\"'\s<>]+\.(?:mp4|m3u8)(?:\?[^\"'\s<>]*)?",
                      hb, re.I)
    out.append(f"board mp4/m3u8 urls (first 5): {vids[:5]}")
except Exception as exc:  # noqa: BLE001
    out.append(f"BOARD FAILED: {type(exc).__name__}: {exc}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(str(x) for x in out))
print("PROBE DONE")
