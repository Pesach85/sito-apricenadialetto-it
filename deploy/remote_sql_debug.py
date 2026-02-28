from __future__ import annotations

import os
import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")

commands = [
    "pwd",
    "which php || command -v php || echo NO_PHP",
    "php -v",
    "ls -la /home/w19158/public_html/deploy | sed -n '1,120p'",
    "php -d display_errors=1 /home/w19158/public_html/deploy/run_sql_updates.php /home/w19158/public_html/deploy/01_fix_mixed_content.sql",
]

pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

for cmd in commands:
    print(f"\n=== CMD: {cmd}")
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
