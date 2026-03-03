from __future__ import annotations

import os
import posixpath
import re
import stat
import sys
from datetime import datetime

import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
REMOTE_ROOT = "/home/w19158/public_html"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
BASE_URL = "https://apricenadialetto.it"

LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(LOCAL_ROOT, "configuration.php")

PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")
if not PASSPHRASE:
    print("ERROR: missing SFTP_PASSPHRASE env var")
    sys.exit(10)

FILES_TO_UPLOAD = [
    "configuration.php",
    "robots.txt",
    "cli/generate_sitemap.php",
    "templates/cassiopeia/index.php",
    "templates/ja_elastica/blocks/head.php",
    "templates/ja_elastica/page/default.php",
]


def read_google_ids() -> tuple[str, str, str]:
    if not os.path.isfile(CONFIG_PATH):
        return "", "", ""

    content = open(CONFIG_PATH, "r", encoding="utf-8", errors="ignore").read()

    def extract(name: str) -> str:
        pattern = rf"public\s+\${name}\s*=\s*'([^']*)'"
        m = re.search(pattern, content)
        return (m.group(1).strip() if m else "")

    return extract("google_tag_manager_id"), extract("google_analytics_id"), extract("google_site_verification")


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    return code, stdout.read().decode("utf-8", errors="ignore"), stderr.read().decode("utf-8", errors="ignore")


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += "/" + part
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)


def is_remote_file(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
    try:
        mode = sftp.stat(remote_path).st_mode
        return stat.S_ISREG(mode)
    except FileNotFoundError:
        return False


def main() -> int:
    gtm_id, ga_id, gsv = read_google_ids()
    print(f"LOCAL_IDS gtm={gtm_id or '-'} ga={ga_id or '-'} gsv={'set' if gsv else 'not-set'}")

    pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

    sftp = ssh.open_sftp()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = posixpath.join(REMOTE_ROOT, "deploy", "backup_seo_quick_" + ts)
    ensure_remote_dir(sftp, backup_dir)

    print(f"Connected. Backup dir: {backup_dir}")

    for rel in FILES_TO_UPLOAD:
        local_path = os.path.join(LOCAL_ROOT, *rel.split("/"))
        if not os.path.isfile(local_path):
            print(f"SKIP missing local file: {rel}")
            continue

        remote_path = posixpath.join(REMOTE_ROOT, rel.replace("\\", "/"))
        ensure_remote_dir(sftp, posixpath.dirname(remote_path))

        if is_remote_file(sftp, remote_path):
            backup_path = posixpath.join(backup_dir, rel.replace("\\", "/"))
            ensure_remote_dir(sftp, posixpath.dirname(backup_path))
            sftp.posix_rename(remote_path, backup_path)
            print(f"BACKUP {rel}")

        sftp.put(local_path, remote_path)
        print(f"UPLOAD {rel}")

    code, out, err = ssh_exec(ssh, f"php {REMOTE_ROOT}/cli/generate_sitemap.php --base-url={BASE_URL}")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    if code != 0:
        print(f"WARN sitemap generation exit={code}")

    check_cmd = f"curl -k -L -s {BASE_URL}/ | head -c 250000"
    code, out, err = ssh_exec(ssh, check_cmd)
    html = out or ""

    if gtm_id:
        print("CHECK_GTM_SCRIPT", "OK" if f"googletagmanager.com/gtm.js?id={gtm_id}" in html else "MISSING")
        print("CHECK_GTM_NOSCRIPT", "OK" if f"ns.html?id={gtm_id}" in html else "MISSING")
    elif ga_id:
        print("CHECK_GA_SCRIPT", "OK" if f"googletagmanager.com/gtag/js?id={ga_id}" in html else "MISSING")

    if gsv:
        print("CHECK_GSV_META", "OK" if "google-site-verification" in html and gsv in html else "MISSING")

    cache_clear_cmd = (
        f"find {REMOTE_ROOT}/cache -type f ! -name index.html -delete; "
        f"find {REMOTE_ROOT}/tmp -type f ! -name index.html -delete"
    )
    code, out, err = ssh_exec(ssh, cache_clear_cmd)
    print("CACHE_CLEAR_OK" if code == 0 else f"CACHE_CLEAR_WARN code={code}")

    sftp.close()
    ssh.close()
    print("DEPLOY_QUICK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
