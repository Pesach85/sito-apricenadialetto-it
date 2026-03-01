from __future__ import annotations

import argparse
import base64
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


def get_staging_config(ssh: paramiko.SSHClient, staging_root: str) -> dict:
    cfg_path = posixpath.join(staging_root, "configuration.php")
    php_cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + cfg_path
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array("
            + "'host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix"
            + ")));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Lettura config staging fallita: " + err.strip())
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
    parser = argparse.ArgumentParser(description="Disattiva estensioni legacy su staging (safe by default)")
    parser.add_argument("--apply", action="store_true", help="Esegue realmente le disattivazioni")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    parser.add_argument("--disable-akeeba", action="store_true", help="Disattiva anche com_akeeba in staging")
    args = parser.parse_args()

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

    db_cfg = get_staging_config(ssh, staging_root)
    prefix = db_cfg["dbprefix"]
    extensions = prefix + "extensions"
    modules = prefix + "modules"

    list_sql = (
        "SELECT type,element,folder,name,enabled FROM "
        + extensions
        + " WHERE "
        + "(type='module' AND element='mod_itpfblikebox') OR "
        + "(type='plugin' AND folder='content' AND element='me_edocs') OR "
        + "(type='component' AND element='com_phocafavicon') OR "
        + "(type='plugin' AND folder='system' AND element='jat3')"
    )
    if args.disable_akeeba:
        list_sql += " OR (type='component' AND element='com_akeeba')"
    code, out, err = run_mysql(ssh, db_cfg, list_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query estensioni fallita: " + err.strip())

    print("STAGING_DISABLE_PLAN")
    print("db=", db_cfg["db"])
    print("dbprefix=", prefix)
    print("target_disable: mod_itpfblikebox, me_edocs, com_phocafavicon")
    if args.disable_akeeba:
        print("target_disable_extra: com_akeeba")
    print("target_keep_enabled: jat3")
    print("CURRENT_STATE")
    print(out.strip())

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        ssh.close()
        return 3

    disable_ext_sql = (
        "UPDATE "
        + extensions
        + " SET enabled=0 WHERE "
        + "(type='module' AND element='mod_itpfblikebox') OR "
        + "(type='plugin' AND folder='content' AND element='me_edocs') OR "
        + "(type='component' AND element='com_phocafavicon')"
    )
    if args.disable_akeeba:
        disable_ext_sql += " OR (type='component' AND element='com_akeeba')"
    code, out, err = run_mysql(ssh, db_cfg, disable_ext_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Disable extensions failed: " + err.strip())

    disable_modules_sql = (
        "UPDATE "
        + modules
        + " SET published=0 WHERE module='mod_itpfblikebox'"
    )
    code, out, err = run_mysql(ssh, db_cfg, disable_modules_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Disable module instances failed: " + err.strip())

    verify_sql = (
        "SELECT type,element,folder,name,enabled FROM "
        + extensions
        + " WHERE "
        + "(type='module' AND element='mod_itpfblikebox') OR "
        + "(type='plugin' AND folder='content' AND element='me_edocs') OR "
        + "(type='component' AND element='com_phocafavicon') OR "
        + "(type='plugin' AND folder='system' AND element='jat3')"
    )
    if args.disable_akeeba:
        verify_sql += " OR (type='component' AND element='com_akeeba')"
    code, out, err = run_mysql(ssh, db_cfg, verify_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Verify query failed: " + err.strip())

    cache_clear_cmd = (
        "find "
        + shlex.quote(staging_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(staging_root + "/tmp")
        + " -type f ! -name index.html -delete"
    )
    code, out_cache, err_cache = ssh_exec(ssh, cache_clear_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("Cache clear staging failed: " + err_cache.strip())

    ssh.close()

    print("UPDATED_STATE")
    print(out.strip())
    print("STAGING_DISABLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
