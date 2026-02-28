from __future__ import annotations

import json
import os

import paramiko

LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")

with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
    cfg = json.load(handle)

pkey = paramiko.RSAKey.from_private_key_file(cfg["privateKeyPath"], password=cfg.get("passphrase", ""))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(cfg["host"], port=int(cfg.get("port", 22)), username=cfg["username"], pkey=pkey, timeout=20)

cmd = (
    "ls -l /home/w19158/public_html_staging/configuration.php; "
    "stat -c '%a %U %G' /home/w19158/public_html_staging/configuration.php; "
    "test -w /home/w19158/public_html_staging/configuration.php && echo WRITABLE || echo NOT_WRITABLE"
)
stdin, stdout, stderr = ssh.exec_command(cmd)
exit_code = stdout.channel.recv_exit_status()
print(stdout.read().decode("utf-8", errors="ignore"))
err = stderr.read().decode("utf-8", errors="ignore")
if err.strip():
    print(err)
print("EXIT", exit_code)
ssh.close()
