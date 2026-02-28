from __future__ import annotations

import os
import posixpath
import stat
import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")
REMOTE_ROOT = "/home/w19158/public_html"
LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REL = "templates/ja_elastica/css/modernize.css"


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
local_path = os.path.join(LOCAL_ROOT, *REL.split('/'))
remote_path = posixpath.join(REMOTE_ROOT, REL)
backup_path = remote_path + ".bak_tune"

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
print("UPLOAD_OK", REL)
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
