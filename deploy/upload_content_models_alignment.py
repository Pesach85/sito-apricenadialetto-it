from __future__ import annotations

import json
import os
import posixpath
import stat
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")

REL_PATHS = [
    "administrator/components/com_content/models/article.php",
    "components/com_content/models/articles.php",
]


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += "/" + part
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg.get("remotePath", "/home/w19158/public_html")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)
    sftp = ssh.open_sftp()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for rel_path in REL_PATHS:
        local_path = os.path.join(LOCAL_ROOT, *rel_path.split("/"))
        remote_path = posixpath.join(remote_root, rel_path)
        backup_path = f"{remote_path}.bak_align_models_{stamp}"

        ensure_remote_dir(sftp, posixpath.dirname(remote_path))

        try:
            mode = sftp.stat(remote_path).st_mode
            if stat.S_ISREG(mode):
                sftp.posix_rename(remote_path, backup_path)
                print("BACKUP_OK", backup_path)
        except FileNotFoundError:
            pass

        sftp.put(local_path, remote_path)
        print("UPLOAD_OK", rel_path)

    sftp.close()

    lint_cmd = " ; ".join([
        "php -l /home/w19158/public_html/administrator/components/com_content/models/article.php",
        "php -l /home/w19158/public_html/components/com_content/models/articles.php",
    ])

    stdin, stdout, stderr = ssh.exec_command(lint_cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    print(f"LINT_EXIT={code}")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

    cache_cmd = (
        "find /home/w19158/public_html/cache -type f ! -name index.html -delete ; "
        "find /home/w19158/public_html/tmp -type f ! -name index.html -delete ; "
        "find /home/w19158/public_html/administrator/cache -type f ! -name index.html -delete ; "
        "echo CACHE_CLEAR_OK"
    )
    stdin, stdout, stderr = ssh.exec_command(cache_cmd)
    code2 = stdout.channel.recv_exit_status()
    out2 = stdout.read().decode("utf-8", errors="ignore")
    err2 = stderr.read().decode("utf-8", errors="ignore")
    print(f"CACHE_EXIT={code2}")
    if out2.strip():
        print(out2.strip())
    if err2.strip():
        print(err2.strip())

    ssh.close()
    return 0 if code == 0 and code2 == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
