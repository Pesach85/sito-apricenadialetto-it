from __future__ import annotations

import re
import sys

import requests


LOGIN_URL = "https://www.apricenadialetto.it/administrator/"
POST_URL = "https://www.apricenadialetto.it/administrator/index.php"


def extract_token(html: str) -> str:
    match = re.search(r'name="([a-f0-9]{32})"\s+value="1"', html, re.IGNORECASE)
    return match.group(1) if match else ""


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: verify_admin_login_http.py <username> <password>")
        return 1

    username = sys.argv[1]
    password = sys.argv[2]

    session = requests.Session()
    session.verify = True
    session.headers.update({"User-Agent": "Mozilla/5.0 admin-login-check"})

    get_resp = session.get(LOGIN_URL, timeout=30)
    token = extract_token(get_resp.text)
    if not token:
        print("TOKEN_MISSING")
        print("GET_STATUS", get_resp.status_code)
        return 2

    payload = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
        "return": "aW5kZXgucGhw",
        token: "1",
    }

    post_resp = session.post(POST_URL, data=payload, timeout=30, allow_redirects=True)

    body = post_resp.text
    body_l = body.lower()

    success_markers = [
        "com_cpanel",
        "panel di controllo",
        "logout",
        "task=logout",
    ]
    error_markers = [
        "nome utente e password non corretti",
        "username and password do not match",
        "invalid token",
        "access denied",
    ]

    success = any(marker in body_l for marker in success_markers)
    has_error = any(marker in body_l for marker in error_markers)

    print("GET_STATUS", get_resp.status_code)
    print("POST_STATUS", post_resp.status_code)
    print("FINAL_URL", post_resp.url)
    print("LOGIN_SUCCESS", "YES" if success and not has_error else "NO")

    if not success or has_error:
        heading = ""
        message = ""
        h_match = re.search(r"<h1>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
        if h_match:
            heading = re.sub(r"\s+", " ", h_match.group(1)).strip()
        p_match = re.search(r"<p>(.*?)</p>", body, re.IGNORECASE | re.DOTALL)
        if p_match:
            message = re.sub(r"\s+", " ", p_match.group(1)).strip()
        snippet = re.sub(r"\s+", " ", body)[:900]
        if heading:
            print("ERROR_HEADING", heading)
        if message:
            print("ERROR_MESSAGE", message)
        print("BODY_SNIPPET", snippet)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
