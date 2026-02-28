from __future__ import annotations

import os
import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"
PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")

LOCAL_RUNNER = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_sql_updates.php"))
LOCAL_SQL = os.path.abspath(os.path.join(os.path.dirname(__file__), "01_fix_mixed_content.sql"))
REMOTE_RUNNER = "/home/w19158/public_html/deploy/run_sql_updates.php"
REMOTE_SQL = "/home/w19158/public_html/deploy/01_fix_mixed_content.sql"

pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

sftp = ssh.open_sftp()
sftp.put(LOCAL_RUNNER, REMOTE_RUNNER)
sftp.put(LOCAL_SQL, REMOTE_SQL)
sftp.close()

cmd = f"php -d display_errors=1 {REMOTE_RUNNER} {REMOTE_SQL}"
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
