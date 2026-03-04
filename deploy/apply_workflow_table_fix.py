from __future__ import annotations

import json
import os
import posixpath

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
LOCAL_RUNNER = os.path.join(LOCAL_ROOT, "deploy", "run_sql_updates.php")
LOCAL_SQL = os.path.join(LOCAL_ROOT, "deploy", "03_fix_missing_workflow_tables.sql")


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")

    remote_runner = posixpath.join(remote_root, "deploy", "run_sql_updates.php")
    remote_sql = posixpath.join(remote_root, "deploy", "03_fix_missing_workflow_tables.sql")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    sftp = ssh.open_sftp()
    sftp.put(LOCAL_RUNNER, remote_runner)
    sftp.put(LOCAL_SQL, remote_sql)
    sftp.close()

    cmd = f"php -d display_errors=1 {remote_runner} {remote_sql}"
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
    return code


if __name__ == "__main__":
    raise SystemExit(main())
