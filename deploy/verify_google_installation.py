from __future__ import annotations

import os
import re
import ssl
import urllib.request

BASE_URL = "https://apricenadialetto.it/"
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configuration.php"))


def read_google_ids() -> tuple[str, str, str]:
    content = ""
    if os.path.isfile(CONFIG_PATH):
        content = open(CONFIG_PATH, "r", encoding="utf-8", errors="ignore").read()

    def extract(name: str) -> str:
        m = re.search(rf"public\s+\${name}\s*=\s*'([^']*)'", content)
        return m.group(1).strip() if m else ""

    return extract("google_tag_manager_id"), extract("google_analytics_id"), extract("google_site_verification")


def fetch_html(url: str) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SEO-Checker)"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def main() -> int:
    gtm_id, ga_id, gsv = read_google_ids()
    html = fetch_html(BASE_URL)

    print(f"URL {BASE_URL}")
    print(f"CONFIG gtm={gtm_id or '-'} ga={ga_id or '-'} gsv={'set' if gsv else 'not-set'}")

    if gtm_id:
        has_gtm = f"googletagmanager.com/gtm.js?id={gtm_id}" in html
        has_noscript = f"ns.html?id={gtm_id}" in html
        print("GTM_SCRIPT", "OK" if has_gtm else "MISSING")
        print("GTM_NOSCRIPT", "OK" if has_noscript else "MISSING")

    if ga_id:
        has_ga = f"googletagmanager.com/gtag/js?id={ga_id}" in html
        has_ga_cfg = ga_id in html and "gtag('config'" in html
        print("GA_SCRIPT", "OK" if has_ga else "MISSING")
        print("GA_CONFIG", "OK" if has_ga_cfg else "MISSING")

    if gsv:
        has_gsv = "google-site-verification" in html and gsv in html
        print("SEARCH_CONSOLE_META", "OK" if has_gsv else "MISSING")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
