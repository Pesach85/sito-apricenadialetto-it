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


def parse_table(raw: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


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


def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Distacca JAT3 su staging con switch template home")
    parser.add_argument("--target-template", default="beez_20", help="Template da impostare come home style")
    parser.add_argument("--apply", action="store_true", help="Esegue realmente le modifiche")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
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
    ext_table = prefix + "extensions"
    styles_table = prefix + "template_styles"
    menu_table = prefix + "menu"

    q_current_home = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_current_home)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query home style fallita: " + err.strip())
    current_rows = parse_table(out)

    q_target = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND template="
        + sql_str(args.target_template)
        + " ORDER BY id ASC LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_target)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query target style fallita: " + err.strip())
    target_rows = parse_table(out)
    if not target_rows:
        ssh.close()
        print("TARGET_STYLE_NOT_FOUND")
        print("template=", args.target_template)
        return 2

    target_style_id = target_rows[0][0]

    q_jat3 = (
        "SELECT extension_id,enabled FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_jat3)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query jat3 fallita: " + err.strip())
    jat3_rows = parse_table(out)
    jat3_enabled = bool(jat3_rows and len(jat3_rows[0]) > 1 and jat3_rows[0][1] == "1")

    print("DETACH_JAT3_PLAN")
    print("current_home_style=", current_rows[0] if current_rows else [])
    print("target_template=", args.target_template)
    print("target_style=", target_rows[0])
    print("jat3_enabled=", jat3_enabled)

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        ssh.close()
        return 3

    up_styles = (
        "UPDATE "
        + styles_table
        + " SET home='0' WHERE client_id=0; "
        + "UPDATE "
        + styles_table
        + " SET home='1' WHERE id="
        + sql_str(target_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, up_styles)
    if code != 0:
        ssh.close()
        raise RuntimeError("Switch home style fallito: " + err.strip())

    up_menu = (
        "UPDATE "
        + menu_table
        + " SET template_style_id="
        + sql_str(target_style_id)
        + " WHERE home=1 AND client_id=0"
    )
    code, out, err = run_mysql(ssh, db_cfg, up_menu)
    if code != 0:
        ssh.close()
        raise RuntimeError("Aggiornamento menu home fallito: " + err.strip())

    up_jat3 = (
        "UPDATE "
        + ext_table
        + " SET enabled=0 WHERE type='plugin' AND folder='system' AND element='jat3'"
    )
    code, out, err = run_mysql(ssh, db_cfg, up_jat3)
    if code != 0:
        ssh.close()
        raise RuntimeError("Disable jat3 fallito: " + err.strip())

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
        raise RuntimeError("Cache clear staging fallito: " + err_cache.strip())

    q_verify = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1' LIMIT 1; "
        + "SELECT extension_id,enabled FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_verify)
    if code != 0:
        ssh.close()
        raise RuntimeError("Verify fallito: " + err.strip())

    ssh.close()

    print("UPDATED_STATE")
    print(out.strip())
    print("DETACH_JAT3_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
