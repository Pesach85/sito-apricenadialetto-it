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
    parser = argparse.ArgumentParser(description="Ripristina template produzione a JA Elastica")
    parser.add_argument("--apply", action="store_true", help="Esegue realmente il ripristino")
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
    ext_table = db_cfg["dbprefix"] + "extensions"

    q_ja = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND template='ja_elastica' ORDER BY id ASC LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_ja)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query style ja_elastica fallita: " + err.strip())
    rows = parse_table(out)
    if not rows:
        ssh.close()
        print("JA_STYLE_NOT_FOUND")
        return 2
    ja_style_id = rows[0][0]

    q_beez = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND template='beez_20' ORDER BY id ASC LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_beez)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query style beez_20 fallita: " + err.strip())
    beez_rows = parse_table(out)
    beez_style_id = beez_rows[0][0] if beez_rows else "4"

    q_count = (
        "SELECT COUNT(*) FROM "
        + menu_table
        + " WHERE client_id=0 AND template_style_id="
        + sql_int(beez_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, q_count)
    if code != 0:
        ssh.close()
        raise RuntimeError("Conteggio menu beez fallito: " + err.strip())
    count_rows = parse_table(out)
    menu_count = int(count_rows[0][0]) if count_rows and count_rows[0] else 0

    q_jat3 = (
        "SELECT extension_id,enabled FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_jat3)
    jat3_rows = parse_table(out) if code == 0 else []

    print("RESTORE_JA_PLAN")
    print("ja_style=", rows[0])
    print("beez_style_id=", beez_style_id)
    print("menu_items_on_beez=", menu_count)
    print("jat3_state=", jat3_rows[0] if jat3_rows else [])

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
        + sql_int(ja_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, up_styles)
    if code != 0:
        ssh.close()
        raise RuntimeError("Switch home style ja_elastica fallito: " + err.strip())

    up_menu = (
        "UPDATE "
        + menu_table
        + " SET template_style_id="
        + sql_int(ja_style_id)
        + " WHERE client_id=0 AND template_style_id="
        + sql_int(beez_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, up_menu)
    if code != 0:
        ssh.close()
        raise RuntimeError("Riallineamento menu style fallito: " + err.strip())

    up_jat3 = (
        "UPDATE "
        + ext_table
        + " SET enabled=1 WHERE type='plugin' AND folder='system' AND element='jat3'"
    )
    code, out, err = run_mysql(ssh, db_cfg, up_jat3)
    if code != 0:
        ssh.close()
        raise RuntimeError("Enable jat3 produzione fallito: " + err.strip())

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
        + " WHERE client_id=0 AND template_style_id="
        + sql_int(beez_style_id)
    )
    code, out, err = run_mysql(ssh, db_cfg, q_verify)
    if code != 0:
        ssh.close()
        raise RuntimeError("Verify ripristino fallito: " + err.strip())

    ssh.close()

    print("UPDATED_STATE")
    print(out.strip())
    print("RESTORE_JA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
