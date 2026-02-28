from __future__ import annotations

import os
import posixpath
import sys
import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")
REMOTE_ROOT = "/home/w19158/public_html"
LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if len(sys.argv) < 2:
    print("Usage: run_remote_php.py deploy/<script>.php")
    raise SystemExit(1)

rel_path = sys.argv[1].replace("\\", "/")
local_path = os.path.join(LOCAL_ROOT, *rel_path.split("/"))
remote_path = posixpath.join(REMOTE_ROOT, rel_path)

pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

sftp = ssh.open_sftp()
sftp.put(local_path, remote_path)
sftp.close()

cmd = f"php -d display_errors=1 {remote_path}"
stdin, stdout, stderr = ssh.exec_command(cmd)
code = stdout.channel.recv_exit_status()
out = stdout.read().decode("utf-8", errors="ignore")
err = stderr.read().decode("utf-8", errors="ignore")

print(f"EXIT={code}")
if out.strip():
    print("STDOUT:")
    print(out.strip())
if err.strip():
    print("STDERR:")
    print(err.strip())

ssh.close()
