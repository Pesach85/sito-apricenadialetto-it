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


def parse_semver(version: str) -> tuple[int, int, int]:
    parts = version.strip().split(".")
    nums = []
    for part in parts[:3]:
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def version_gte(current: str, minimum: str) -> bool:
    return parse_semver(current) >= parse_semver(minimum)


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


def get_joomla_version(ssh: paramiko.SSHClient, staging_root: str) -> str:
    joomla_version_cmd = (
        "php -r "
        + shlex.quote(
            "$f='"
            + posixpath.join(staging_root, "administrator/manifests/files/joomla.xml")
            + "';"
            + "$x=@simplexml_load_file($f);"
            + "if($x && isset($x->version)){echo trim((string)$x->version);}"
        )
    )
    code, out, err = ssh_exec(ssh, joomla_version_cmd)
    if code == 0 and out.strip():
        return out.strip()
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

    report: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "staging_root": staging_root,
        "checks": {},
    }

    code, out, err = ssh_exec(ssh, "php -r 'echo PHP_VERSION;' 2>/dev/null")
    php_version = out.strip() if code == 0 else ""
    php_ok = bool(php_version) and version_gte(php_version, "7.2.5")
    report["checks"]["php_version"] = {
        "value": php_version,
        "minimum_for_j4": "7.2.5",
        "ok": php_ok,
    }

    joomla_version = get_joomla_version(ssh, staging_root)
    joomla_ok = bool(joomla_version) and version_gte(joomla_version, "3.10.0")
    report["checks"]["joomla_version"] = {
        "value": joomla_version,
        "minimum_bridge": "3.10.0",
        "ok": joomla_ok,
    }

    stg_cfg = get_staging_config(ssh, staging_root)
    cfg_ok = stg_cfg["dbprefix"].startswith("stg") and str(stg_cfg["force_ssl"]) == "0"
    report["checks"]["staging_config"] = {
        "db": stg_cfg["db"],
        "dbprefix": stg_cfg["dbprefix"],
        "force_ssl": str(stg_cfg["force_ssl"]),
        "tmp_path": stg_cfg["tmp_path"],
        "log_path": stg_cfg["log_path"],
        "ok": cfg_ok,
    }

    ext_table = stg_cfg["dbprefix"] + "extensions"
    ext_sql = (
        "SELECT type,element,folder,enabled FROM "
        + ext_table
        + " WHERE "
        + "(type='module' AND element='mod_itpfblikebox') OR "
        + "(type='plugin' AND folder='content' AND element='me_edocs') OR "
        + "(type='component' AND element='com_phocafavicon') OR "
        + "(type='component' AND element='com_akeeba') OR "
        + "(type='plugin' AND folder='system' AND element='jat3')"
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

    state: dict[str, bool] = {}
    for row in rows:
        if len(row) < 4:
            continue
        ext_type, element, folder, enabled = row[:4]
        key = f"{ext_type}:{folder}:{element}"
        state[key] = enabled == "1"

    expected_for_j4 = {
        "module::mod_itpfblikebox": False,
        "plugin:content:me_edocs": False,
        "component::com_phocafavicon": False,
        "component::com_akeeba": False,
        "plugin:system:jat3": False,
    }

    ext_ok = True
    blockers: list[str] = []
    for key, expected_enabled in expected_for_j4.items():
        current = state.get(key)
        if current != expected_enabled:
            ext_ok = False
            blockers.append(f"{key} expected={int(expected_enabled)} got={int(current) if current is not None else 'MISSING'}")

    report["checks"]["legacy_extension_state_for_j4"] = {
        "state": state,
        "expected": expected_for_j4,
        "blockers": blockers,
        "ok": ext_ok,
    }

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

    go = php_ok and joomla_ok and cfg_ok and ext_ok and writable_ok
    report["decision"] = {
        "status": "GO_J4_STAGING" if go else "NO_GO_J4_STAGING",
        "next_action": (
            "Procedere con migrazione staging a Joomla 4"
            if go
            else "Correggere blocker: PHP staging >=7.2.5 e rimozione/sostituzione framework jat3"
        ),
    }

    ssh.close()

    out_path = os.path.join(LOCAL_ROOT, "upgrade_backups", "staging_precheck_j4_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["decision"]["status"])
    print("report=", out_path)

    return 0 if go else 4


if __name__ == "__main__":
    raise SystemExit(main())
