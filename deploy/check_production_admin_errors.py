from __future__ import annotations

import json
import os
import posixpath
import shlex

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return code, out, err


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    admin_url = "https://www.apricenadialetto.it/administrator/"
    checks = {
        "curl_admin_headers": "curl -k -sS -I " + shlex.quote(admin_url) + " | head -n 20",
        "tail_public_error_log": "test -f " + shlex.quote(posixpath.join(remote_root, "error_log")) + " && tail -n 120 " + shlex.quote(posixpath.join(remote_root, "error_log")) + " || echo MISSING",
        "tail_admin_error_log": "test -f " + shlex.quote(posixpath.join(remote_root, "administrator/error_log")) + " && tail -n 120 " + shlex.quote(posixpath.join(remote_root, "administrator/error_log")) + " || echo MISSING",
        "php_lint_admin_index": "php -l " + shlex.quote(posixpath.join(remote_root, "administrator/index.php")),
        "php_lint_lib_version": "test -f " + shlex.quote(posixpath.join(remote_root, "libraries/src/Version.php")) + " && php -l " + shlex.quote(posixpath.join(remote_root, "libraries/src/Version.php")) + " || echo MISSING",
    }

    for name, cmd in checks.items():
        code, out, err = ssh_exec(ssh, cmd)
        print(f"=== {name} (exit={code}) ===")
        if out.strip():
            print(out.strip())
        if err.strip():
            print("ERR:")
            print(err.strip())

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
