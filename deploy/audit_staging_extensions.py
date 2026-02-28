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


def parse_manifest_version(raw_manifest: str) -> str:
    if not raw_manifest:
        return ""
    try:
        data = json.loads(raw_manifest)
        version = str(data.get("version", "")).strip()
        return version
    except Exception:
        return ""


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

    stg_cfg = get_staging_config(ssh, staging_root)
    extensions_table = stg_cfg["dbprefix"] + "extensions"

    query = (
        "SELECT type,element,folder,client_id,name,enabled,manifest_cache "
        "FROM " + extensions_table + " "
        "WHERE element IN ('com_akeeba','com_phocafavicon','me_edocs','mod_itpfblikebox','jat3') "
        "   OR (type='plugin' AND folder='content' AND element='me_edocs') "
        "   OR (type='module' AND element='mod_itpfblikebox') "
        "   OR (type='component' AND element IN ('com_akeeba','com_phocafavicon')) "
        "   OR (type='plugin' AND folder='system' AND element='jat3')"
    )

    mysql_cmd = (
        "MYSQL_PWD="
        + shlex.quote(stg_cfg["password"])
        + " mysql -N -B -h "
        + shlex.quote(stg_cfg["host"])
        + " -u "
        + shlex.quote(stg_cfg["user"])
        + " -D "
        + shlex.quote(stg_cfg["db"])
        + " -e "
        + shlex.quote(query)
    )

    code, out, err = ssh_exec(ssh, mysql_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query estensioni fallita: " + err.strip())

    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        ext_type, element, folder, client_id, name, enabled, manifest_cache = parts[:7]
        rows.append(
            {
                "type": ext_type,
                "element": element,
                "folder": folder,
                "client_id": client_id,
                "name": name,
                "enabled": enabled == "1",
                "version": parse_manifest_version(manifest_cache),
            }
        )

    checks = {
        "jat3_dir": "test -d " + shlex.quote(posixpath.join(staging_root, "plugins/system/jat3")) + " && echo PRESENT || echo ABSENT",
        "me_edocs_file": "test -f " + shlex.quote(posixpath.join(staging_root, "plugins/content/me_edocs/me_edocs.php")) + " && echo PRESENT || echo ABSENT",
        "itpfb_file": "test -f " + shlex.quote(posixpath.join(staging_root, "modules/mod_itpfblikebox/mod_itpfblikebox.php")) + " && echo PRESENT || echo ABSENT",
    }

    fs_checks: dict[str, str] = {}
    for key, command in checks.items():
        c, o, e = ssh_exec(ssh, command)
        fs_checks[key] = (o.strip() or e.strip() or "UNKNOWN")

    ssh.close()

    risk_rules = {
        "com_akeeba": "ALTA",
        "com_phocafavicon": "ALTA",
        "me_edocs": "ALTA",
        "mod_itpfblikebox": "ALTA",
        "jat3": "CRITICA",
    }

    actions = {
        "com_akeeba": "Sostituire con Akeeba compatibile Joomla 3.10+ o rimuovere in staging",
        "com_phocafavicon": "Valutare rimozione e gestione favicon via template",
        "me_edocs": "Disattivare plugin e sostituire embed documenti con metodo compatibile",
        "mod_itpfblikebox": "Disattivare modulo legacy, usare solo link/pulsante social",
        "jat3": "Pianificare migrazione template/framework prima di salto Joomla 4/5",
    }

    report_rows = []
    for row in rows:
        key = row["element"]
        risk = risk_rules.get(key, "MEDIA")
        report_rows.append(
            {
                **row,
                "risk": risk,
                "recommended_action": actions.get(key, "Verifica manuale"),
            }
        )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "staging_root": staging_root,
        "staging_db": stg_cfg["db"],
        "staging_dbprefix": stg_cfg["dbprefix"],
        "filesystem_checks": fs_checks,
        "extensions": report_rows,
        "status": "AUDIT_OK",
    }

    out_dir = os.path.join(LOCAL_ROOT, "upgrade_backups")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "staging_extension_audit_latest.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("AUDIT_OK")
    print("report=", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
