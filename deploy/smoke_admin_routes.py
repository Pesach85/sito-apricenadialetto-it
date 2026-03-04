from __future__ import annotations

import argparse
import re
from pathlib import Path

import requests


BASE = "https://www.apricenadialetto.it/administrator/"
ROUTES = [
    "index.php",
    "index.php?option=com_users&view=users",
    "index.php?option=com_templates&view=styles",
    "index.php?option=com_templates&view=templates",
    "index.php?option=com_menus&view=menus",
    "index.php?option=com_content&view=articles",
    "index.php?option=com_content&task=article.add",
    "index.php?option=com_plugins&view=plugins",
    "index.php?option=com_installer&view=manage",
    "index.php?option=com_modules&view=modules&client_id=1",
]


def get_login(session: requests.Session) -> tuple[str, str]:
    response = session.get(BASE, timeout=20)
    response.raise_for_status()
    html = response.text

    token = re.search(r'name="([a-f0-9]{32})"\s+value="1"', html)
    if not token:
        raise RuntimeError("CSRF token not found")
    return html, token.group(1)


def login(session: requests.Session, username: str, password: str) -> None:
    _, token = get_login(session)
    data = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
        "return": "aW5kZXgucGhw",
        token: "1",
    }
    response = session.post(BASE + "index.php", data=data, timeout=20, allow_redirects=True)
    response.raise_for_status()


def classify(html: str) -> str:
    if "Call to a member function loadArray() on null" in html:
        return "FAIL_LOADARRAY_NULL"
    if "Fatal error" in html or "Si è verificato un errore" in html:
        return "FAIL_GENERIC"
    if "Home Dashboard" in html or "administrator/atum" in html:
        return "OK"
    return "OK"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": "admin-smoke/1.0"})

    login(session, args.username, args.password)

    backup_dir = Path(__file__).resolve().parents[1] / "upgrade_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    failures = 0

    for route in ROUTES:
        url = BASE + route
        response = session.get(url, timeout=25)
        status = response.status_code
        html = response.text
        verdict = classify(html)
        out_name = route.replace("?", "_").replace("&", "_").replace("=", "-")
        out_file = backup_dir / f"smoke_{out_name}.html"
        out_file.write_text(html, encoding="utf-8", errors="ignore")
        print(f"{status} {verdict} {route}")
        if verdict != "OK":
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
