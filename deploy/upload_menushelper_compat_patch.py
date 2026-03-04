from __future__ import annotations

import json
import os
import posixpath
import stat
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
FILES_TO_UPLOAD = [
    "administrator/includes/legacy_dispatcher_polyfill.php",
    "administrator/components/com_menus/helpers/menus.php",
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
    remote_root = cfg["remotePath"].rstrip("/")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    sftp = ssh.open_sftp()
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    for rel_path in FILES_TO_UPLOAD:
        local_path = os.path.join(LOCAL_ROOT, *rel_path.split('/'))
        remote_path = posixpath.join(remote_root, rel_path)
        ensure_remote_dir(sftp, posixpath.dirname(remote_path))

        try:
            mode = sftp.stat(remote_path).st_mode
            if stat.S_ISREG(mode):
                backup_path = remote_path + ".bak_menushelper_" + suffix
                sftp.posix_rename(remote_path, backup_path)
                print("BACKUP_OK", backup_path)
        except FileNotFoundError:
            pass

        sftp.put(local_path, remote_path)
        print("UPLOAD_OK", rel_path)

    sftp.close()

    cmd = (
        f"php -l {posixpath.join(remote_root, 'administrator/includes/legacy_dispatcher_polyfill.php')}; "
        f"php -l {posixpath.join(remote_root, 'administrator/components/com_menus/helpers/menus.php')}; "
        f"find {remote_root}/cache -type f ! -name index.html -delete; "
        f"find {remote_root}/tmp -type f ! -name index.html -delete; "
        "echo DEPLOY_OK"
    )

    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")

    print(f"REMOTE_EXIT={code}")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

    ssh.close()
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
