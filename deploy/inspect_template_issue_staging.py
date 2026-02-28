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


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect template routing issue for staging or production")
    parser.add_argument("--target", choices=["staging", "production"], default="staging")
    args = parser.parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = cfg["remotePath"].rstrip("/")
    site_root = remote_root + "_staging" if args.target == "staging" else remote_root

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    cfg_path = posixpath.join(site_root, "configuration.php")
    php_cfg_cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + cfg_path
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array('host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix,'template'=>$c->template)));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cfg_cmd)
    if code != 0 or not out.strip():
        ssh.close()
        raise RuntimeError("Lettura configuration.php fallita: " + err.strip())
    db_cfg = json.loads(base64.b64decode(out.strip()).decode("utf-8"))

    styles_table = db_cfg["dbprefix"] + "template_styles"
    menu_table = db_cfg["dbprefix"] + "menu"
    content_table = db_cfg["dbprefix"] + "content"
    categories_table = db_cfg["dbprefix"] + "categories"

    q_home_style = (
        "SELECT id,template,title,home FROM "
        + styles_table
        + " WHERE client_id=0 AND home='1'"
    )
    q_home_menu = (
        "SELECT id,title,link,access,published,template_style_id FROM "
        + menu_table
        + " WHERE home=1 AND client_id=0 LIMIT 1"
    )
    q_legacy_menu = (
        "SELECT id,title,link,template_style_id FROM "
        + menu_table
        + " WHERE template_style_id IN (SELECT id FROM "
        + styles_table
        + " WHERE client_id=0 AND (template='ja_elastica' OR template='gratis'))"
    )

    code, out, err = run_mysql(ssh, db_cfg, q_home_style)
    home_rows = parse_table(out) if code == 0 else []

    code, out, err = run_mysql(ssh, db_cfg, q_legacy_menu)
    legacy_menu_rows = parse_table(out) if code == 0 else []

    code, out, err = run_mysql(ssh, db_cfg, q_home_menu)
    home_menu_rows = parse_table(out) if code == 0 else []

    code, out, err = ssh_exec(
        ssh,
        "grep -n 'public $template' " + shlex.quote(cfg_path) + " || true",
    )
    template_line = out.strip()

    report = {
        "target": args.target,
        "site_root": site_root,
        "config_template": db_cfg.get("template", ""),
        "config_template_line": template_line,
        "home_styles": home_rows,
        "home_menu": home_menu_rows,
        "home_article": [],
        "home_category": [],
        "legacy_menu_assignments": legacy_menu_rows,
        "legacy_menu_count": len(legacy_menu_rows),
    }

    if home_menu_rows and len(home_menu_rows[0]) >= 3:
        home_link = home_menu_rows[0][2]
        match = re.search(r"id=(\d+)", home_link)
        if match:
            article_id = match.group(1)
            q_home_article = (
                "SELECT id,title,state,access,catid FROM "
                + content_table
                + " WHERE id="
                + article_id
                + " LIMIT 1"
            )
            code, out, err = run_mysql(ssh, db_cfg, q_home_article)
            if code == 0:
                article_rows = parse_table(out)
                report["home_article"] = article_rows
                if article_rows and len(article_rows[0]) >= 5:
                    catid = article_rows[0][4]
                    q_home_category = (
                        "SELECT id,title,published,access FROM "
                        + categories_table
                        + " WHERE id="
                        + catid
                        + " LIMIT 1"
                    )
                    code2, out2, err2 = run_mysql(ssh, db_cfg, q_home_category)
                    if code2 == 0:
                        report["home_category"] = parse_table(out2)

    ssh.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
