from __future__ import annotations

import json
import os
import posixpath
import stat

import paramiko

LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")

with open(SFTP_CONFIG, "r", encoding="utf-8") as handle:
    cfg = json.load(handle)

HOST = cfg["host"]
PORT = int(cfg.get("port", 22))
USERNAME = cfg["username"]
KEY_PATH = cfg["privateKeyPath"]
PASSPHRASE = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
REMOTE_ROOT = cfg["remotePath"].rstrip("/")

FILES = [
    "privacy_policy.html",
    "templates/ja_elastica/page/default.php",
    "templates/gratis/yjsgcore/yjsg_footer.php",
]


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += "/" + part
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)


pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

sftp = ssh.open_sftp()
for rel in FILES:
    local_path = os.path.join(LOCAL_ROOT, *rel.split('/'))
    remote_path = posixpath.join(REMOTE_ROOT, rel)
    backup_path = remote_path + ".bak_privacy"

    ensure_remote_dir(sftp, posixpath.dirname(remote_path))

    try:
        mode = sftp.stat(remote_path).st_mode
        if stat.S_ISREG(mode):
            try:
                sftp.remove(backup_path)
            except Exception:
                pass
            sftp.posix_rename(remote_path, backup_path)
            print("BACKUP_OK", backup_path)
    except FileNotFoundError:
        pass

    sftp.put(local_path, remote_path)
    print("UPLOAD_OK", rel)

sftp.close()

cmd = (
    f"find {REMOTE_ROOT}/cache -type f ! -name index.html -delete; "
    f"find {REMOTE_ROOT}/tmp -type f ! -name index.html -delete; "
    f"echo CACHE_CLEAR_OK"
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
