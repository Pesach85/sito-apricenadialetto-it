from __future__ import annotations

import json
import os
import posixpath
import sys

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_remote_php.py deploy/<script>.php")
        return 1

    rel_path = sys.argv[1].replace("\\", "/")
    local_path = os.path.join(LOCAL_ROOT, *rel_path.split("/"))

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg.get("remotePath", "/home/w19158/public_html")

    remote_path = posixpath.join(remote_root, rel_path)

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=20)

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
    return code


if __name__ == "__main__":
    raise SystemExit(main())
