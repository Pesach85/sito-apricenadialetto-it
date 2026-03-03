from __future__ import annotations

import json
import os
import posixpath
import re
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


def check_http_status(ssh: paramiko.SSHClient, url: str) -> tuple[bool, str]:
    cmd = "curl -k -sS -I " + shlex.quote(url) + " | head -n 1"
    code, out, err = ssh_exec(ssh, cmd)
    line = out.strip() if out.strip() else err.strip()
    ok = bool(re.search(r"\s200\s|\s200$", line))
    return ok, line


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    root = cfg["remotePath"].rstrip("/")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    report: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": root,
        "checks": {},
    }

    file_checks = {
        "admin_index": posixpath.join(root, "administrator/index.php"),
        "admin_app": posixpath.join(root, "administrator/includes/app.php"),
        "behavior_helper": posixpath.join(root, "libraries/src/HTML/Helpers/Behavior.php"),
        "joomla_manifest": posixpath.join(root, "administrator/manifests/files/joomla.xml"),
    }

    checks = report["checks"]
    assert isinstance(checks, dict)

    for key, file_path in file_checks.items():
        cmd = "test -f " + shlex.quote(file_path) + " && echo FOUND || echo MISSING"
        code, out, err = ssh_exec(ssh, cmd)
        value = out.strip() or err.strip()
        checks[key] = {"ok": value == "FOUND", "value": value}

    code, out, err = ssh_exec(
        ssh,
        "php -r "
        + shlex.quote(
            "$f='"
            + posixpath.join(root, "administrator/manifests/files/joomla.xml")
            + "';$x=@simplexml_load_file($f);if($x&&isset($x->version)){echo trim((string)$x->version);}"
        ),
    )
    version = out.strip() or err.strip()
    checks["joomla_version"] = {"ok": bool(re.match(r"^4\.4\.13$", version)), "value": version}

    code, out, err = ssh_exec(
        ssh,
        "grep -n " + shlex.quote("function noframes(") + " " + shlex.quote(posixpath.join(root, "libraries/src/HTML/Helpers/Behavior.php")) + " | head -n 1",
    )
    noframes_line = out.strip() or err.strip()
    checks["behavior_noframes"] = {"ok": code == 0 and noframes_line != "", "value": noframes_line}

    admin_ok, admin_status = check_http_status(ssh, "https://www.apricenadialetto.it/administrator/")
    checks["administrator_http"] = {"ok": admin_ok, "value": admin_status}

    asset_urls = [
        "https://www.apricenadialetto.it/media/system/js/core.min.js",
        "https://www.apricenadialetto.it/media/system/css/system.css",
        "https://www.apricenadialetto.it/administrator/templates/bluestork/css/template.css",
    ]

    assets_ok = True
    asset_results = []
    for url in asset_urls:
        ok, status = check_http_status(ssh, url)
        if not ok:
            assets_ok = False
        asset_results.append({"url": url, "ok": ok, "status": status})

    checks["admin_assets_http"] = {"ok": assets_ok, "value": asset_results}

    overall_ok = all(item.get("ok") for item in checks.values() if isinstance(item, dict) and "ok" in item)
    report["status"] = "ADMIN_STACK_OK" if overall_ok else "ADMIN_STACK_FAIL"

    out_path = os.path.join(LOCAL_ROOT, "upgrade_backups", "production_admin_stack_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["status"])
    print("report=", out_path)

    ssh.close()
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
