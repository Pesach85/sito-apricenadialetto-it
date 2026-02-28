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

    db_cfg = get_staging_config(ssh, staging_root)
    prefix = db_cfg["dbprefix"]

    ext_table = prefix + "extensions"
    styles_table = prefix + "template_styles"
    menu_table = prefix + "menu"

    report: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "staging_root": staging_root,
        "db": db_cfg["db"],
        "dbprefix": prefix,
        "plugin_jat3": {},
        "template_home_style": {},
        "template_styles": [],
        "menu_default": {},
        "filesystem": {},
        "recommendation": "",
    }

    q_jat3 = (
        "SELECT extension_id,type,element,folder,enabled,name FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3'"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_jat3)
    rows = parse_table(out) if code == 0 else []
    if rows:
        r = rows[0]
        report["plugin_jat3"] = {
            "extension_id": r[0],
            "type": r[1],
            "element": r[2],
            "folder": r[3],
            "enabled": r[4] == "1",
            "name": r[5] if len(r) > 5 else "",
        }
    else:
        report["plugin_jat3"] = {"found": False, "enabled": False}

    q_home_style = (
        "SELECT id,template,title,home,client_id FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_home_style)
    rows = parse_table(out) if code == 0 else []
    if rows:
        r = rows[0]
        report["template_home_style"] = {
            "id": r[0],
            "template": r[1],
            "title": r[2],
            "home": r[3],
            "client_id": r[4],
        }

    q_styles = (
        "SELECT id,template,title,home,client_id FROM "
        + styles_table
        + " WHERE client_id=0 ORDER BY home DESC, id ASC"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_styles)
    rows = parse_table(out) if code == 0 else []
    styles = []
    for r in rows:
        if len(r) < 5:
            continue
        styles.append(
            {
                "id": r[0],
                "template": r[1],
                "title": r[2],
                "home": r[3],
                "client_id": r[4],
            }
        )
    report["template_styles"] = styles

    q_menu = (
        "SELECT id,title,link,template_style_id,home,published FROM "
        + menu_table
        + " WHERE home=1 AND client_id=0 LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, q_menu)
    rows = parse_table(out) if code == 0 else []
    if rows:
        r = rows[0]
        report["menu_default"] = {
            "id": r[0],
            "title": r[1],
            "link": r[2],
            "template_style_id": r[3],
            "home": r[4],
            "published": r[5],
        }

    fs_checks = {
        "jat3_plugin_dir": posixpath.join(staging_root, "plugins/system/jat3"),
        "jat3_lib_dir": posixpath.join(staging_root, "templates/ja_elastica"),
        "template_gratis_dir": posixpath.join(staging_root, "templates/gratis"),
        "template_ja_elastica_dir": posixpath.join(staging_root, "templates/ja_elastica"),
    }
    fs_result = {}
    for key, path in fs_checks.items():
        code, out, err = ssh_exec(ssh, f"test -d {shlex.quote(path)} && echo PRESENT || echo MISSING")
        fs_result[key] = out.strip() if out.strip() else "MISSING"
    report["filesystem"] = fs_result

    home_template = str(report.get("template_home_style", {}).get("template", ""))
    jat3_enabled = bool(report.get("plugin_jat3", {}).get("enabled", False))

    if jat3_enabled and home_template in {"ja_elastica", "gratis"}:
        report["recommendation"] = (
            "JAT3 risulta attivo con template legacy. Prima di Joomla 4: creare template style alternativo compatibile, "
            "assegnarlo come home, poi disattivare plg_system_jat3 e rieseguire precheck J4."
        )
    else:
        report["recommendation"] = "Dipendenza JAT3 non bloccante rilevata in forma ridotta."

    ssh.close()

    out_path = os.path.join(LOCAL_ROOT, "upgrade_backups", "staging_jat3_dependency_audit_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("JAT3_AUDIT_OK")
    print("report=", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
