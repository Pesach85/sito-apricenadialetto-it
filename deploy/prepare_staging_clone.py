from __future__ import annotations

import argparse
import base64
import json
import os
import posixpath
import re
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


def get_site_config(ssh: paramiko.SSHClient, remote_root: str) -> dict:
    remote_config = posixpath.join(remote_root, "configuration.php")
    php_cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + remote_config
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array("
            + "'host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix,"
            + "'tmp_path'=>$c->tmp_path,'log_path'=>$c->log_path,'live_site'=>$c->live_site"
            + ")));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Impossibile leggere configuration.php: " + err.strip())
    raw = base64.b64decode(out.strip())
    return json.loads(raw.decode("utf-8"))


def ensure_ok(code: int, err: str, label: str) -> None:
    if code != 0:
        raise RuntimeError(f"{label} fallito: {err.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara clone staging da produzione (dry-run di default)")
    parser.add_argument("--apply", action="store_true", help="Esegue la clonazione reale")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    parser.add_argument("--staging-root", default="", help="Path staging remoto (default: <remotePath>_staging)")
    parser.add_argument("--staging-db", default="", help="Nome DB staging (default: <db>_stg)")
    args = parser.parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    remote_root = cfg["remotePath"].rstrip("/")
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    site_cfg = get_site_config(ssh, remote_root)
    staging_root = args.staging_root.strip() or (remote_root + "_staging")
    staging_db = args.staging_db.strip() or (site_cfg["db"] + "_stg")
    source_prefix = site_cfg.get("dbprefix", "")
    fallback_prefix_base = source_prefix.rstrip("_")[:3] or "jml"
    fallback_staging_prefix = ("stg" + fallback_prefix_base + "_")

    plan = {
        "remote_root": remote_root,
        "staging_root": staging_root,
        "source_db": site_cfg["db"],
        "staging_db": staging_db,
        "source_dbprefix": source_prefix,
        "fallback_same_dbprefix": fallback_staging_prefix,
        "db_user": site_cfg["user"],
        "db_host": site_cfg["host"],
    }

    print("STAGING_PLAN")
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    preflight_cmds = {
        "rsync_available": "command -v rsync >/dev/null 2>&1 && echo OK || echo MISSING",
        "staging_parent_writable": (
            "parent=$(dirname " + shlex.quote(staging_root) + "); "
            + "test -w \"$parent\" && echo WRITABLE || echo NOT_WRITABLE"
        ),
        "mysql_available": "command -v mysql >/dev/null 2>&1 && echo OK || echo MISSING",
        "mysqldump_available": "command -v mysqldump >/dev/null 2>&1 && echo OK || echo MISSING",
    }

    preflight_results: dict[str, str] = {}
    for label, cmd in preflight_cmds.items():
        code, out, err = ssh_exec(ssh, cmd)
        value = out.strip() or err.strip()
        preflight_results[label] = value
        print(f"PREFLIGHT {label}: {value}")

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire la clonazione staging")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        ssh.close()
        return 3

    code, out, err = ssh_exec(ssh, "mkdir -p " + shlex.quote(staging_root))
    ensure_ok(code, err, "mkdir staging")

    if preflight_results.get("rsync_available") == "OK":
        clone_files_cmd = (
            "rsync -a --delete "
            + shlex.quote(remote_root + "/")
            + " "
            + shlex.quote(staging_root + "/")
            + " --exclude cache/* --exclude tmp/*"
        )
        code, out, err = ssh_exec(ssh, clone_files_cmd)
        ensure_ok(code, err, "rsync staging")
    else:
        fallback_clone_cmd = (
            "find "
            + shlex.quote(staging_root)
            + " -mindepth 1 -maxdepth 1 ! -name cache ! -name tmp -exec rm -rf {} +; "
            + "cp -a "
            + shlex.quote(remote_root + "/.")
            + " "
            + shlex.quote(staging_root + "/")
        )
        code, out, err = ssh_exec(ssh, fallback_clone_cmd)
        ensure_ok(code, err, "fallback copy staging")

    target_db = staging_db
    target_prefix = source_prefix
    create_db_cmd = (
        "MYSQL_PWD="
        + shlex.quote(site_cfg["password"])
        + " mysql -h "
        + shlex.quote(site_cfg["host"])
        + " -u "
        + shlex.quote(site_cfg["user"])
        + " -e "
        + shlex.quote(
            "CREATE DATABASE IF NOT EXISTS `" + staging_db + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
        )
    )
    code, out, err = ssh_exec(ssh, create_db_cmd)
    if code == 0:
        clone_db_cmd = (
            "MYSQL_PWD="
            + shlex.quote(site_cfg["password"])
            + " mysqldump --single-transaction --quick --routines --triggers "
            + "-h "
            + shlex.quote(site_cfg["host"])
            + " -u "
            + shlex.quote(site_cfg["user"])
            + " "
            + shlex.quote(site_cfg["db"])
            + " | MYSQL_PWD="
            + shlex.quote(site_cfg["password"])
            + " mysql -h "
            + shlex.quote(site_cfg["host"])
            + " -u "
            + shlex.quote(site_cfg["user"])
            + " "
            + shlex.quote(staging_db)
        )
        code, out, err = ssh_exec(ssh, clone_db_cmd)
        ensure_ok(code, err, "clone db")
    else:
        if "Access denied" not in err and "ERROR 1044" not in err:
            ensure_ok(code, err, "create staging db")

        print("INFO: CREATE DATABASE non consentito, fallback su stesso DB con prefix staging")
        target_db = site_cfg["db"]
        target_prefix = fallback_staging_prefix

        clone_by_prefix_cmd = (
            "MYSQL_PWD="
            + shlex.quote(site_cfg["password"])
            + " mysql -N -h "
            + shlex.quote(site_cfg["host"])
            + " -u "
            + shlex.quote(site_cfg["user"])
            + " -D "
            + shlex.quote(site_cfg["db"])
            + " -e "
            + shlex.quote(
                "SELECT CONCAT("
                + "'DROP TABLE IF EXISTS ', CHAR(96), REPLACE(table_name, '"
                + source_prefix
                + "', '"
                + target_prefix
                + "'), CHAR(96), ';',"
                + "'CREATE TABLE ', CHAR(96), REPLACE(table_name, '"
                + source_prefix
                + "', '"
                + target_prefix
                + "'), CHAR(96), ' LIKE ', CHAR(96), table_name, CHAR(96), ';',"
                + "'INSERT INTO ', CHAR(96), REPLACE(table_name, '"
                + source_prefix
                + "', '"
                + target_prefix
                + "'), CHAR(96), ' SELECT * FROM ', CHAR(96), table_name, CHAR(96), ';'"
                + ") "
                + "FROM information_schema.tables "
                + "WHERE table_schema='"
                + site_cfg["db"]
                + "' AND table_name LIKE '"
                + source_prefix
                + "%'"
            )
            + " | MYSQL_PWD="
            + shlex.quote(site_cfg["password"])
            + " mysql -h "
            + shlex.quote(site_cfg["host"])
            + " -u "
            + shlex.quote(site_cfg["user"])
            + " -D "
            + shlex.quote(site_cfg["db"])
        )
        code, out, err = ssh_exec(ssh, clone_by_prefix_cmd)
        ensure_ok(code, err, "clone db by prefix")

    staging_config = posixpath.join(staging_root, "configuration.php")
    escaped_new_db = target_db.replace("'", "\\'")
    escaped_new_prefix = target_prefix.replace("'", "\\'")
    new_tmp = posixpath.join(staging_root, "tmp")
    new_log = posixpath.join(staging_root, "logs")

    code, out, err = ssh_exec(ssh, "chmod u+w " + shlex.quote(staging_config))
    ensure_ok(code, err, "chmod staging configuration writable")

    sftp = ssh.open_sftp()
    try:
        with sftp.open(staging_config, "r") as handle:
            config_text = handle.read().decode("utf-8", errors="ignore")

        config_text = re.sub(r"public\s+\$db\s*=\s*'[^']*';", "public $db = '" + escaped_new_db + "';", config_text, count=1)
        config_text = re.sub(r"public\s+\$dbprefix\s*=\s*'[^']*';", "public $dbprefix = '" + escaped_new_prefix + "';", config_text, count=1)
        config_text = re.sub(r"public\s+\$tmp_path\s*=\s*'[^']*';", "public $tmp_path = '" + new_tmp + "';", config_text, count=1)
        config_text = re.sub(r"public\s+\$log_path\s*=\s*'[^']*';", "public $log_path = '" + new_log + "';", config_text, count=1)
        config_text = re.sub(r"public\s+\$force_ssl\s*=\s*'[0-9]+';", "public $force_ssl = '0';", config_text, count=1)

        with sftp.open(staging_config, "w") as handle:
            handle.write(config_text)
    finally:
        sftp.close()

    verify_patch_cmd = (
        "php -r "
        + shlex.quote(
            "$f='"
            + staging_config
            + "';require $f;$c=new JConfig();"
            + "echo 'DB='.$c->db.PHP_EOL;"
            + "echo 'DBPREFIX='.$c->dbprefix.PHP_EOL;"
            + "echo 'FORCE_SSL='.$c->force_ssl.PHP_EOL;"
            + "echo 'TMP_PATH='.$c->tmp_path.PHP_EOL;"
            + "echo 'LOG_PATH='.$c->log_path.PHP_EOL;"
        )
    )
    code, out, err = ssh_exec(ssh, verify_patch_cmd)
    ensure_ok(code, err, "verify staging config")
    if (
        f"DB={target_db}" not in out
        or f"DBPREFIX={target_prefix}" not in out
        or "FORCE_SSL=0" not in out
        or f"TMP_PATH={new_tmp}" not in out
        or f"LOG_PATH={new_log}" not in out
    ):
        ssh.close()
        raise RuntimeError("staging configuration non allineata dopo patch")

    ssh_exec(ssh, "chmod 444 " + shlex.quote(staging_config))

    cache_clear_cmd = (
        "find "
        + shlex.quote(staging_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(staging_root + "/tmp")
        + " -type f ! -name index.html -delete"
    )
    code, out, err = ssh_exec(ssh, cache_clear_cmd)
    ensure_ok(code, err, "staging cache clear")

    ssh.close()
    print("STAGING_CLONE_OK")
    print("staging_root=", staging_root)
    print("staging_db=", target_db)
    print("staging_dbprefix=", target_prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
