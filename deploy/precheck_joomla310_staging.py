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
            + "'host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'dbprefix'=>$c->dbprefix,"
            + "'force_ssl'=>$c->force_ssl,'tmp_path'=>$c->tmp_path,'log_path'=>$c->log_path"
            + ")));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Lettura config staging fallita: " + err.strip())
    return json.loads(base64.b64decode(out.strip()).decode("utf-8"))


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

    # PHP version
    code, out, err = ssh_exec(ssh, "php -r 'echo PHP_VERSION;' 2>/dev/null")
    php_version = out.strip() if code == 0 else ""
    report["checks"]["php_version"] = {
        "value": php_version,
        "ok": bool(php_version),
    }

    # Joomla short version on staging files
    joomla_version_cmd = (
        "php -r "
        + shlex.quote(
            "$f1='"
            + posixpath.join(staging_root, "libraries/cms/version/version.php")
            + "';"
            + "$f2='"
            + posixpath.join(staging_root, "libraries/joomla/version.php")
            + "';"
            + "if(file_exists($f1)){require $f1;}"
            + "elseif(file_exists($f2)){require $f2;}"
            + "else{echo 'MISSING'; exit(2);}"
            + "$v=new JVersion();"
            + "if(method_exists($v,'getShortVersion')){echo $v->getShortVersion();}"
            + "elseif(property_exists($v,'RELEASE')){echo $v->RELEASE.'.'.$v->DEV_LEVEL;}"
        )
    )
    code, out, err = ssh_exec(ssh, joomla_version_cmd)
    joomla_version = out.strip() if code == 0 else ""
    joomla_version_err = err.strip()

    if not joomla_version or joomla_version == "MISSING":
        xml_version_cmd = (
            "php -r "
            + shlex.quote(
                "$f='"
                + posixpath.join(staging_root, "administrator/manifests/files/joomla.xml")
                + "';"
                + "$x=@simplexml_load_file($f);"
                + "if($x && isset($x->version)){echo trim((string)$x->version);}"
            )
        )
        code2, out2, err2 = ssh_exec(ssh, xml_version_cmd)
        if code2 == 0 and out2.strip():
            joomla_version = out2.strip()
            joomla_version_err = err2.strip()
    report["checks"]["joomla_version"] = {
        "value": joomla_version,
        "ok": bool(joomla_version) and joomla_version != "MISSING",
        "stderr": joomla_version_err,
    }

    stg_cfg = get_staging_config(ssh, staging_root)
    report["checks"]["staging_config"] = {
        "db": stg_cfg["db"],
        "dbprefix": stg_cfg["dbprefix"],
        "force_ssl": str(stg_cfg["force_ssl"]),
        "tmp_path": stg_cfg["tmp_path"],
        "log_path": stg_cfg["log_path"],
        "ok": stg_cfg["dbprefix"].startswith("stg") and str(stg_cfg["force_ssl"]) == "0",
    }

    ext_table = stg_cfg["dbprefix"] + "extensions"
    ext_sql = (
        "SELECT type,element,folder,enabled FROM "
        + ext_table
        + " WHERE "
        + "(type='module' AND element='mod_itpfblikebox') OR "
        + "(type='plugin' AND folder='content' AND element='me_edocs') OR "
        + "(type='component' AND element='com_phocafavicon') OR "
        + "(type='plugin' AND folder='system' AND element='jat3') OR "
        + "(type='component' AND element='com_akeeba')"
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
        + shlex.quote(ext_sql)
    )
    code, out, err = ssh_exec(ssh, mysql_cmd)
    rows = parse_table(out) if code == 0 else []

    state = {}
    for row in rows:
        if len(row) < 4:
            continue
        ext_type, element, folder, enabled = row[:4]
        key = f"{ext_type}:{folder}:{element}"
        state[key] = enabled == "1"

    expected = {
        "module::mod_itpfblikebox": False,
        "plugin:content:me_edocs": False,
        "component::com_phocafavicon": False,
        "plugin:system:jat3": True,
    }

    ext_ok = True
    for key, expected_enabled in expected.items():
        if state.get(key) != expected_enabled:
            ext_ok = False

    report["checks"]["legacy_extension_state"] = {
        "state": state,
        "expected": expected,
        "ok": ext_ok,
    }

    # writable dirs
    writable_cmd = (
        "test -w "
        + shlex.quote(posixpath.join(staging_root, "cache"))
        + " && echo CACHE_OK || echo CACHE_FAIL; "
        + "test -w "
        + shlex.quote(posixpath.join(staging_root, "tmp"))
        + " && echo TMP_OK || echo TMP_FAIL"
    )
    code, out, err = ssh_exec(ssh, writable_cmd)
    writable_ok = "CACHE_OK" in out and "TMP_OK" in out
    report["checks"]["staging_writable"] = {
        "raw": out.strip(),
        "ok": writable_ok,
    }

    # GO / NO-GO for starting Joomla 3.10 migration on staging
    go = True
    go = go and report["checks"]["php_version"]["ok"]
    go = go and report["checks"]["joomla_version"]["ok"]
    go = go and report["checks"]["staging_config"]["ok"]
    go = go and report["checks"]["legacy_extension_state"]["ok"]
    go = go and report["checks"]["staging_writable"]["ok"]

    report["decision"] = {
        "status": "GO_J310_STAGING" if go else "NO_GO",
        "next_action": (
            "Procedere con aggiornamento Joomla 3.10 su staging"
            if go
            else "Correggere i check FAIL prima di aggiornare"
        ),
    }

    ssh.close()

    out_path = os.path.join(LOCAL_ROOT, "upgrade_backups", "staging_precheck_j310_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["decision"]["status"])
    print("report=", out_path)

    return 0 if go else 4


if __name__ == "__main__":
    raise SystemExit(main())
