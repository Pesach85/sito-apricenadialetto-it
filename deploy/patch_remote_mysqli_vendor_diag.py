from __future__ import annotations

import json
import os
import posixpath
import re
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
REMOTE_PATH = "/home/w19158/public_html/libraries/vendor/joomla/database/src/Mysqli/MysqliDriver.php"

PATTERN = re.compile(r"(\$errorMsg\s*=\s*\(string\)\s*\$this->connection->error;\n)")
LOG_LINE = "                        @file_put_contents('/tmp/jdb_fail.log', '[JDB-FAIL] ' . $errorNum . ' ' . $errorMsg . ' SQL=' . $sql . \"\\n\", FILE_APPEND);\n"


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
    with sftp.open(REMOTE_PATH, "r") as fh:
        content = fh.read().decode("utf-8", errors="ignore")

    if not PATTERN.search(content):
        print("PATCH_TARGET_NOT_FOUND")
        sftp.close()
        ssh.close()
        return 2

    backup_path = REMOTE_PATH + ".bak_vendor_diag_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    sftp.posix_rename(REMOTE_PATH, backup_path)
    print("BACKUP_OK", backup_path)

    patched, replacements = PATTERN.subn(r"\1" + LOG_LINE, content)
    if replacements == 0:
        print("PATCH_NO_REPLACEMENTS")
        sftp.close()
        ssh.close()
        return 3
    print("PATCH_REPLACEMENTS", replacements)
    with sftp.open(REMOTE_PATH, "w") as fh:
        fh.write(patched)
    print("PATCH_APPLIED")

    sftp.close()

    cmd = f"php -l {REMOTE_PATH}"
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
