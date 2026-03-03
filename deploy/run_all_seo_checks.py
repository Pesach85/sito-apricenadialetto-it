from __future__ import annotations

import os
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EXE = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
BASE_URL = "https://apricenadialetto.it"
SITEMAP_URL = BASE_URL + "/sitemap.xml"


def run_step(title: str, command: list[str]) -> int:
    print(f"\n=== {title} ===")
    print("CMD:", " ".join(command))
    completed = subprocess.run(command, cwd=ROOT)
    print(f"EXIT={completed.returncode}")
    return completed.returncode


def fetch_status(url: str) -> tuple[int, int]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SEO-Automation)"})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
        body = resp.read()
        return resp.getcode(), len(body)


def main() -> int:
    if not os.path.isfile(PYTHON_EXE):
        print(f"ERROR: python env not found at {PYTHON_EXE}")
        return 2

    steps = [
        ("Deploy SEO Quick", [PYTHON_EXE, "deploy/deploy_seo_quick.py"]),
        ("Verify Google Install", [PYTHON_EXE, "deploy/verify_google_installation.py"]),
    ]

    for title, cmd in steps:
        code = run_step(title, cmd)
        if code != 0:
            return code

    print("\n=== Check Sitemap URL ===")
    try:
        status, size = fetch_status(SITEMAP_URL)
        print(f"SITEMAP_STATUS {status} bytes={size}")
    except Exception as exc:
        print(f"SITEMAP_STATUS ERROR {exc}")
        return 3

    print("\n=== Google Sitemap Ping (best effort) ===")
    ping_url = "https://www.google.com/ping?sitemap=" + urllib.parse.quote(SITEMAP_URL, safe=':/?=&')
    try:
        status, size = fetch_status(ping_url)
        print(f"GOOGLE_PING_STATUS {status} bytes={size}")
    except Exception as exc:
        print(f"GOOGLE_PING_STATUS ERROR {exc}")

    print("\nRUN_ALL_SEO_CHECKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
