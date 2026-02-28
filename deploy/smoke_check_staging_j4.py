from __future__ import annotations

import base64
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


def parse_table(raw: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in raw.splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def get_staging_db_cfg(ssh: paramiko.SSHClient, staging_root: str) -> dict:
    cfg_path = posixpath.join(staging_root, "configuration.php")
    cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + cfg_path
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array('host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix)));"
        )
    )
    code, out, err = ssh_exec(ssh, cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Lettura configuration.php staging fallita: " + err.strip())
    return json.loads(base64.b64decode(out.strip()).decode("utf-8"))


def run_mysql(ssh: paramiko.SSHClient, db_cfg: dict, sql: str) -> tuple[int, str, str]:
    cmd = (
        "MYSQL_PWD="
        + shlex.quote(db_cfg["password"])
        + " mysql -N -B -h "
        + shlex.quote(db_cfg["host"])
        + " -u "
        + shlex.quote(db_cfg["user"])
        + " -D "
        + shlex.quote(db_cfg["db"])
        + " -e "
        + shlex.quote(sql)
    )
    return ssh_exec(ssh, cmd)


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")
    staging_root = remote_root + "_staging"

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    report: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "staging_root": staging_root,
        "checks": {},
    }

    code, out, err = ssh_exec(ssh, "php -r 'echo PHP_VERSION;'")
    report["checks"]["php_version"] = {"ok": code == 0 and bool(out.strip()), "value": out.strip()}

    code, out, err = ssh_exec(
        ssh,
        "php -r "
        + shlex.quote(
            "$f='"
            + posixpath.join(staging_root, "administrator/manifests/files/joomla.xml")
            + "';$x=@simplexml_load_file($f);if($x&&isset($x->version)){echo trim((string)$x->version);}"
        ),
    )
    version = out.strip()
    report["checks"]["joomla_version"] = {"ok": bool(version), "value": version}

    code, out, err = ssh_exec(
        ssh,
        "test -f " + shlex.quote(posixpath.join(staging_root, "administrator/index.php")) + " && echo OK || echo MISSING",
    )
    report["checks"]["admin_index"] = {"ok": out.strip() == "OK", "value": out.strip()}

    code, out, err = ssh_exec(
        ssh,
        "find " + shlex.quote(staging_root + "/cache") + " -maxdepth 1 -type f | wc -l",
    )
    report["checks"]["cache_file_count"] = {"ok": code == 0, "value": out.strip()}

    db_cfg = get_staging_db_cfg(ssh, staging_root)
    ext_table = db_cfg["dbprefix"] + "extensions"
    sql = (
        "SELECT type,element,folder,enabled FROM "
        + ext_table
        + " WHERE (type='plugin' AND folder='system' AND element='jat3')"
        + " OR (type='component' AND element='com_akeeba')"
        + " OR (type='component' AND element='com_phocafavicon')"
        + " OR (type='plugin' AND folder='content' AND element='me_edocs')"
        + " OR (type='module' AND element='mod_itpfblikebox')"
    )
    code, out, err = run_mysql(ssh, db_cfg, sql)
    rows = parse_table(out) if code == 0 else []
    state = {}
    for row in rows:
        if len(row) >= 4:
            key = f"{row[0]}:{row[2]}:{row[1]}"
            state[key] = row[3] == "1"
    report["checks"]["legacy_state"] = {"ok": True, "state": state}

    code, out, err = ssh_exec(ssh, "tail -n 80 " + shlex.quote(staging_root + "/error_log") + " 2>/dev/null | tail -n 40")
    report["checks"]["error_log_tail"] = {"ok": code == 0, "value": out.strip()}

    ssh.close()

    overall_ok = (
        report["checks"]["php_version"]["ok"]
        and report["checks"]["joomla_version"]["ok"]
        and report["checks"]["admin_index"]["ok"]
    )
    report["status"] = "SMOKE_OK" if overall_ok else "SMOKE_FAIL"

    out_path = os.path.join(LOCAL_ROOT, "upgrade_backups", "staging_smoke_j4_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["status"])
    print("report=", out_path)
    return 0 if overall_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
