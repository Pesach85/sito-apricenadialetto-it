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


def sql_int(value: str) -> str:
    return str(int(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hotfix produzione: switch template fallback core")
    parser.add_argument("--target-template", default="beez_20", help="Template fallback da attivare")
    parser.add_argument("--apply", action="store_true", help="Esegue hotfix reale")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    args = parser.parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    cfg_path = posixpath.join(remote_root, "configuration.php")
    php_cfg_cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + cfg_path
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array('host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix)));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cfg_cmd)
    if code != 0 or not out.strip():
        ssh.close()
        raise RuntimeError("Lettura config produzione fallita: " + err.strip())
    db_cfg = json.loads(base64.b64decode(out.strip()).decode("utf-8"))

    styles_table = db_cfg["dbprefix"] + "template_styles"
    menu_table = db_cfg["dbprefix"] + "menu"

    q_current_home = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_current_home)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query home style produzione fallita: " + err.strip())
    current_home_rows = parse_table(out)

    q_target = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND template='"
        + args.target_template.replace("'", "''")
        + "' ORDER BY id ASC LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_target)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query target template produzione fallita: " + err.strip())
    target_rows = parse_table(out)
    if not target_rows:
        ssh.close()
        print("TARGET_STYLE_NOT_FOUND")
        print("template=", args.target_template)
        return 2

    target_style_id = target_rows[0][0]

    q_legacy_styles = (
        "SELECT id,template,title FROM "
        + styles_table
        + " WHERE client_id=0 AND (template='ja_elastica' OR template='gratis')"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_legacy_styles)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query legacy styles produzione fallita: " + err.strip())
    legacy_style_rows = parse_table(out)
    legacy_style_ids = [row[0] for row in legacy_style_rows if row and row[0] != target_style_id]

    legacy_menu_count = 0
    if legacy_style_ids:
        in_clause = ",".join(sql_int(style_id) for style_id in legacy_style_ids)
        q_legacy_menu_count = (
            "SELECT COUNT(*) FROM "
            + menu_table
            + " WHERE template_style_id IN ("
            + in_clause
            + ")"
        )
        code, out, err = run_mysql(ssh, db_cfg, q_legacy_menu_count)
        if code != 0:
            ssh.close()
            raise RuntimeError("Query legacy menu count produzione fallita: " + err.strip())
        rows = parse_table(out)
        if rows and rows[0]:
            legacy_menu_count = int(rows[0][0])

    print("PROD_TEMPLATE_HOTFIX_PLAN")
    print("current_home_style=", current_home_rows[0] if current_home_rows else [])
    print("target_style=", target_rows[0])
    print("legacy_style_ids=", legacy_style_ids)
    print("legacy_menu_items_to_rewire=", legacy_menu_count)

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
        + sql_int(target_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, up_styles)
    if code != 0:
        ssh.close()
        raise RuntimeError("Switch home style produzione fallito: " + err.strip())

    up_menu_home = (
        "UPDATE "
        + menu_table
        + " SET template_style_id="
        + sql_int(target_style_id)
        + " WHERE home=1 AND client_id=0"
    )
    code, out, err = run_mysql(ssh, db_cfg, up_menu_home)
    if code != 0:
        ssh.close()
        raise RuntimeError("Aggiornamento menu home produzione fallito: " + err.strip())

    if legacy_style_ids:
        in_clause = ",".join(sql_int(style_id) for style_id in legacy_style_ids)
        up_legacy_menu = (
            "UPDATE "
            + menu_table
            + " SET template_style_id="
            + sql_int(target_style_id)
            + " WHERE template_style_id IN ("
            + in_clause
            + ")"
        )
        code, out, err = run_mysql(ssh, db_cfg, up_legacy_menu)
        if code != 0:
            ssh.close()
            raise RuntimeError("Rewire menu legacy produzione fallito: " + err.strip())

    cache_clear_cmd = (
        "find "
        + shlex.quote(remote_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(remote_root + "/tmp")
        + " -type f ! -name index.html -delete"
    )
    code, out_cache, err_cache = ssh_exec(ssh, cache_clear_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("Cache clear produzione fallito: " + err_cache.strip())

    q_verify = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1' LIMIT 1; "
        + "SELECT COUNT(*) FROM "
        + menu_table
        + " WHERE template_style_id IN (SELECT id FROM "
        + styles_table
        + " WHERE client_id=0 AND (template='ja_elastica' OR template='gratis'))"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_verify)
    if code != 0:
        ssh.close()
        raise RuntimeError("Verify hotfix produzione fallito: " + err.strip())

    ssh.close()

    print("UPDATED_STATE")
    print(out.strip())
    print("HOTFIX_PROD_TEMPLATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
