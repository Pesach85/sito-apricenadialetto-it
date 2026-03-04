from __future__ import annotations

import json
import os

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
REMOTE_FILES = [
    "/home/w19158/public_html/libraries/vendor/joomla/database/src/Mysqli/MysqliDriver.php",
    "/home/w19158/public_html/libraries/vendor/joomla/database/src/Mysqli/MysqliStatement.php",
]


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

    sftp = ssh.open_sftp()
    for remote_path in REMOTE_FILES:
        with sftp.open(remote_path, "r") as fh:
            content = fh.read().decode("utf-8", errors="ignore")
        patched = content.replace("'/tmp/jdb_fail.log'", "JPATH_ROOT . '/tmp/jdb_fail.log'")
        if patched != content:
            with sftp.open(remote_path, "w") as fh:
                fh.write(patched)
            print("UPDATED", remote_path)
        else:
            print("UNCHANGED", remote_path)

    sftp.close()

    cmd = "php -l {0}; php -l {1}".format(REMOTE_FILES[0], REMOTE_FILES[1])
    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    print(f"LINT_EXIT={code}")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

    ssh.close()
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
