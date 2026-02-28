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
    parser = argparse.ArgumentParser(description="Hotfix: abilita plugin JAT3 su produzione")
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

    ext_table = db_cfg["dbprefix"] + "extensions"
    check_sql = (
        "SELECT extension_id,enabled FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, check_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Query jat3 produzione fallita: " + err.strip())

    print("PROD_JAT3_STATE_BEFORE")
    print(out.strip())

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        ssh.close()
        return 0

    if args.confirm != "I_UNDERSTAND":
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        ssh.close()
        return 3

    enable_sql = (
        "UPDATE "
        + ext_table
        + " SET enabled=1 WHERE type='plugin' AND folder='system' AND element='jat3'"
    )
    code, out, err = run_mysql(ssh, db_cfg, enable_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Enable jat3 produzione fallito: " + err.strip())

    verify_sql = (
        "SELECT extension_id,enabled FROM "
        + ext_table
        + " WHERE type='plugin' AND folder='system' AND element='jat3' LIMIT 1"
    )
    code, out, err = run_mysql(ssh, db_cfg, verify_sql)
    if code != 0:
        ssh.close()
        raise RuntimeError("Verify jat3 produzione fallito: " + err.strip())

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

    ssh.close()

    print("PROD_JAT3_STATE_AFTER")
    print(out.strip())
    print("HOTFIX_PROD_JAT3_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
