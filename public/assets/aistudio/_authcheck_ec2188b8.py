"""Boolean-only auth check. Prints NO cookies/credentials/passwords."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

profile = Path(os.environ.get("LOCALAPPDATA", "")) / "Wallix" / "PinterestAgent" / "browser-profile"
lock = profile / ".wallix-browser.lock"
OUT = r"c:\Users\admin\dilkush007\_authcheck.txt"

lines = []
lines.append(f"profile_exists={profile.exists()}")
lines.append(f"profile_locked={lock.exists()}")
if not lock.exists() and profile.exists():
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(profile), headless=True,
                viewport={"width": 1280, "height": 800})
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.pinterest.com/",
                      wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            final_path = page.url.split("pinterest.com")[-1].split("?")[0]
            lines.append(f"landed_path={final_path}")
            logged_in = page.evaluate(
                "() => { return "
                "!!document.querySelector(\"[data-test-id='header-profile-menu']\") "
                "|| !!document.querySelector(\"[data-test-id='profile-button']\") "
                "|| !!document.querySelector(\"a[href*='/settings/']\") "
                "|| !!document.querySelector(\"img[alt*='profile' i]\"); }")
            lines.append(f"logged_in={str(logged_in).lower()}")
            has_login_word = page.evaluate(
                "() => { const t = (document.body && document.body.innerText) || "
                "''; return t.includes('Log in') || t.includes('Sign up'); }")
            lines.append(f"login_text_visible={str(has_login_word).lower()}")
            ctx.close()
    except Exception as exc:  # noqa: BLE001
        lines.append(f"authcheck_error={type(exc).__name__}: {exc}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("AUTHCHECK_DONE")
