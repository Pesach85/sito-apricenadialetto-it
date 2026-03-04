from __future__ import annotations

import json
import os

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")


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

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    pattern = r"loadArray\(\) on null|Undefined property: stdClass::\$(locked|package_id|requireReset)|Fatal error"
    cmd = (
        "grep -RinE "
        + "'"
        + pattern
        + "' "
        + "/home/w19158/public_html/administrator/error_log /home/w19158/public_html/error_log "
        + "2>/dev/null | tail -n 80"
    )

    _, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")

    print(f"EXIT={code}")
    if out.strip():
        print(out.strip())
    else:
        print("NO_MATCH")
    if err.strip():
        print("STDERR:")
        print(err.strip())

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
