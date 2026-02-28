from __future__ import annotations

import os
import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")
REMOTE_ROOT = "/home/w19158/public_html"

if not PASSPHRASE:
    print("ERROR: missing SFTP_PASSPHRASE env var")
    raise SystemExit(10)

pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

cmd = (
    f"find {REMOTE_ROOT}/cache -type f ! -name index.html -delete; "
    f"find {REMOTE_ROOT}/tmp -type f ! -name index.html -delete; "
    f"echo CACHE_CLEAR_OK"
)
stdin, stdout, stderr = ssh.exec_command(cmd)
code = stdout.channel.recv_exit_status()
out = stdout.read().decode("utf-8", errors="ignore")
err = stderr.read().decode("utf-8", errors="ignore")

print(f"EXIT={code}")
if out.strip():
    print(out.strip())
if err.strip():
    print(err.strip())

ssh.close()
