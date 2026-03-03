from __future__ import annotations

import argparse
import json
import os
import posixpath
import shlex
from datetime import datetime

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
    parser = argparse.ArgumentParser(description="Neutralizza file legacy versione Joomla 2.5 su produzione")
    parser.add_argument("--apply", action="store_true", help="Esegue modifica reale")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    args = parser.parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")

    legacy_file = posixpath.join(remote_root, "libraries/cms/version/version.php")
    backup_file = legacy_file + ".legacy2_5_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    j4_file = posixpath.join(remote_root, "libraries/src/Version.php")
    xml_file = posixpath.join(remote_root, "administrator/manifests/files/joomla.xml")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    print("HYBRID_RESOLUTION_PLAN")
    print(json.dumps({
        "remote_root": remote_root,
        "legacy_file": legacy_file,
        "backup_file": backup_file,
        "j4_file": j4_file,
        "xml_file": xml_file,
    }, ensure_ascii=False, indent=2))

    checks = {
        "xml_version": "php -r " + shlex.quote(
            "$f='" + xml_file + "';$x=@simplexml_load_file($f);if($x&&isset($x->version)){echo trim((string)$x->version);}"
        ),
        "j4_file_exists": f"test -f {shlex.quote(j4_file)} && echo FOUND || echo MISSING",
        "legacy_file_exists": f"test -f {shlex.quote(legacy_file)} && echo FOUND || echo MISSING",
    }

    pre: dict[str, str] = {}
    for key, cmd in checks.items():
        code, out, err = ssh_exec(ssh, cmd)
        value = out.strip() or err.strip()
        pre[key] = value
        print(f"PRECHECK {key}: {value}")

    if pre.get("j4_file_exists") != "FOUND":
        ssh.close()
        raise RuntimeError("Version.php Joomla 4 non trovato, abort")

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        ssh.close()
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        return 3

    if pre.get("legacy_file_exists") == "FOUND":
        cmd_mv = "mv " + shlex.quote(legacy_file) + " " + shlex.quote(backup_file)
        code, out, err = ssh_exec(ssh, cmd_mv)
        if code != 0:
            ssh.close()
            raise RuntimeError("Rinomina file legacy fallita: " + err.strip())
        print("ACTION legacy_file_renamed=YES")
    else:
        print("ACTION legacy_file_renamed=NO_ALREADY_MISSING")

    post_checks = {
        "legacy_file_exists": f"test -f {shlex.quote(legacy_file)} && echo FOUND || echo MISSING",
        "legacy_backup_exists": f"test -f {shlex.quote(backup_file)} && echo FOUND || echo MISSING",
        "xml_version": checks["xml_version"],
    }

    for key, cmd in post_checks.items():
        code, out, err = ssh_exec(ssh, cmd)
        value = out.strip() or err.strip()
        print(f"POSTCHECK {key}: {value}")

    ssh.close()
    print("HYBRID_RESOLUTION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
