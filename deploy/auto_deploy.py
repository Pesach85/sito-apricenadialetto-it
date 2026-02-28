from __future__ import annotations

import os
import posixpath
import stat
import sys
from datetime import datetime

import paramiko

HOST = "apricenadialetto.it"
PORT = 2299
USERNAME = "w19158"
REMOTE_ROOT = "/home/w19158/public_html"
KEY_PATH = r"C:\Users\Pasquale Lombardi\Documents\SITO_PAPA_DATI\.ssh\id_rsa"

PASSPHRASE = os.environ.get("SFTP_PASSPHRASE", "")
if not PASSPHRASE:
    print("ERROR: missing SFTP_PASSPHRASE env var")
    sys.exit(10)

LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FILES_TO_UPLOAD = [
    ".htaccess",
    "configuration.php",
    "plugins/content/me_edocs/me_edocs.php",
    "templates/gratis/src/yjsge.js",
    "templates/gratis/src/cookie-consent.js",
    "templates/gratis/yjsgcore/yjsg_head.php",
    "templates/gratis/yjsgcore/yjsg_footer.php",
    "templates/gratis/yjsgcore/yjsg_scripts.php",
    "templates/ja_elastica/blocks/header.php",
    "templates/ja_elastica/blocks/css.php",
    "templates/ja_elastica/blocks/head.php",
    "templates/ja_elastica/page/default.php",
    "templates/ja_elastica/js/cookie-consent.js",
    "modules/mod_itpfblikebox/tmpl/default.php",
    "deploy/01_fix_mixed_content.sql",
    "deploy/run_sql_updates.php",
]


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    return code, stdout.read().decode("utf-8", errors="ignore"), stderr.read().decode("utf-8", errors="ignore")


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += "/" + part
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)


def is_remote_file(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
    try:
        mode = sftp.stat(remote_path).st_mode
        return stat.S_ISREG(mode)
    except FileNotFoundError:
        return False


def main() -> int:
    pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=PASSPHRASE)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, pkey=pkey, timeout=20)

    sftp = ssh.open_sftp()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = posixpath.join(REMOTE_ROOT, "deploy", "backup_" + ts)

    print(f"Connected. Preparing backup dir: {backup_dir}")
    ensure_remote_dir(sftp, backup_dir)

    for rel in FILES_TO_UPLOAD:
        local_path = os.path.join(LOCAL_ROOT, *rel.split("/"))
        remote_path = posixpath.join(REMOTE_ROOT, rel.replace("\\", "/"))
        remote_dir = posixpath.dirname(remote_path)
        ensure_remote_dir(sftp, remote_dir)

        if is_remote_file(sftp, remote_path):
            backup_path = posixpath.join(backup_dir, rel.replace("\\", "/"))
            ensure_remote_dir(sftp, posixpath.dirname(backup_path))
            sftp.posix_rename(remote_path, backup_path)
            print(f"BACKUP {rel} -> {backup_path}")

        sftp.put(local_path, remote_path)
        print(f"UPLOAD {rel}")

    sql_remote = posixpath.join(REMOTE_ROOT, "deploy", "01_fix_mixed_content.sql")
    php_runner = posixpath.join(REMOTE_ROOT, "deploy", "run_sql_updates.php")

    code, out, err = ssh_exec(ssh, f"php {php_runner} {sql_remote}")
    print("SQL STDOUT:")
    print(out.strip())
    if err.strip():
        print("SQL STDERR:")
        print(err.strip())
    if code != 0:
        print(f"ERROR: SQL execution failed with code {code}")
        sftp.close()
        ssh.close()
        return code

    cache_clear_cmd = (
        f"find {REMOTE_ROOT}/cache -type f ! -name index.html -delete; "
        f"find {REMOTE_ROOT}/tmp -type f ! -name index.html -delete"
    )
    code, out, err = ssh_exec(ssh, cache_clear_cmd)
    if code == 0:
        print("CACHE_CLEAR_OK")
    else:
        print(f"CACHE_CLEAR_WARN code={code}")
        if err.strip():
            print(err.strip())

    sftp.close()
    ssh.close()
    print("DEPLOY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
