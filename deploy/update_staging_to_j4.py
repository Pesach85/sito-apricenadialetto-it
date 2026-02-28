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
DEFAULT_PACKAGE_URL = "https://github.com/joomla/joomla-cms/releases/download/4.4.13/Joomla_4.4.13-Stable-Update_Package.zip"


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
    parser = argparse.ArgumentParser(description="Aggiorna clone staging verso Joomla 4 (overlay package)")
    parser.add_argument("--apply", action="store_true", help="Esegue l'update reale")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    parser.add_argument("--package-url", default=DEFAULT_PACKAGE_URL, help="URL package Joomla 4 update")
    args = parser.parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")
    staging_root = remote_root + "_staging"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_root = f"/home/{username}/upgrade_work/j4_{ts}"
    package_file = posixpath.join(work_root, "joomla_j4_update.zip")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    plan = {
        "staging_root": staging_root,
        "package_url": args.package_url,
        "work_root": work_root,
        "package_file": package_file,
    }
    print("J4_UPDATE_PLAN")
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    preflight_cmds = {
        "staging_exists": f"test -d {shlex.quote(staging_root)} && echo OK || echo FAIL",
        "unzip_available": "command -v unzip >/dev/null 2>&1 && echo OK || echo MISSING",
        "curl_available": "command -v curl >/dev/null 2>&1 && echo OK || echo MISSING",
        "wget_available": "command -v wget >/dev/null 2>&1 && echo OK || echo MISSING",
        "disk_space": f"df -h {shlex.quote(posixpath.dirname(staging_root))} | tail -n 1",
    }

    preflight: dict[str, str] = {}
    for key, cmd in preflight_cmds.items():
        code, out, err = ssh_exec(ssh, cmd)
        value = out.strip() or err.strip()
        preflight[key] = value
        print(f"PREFLIGHT {key}: {value}")

    if preflight.get("staging_exists") != "OK":
        ssh.close()
        raise RuntimeError("Staging root non trovato")
    if preflight.get("unzip_available") != "OK":
        ssh.close()
        raise RuntimeError("unzip non disponibile sul server")
    if preflight.get("curl_available") != "OK" and preflight.get("wget_available") != "OK":
        ssh.close()
        raise RuntimeError("Né curl né wget disponibili sul server")

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        ssh.close()
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        return 3

    code, out, err = ssh_exec(ssh, "mkdir -p " + shlex.quote(work_root))
    if code != 0:
        ssh.close()
        raise RuntimeError("mkdir work_root fallito: " + err.strip())

    if preflight.get("curl_available") == "OK":
        download_cmd = "curl -fL " + shlex.quote(args.package_url) + " -o " + shlex.quote(package_file)
    else:
        download_cmd = "wget -O " + shlex.quote(package_file) + " " + shlex.quote(args.package_url)

    code, out, err = ssh_exec(ssh, download_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("download package fallito: " + err.strip())

    ssh_exec(ssh, "chmod u+w " + shlex.quote(posixpath.join(staging_root, "configuration.php")))

    unzip_cmd = "unzip -o " + shlex.quote(package_file) + " -d " + shlex.quote(staging_root)
    code, out, err = ssh_exec(ssh, unzip_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("unzip package fallito: " + err.strip())

    verify_version_cmd = (
        "php -r "
        + shlex.quote(
            "$f='"
            + posixpath.join(staging_root, "administrator/manifests/files/joomla.xml")
            + "';"
            + "$x=@simplexml_load_file($f);"
            + "if($x && isset($x->version)){echo trim((string)$x->version);}"
        )
    )
    code, out, err = ssh_exec(ssh, verify_version_cmd)
    detected_version = out.strip()

    cache_clear_cmd = (
        "find "
        + shlex.quote(staging_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(staging_root + "/tmp")
        + " -type f ! -name index.html -delete"
    )
    code_cache, out_cache, err_cache = ssh_exec(ssh, cache_clear_cmd)
    if code_cache != 0:
        ssh.close()
        raise RuntimeError("cache clear staging fallito: " + err_cache.strip())

    ssh_exec(ssh, "chmod 444 " + shlex.quote(posixpath.join(staging_root, "configuration.php")))

    ssh.close()

    print("J4_UPDATE_OK")
    print("detected_version=", detected_version)
    print("note= Verificare backend staging e completare eventuali migrazioni DB da amministrazione")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
