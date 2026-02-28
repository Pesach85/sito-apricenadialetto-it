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


def parse_kv_lines(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


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
        "remote_root": remote_root,
        "staging_root": staging_root,
        "checks": {},
    }

    checks = {
        "staging_root_exists": f"test -d {shlex.quote(staging_root)} && echo OK || echo FAIL",
        "staging_config_exists": f"test -f {shlex.quote(posixpath.join(staging_root, 'configuration.php'))} && echo OK || echo FAIL",
        "staging_admin_exists": f"test -d {shlex.quote(posixpath.join(staging_root, 'administrator'))} && echo OK || echo FAIL",
        "staging_cache_writable": f"test -w {shlex.quote(posixpath.join(staging_root, 'cache'))} && echo OK || echo FAIL",
        "staging_tmp_writable": f"test -w {shlex.quote(posixpath.join(staging_root, 'tmp'))} && echo OK || echo FAIL",
    }

    for name, cmd in checks.items():
        code, out, err = ssh_exec(ssh, cmd)
        value = (out.strip() or err.strip() or "FAIL")
        report["checks"][name] = {"ok": value == "OK", "value": value}

    config_cmd = (
        "php -r "
        + shlex.quote(
            "$f='"
            + posixpath.join(staging_root, "configuration.php")
            + "';"
            + "if(!file_exists($f)){echo 'CFG=FAIL'; exit(2);}"
            + "require $f;"
            + "$c=new JConfig();"
            + "echo 'DB='.$c->db.PHP_EOL;"
            + "echo 'DBPREFIX='.$c->dbprefix.PHP_EOL;"
            + "echo 'FORCE_SSL='.$c->force_ssl.PHP_EOL;"
            + "echo 'TMP_PATH='.$c->tmp_path.PHP_EOL;"
            + "echo 'LOG_PATH='.$c->log_path.PHP_EOL;"
        )
    )
    code, out, err = ssh_exec(ssh, config_cmd)
    cfg_values = parse_kv_lines(out)
    expected_tmp = posixpath.join(staging_root, "tmp")
    expected_log = posixpath.join(staging_root, "logs")
    config_ok = (
        code == 0
        and "DBPREFIX" in cfg_values
        and cfg_values.get("DBPREFIX", "").startswith("stg")
        and cfg_values.get("FORCE_SSL", "") == "0"
        and cfg_values.get("TMP_PATH", "") == expected_tmp
        and cfg_values.get("LOG_PATH", "") == expected_log
    )

    report["config"] = {
        "ok": config_ok,
        "values": cfg_values,
        "expected": {
            "DBPREFIX_startswith": "stg",
            "FORCE_SSL": "0",
            "TMP_PATH": expected_tmp,
            "LOG_PATH": expected_log,
        },
        "stderr": err.strip(),
    }

    db = cfg_values.get("DB", "")
    dbprefix = cfg_values.get("DBPREFIX", "")

    if db and dbprefix:
        db_check_cmd = (
            "php -r "
            + shlex.quote(
                "$f='"
                + posixpath.join(staging_root, "configuration.php")
                + "';"
                + "require $f;"
                + "$c=new JConfig();"
                + "$m=@mysqli_connect($c->host,$c->user,$c->password,$c->db);"
                + "if(!$m){echo 'DB_CONN=FAIL'; exit(3);}"
                + "$prefix=$c->dbprefix;"
                + "$q=\"SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema='\".$c->db.\"' AND table_name LIKE '\".$prefix.\"%'\";"
                + "$r=mysqli_query($m,$q);"
                + "$row=mysqli_fetch_assoc($r);"
                + "echo 'TABLES_WITH_PREFIX='.(int)$row['c'].PHP_EOL;"
                + "mysqli_close($m);"
            )
        )
        code, out, err = ssh_exec(ssh, db_check_cmd)
        db_values = parse_kv_lines(out)
        table_count = int(db_values.get("TABLES_WITH_PREFIX", "0") or 0)
        report["db_prefix_tables"] = {
            "ok": code == 0 and table_count > 20,
            "table_count": table_count,
            "stderr": err.strip(),
        }
    else:
        report["db_prefix_tables"] = {"ok": False, "table_count": 0, "stderr": "Config non leggibile"}

    ssh.close()

    overall_ok = True
    for value in report["checks"].values():
        if not value["ok"]:
            overall_ok = False
    if not report["config"]["ok"]:
        overall_ok = False
    if not report["db_prefix_tables"]["ok"]:
        overall_ok = False

    report["status"] = "STAGING_VERIFY_OK" if overall_ok else "STAGING_VERIFY_FAIL"

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["status"])
    return 0 if overall_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
