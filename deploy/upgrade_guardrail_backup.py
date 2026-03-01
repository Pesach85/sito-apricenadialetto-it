from __future__ import annotations

import base64
import hashlib
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
        cfg = json.load(handle)
    return cfg


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return code, out, err


def compute_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def get_db_config(ssh: paramiko.SSHClient, remote_root: str) -> dict:
    remote_config = posixpath.join(remote_root, "configuration.php")
    php_cmd = (
        "php -r "
        + shlex.quote(
            "require '"
            + remote_config
            + "';"
            + "$c=new JConfig();"
            + "echo base64_encode(json_encode(array("
            + "'host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db,'prefix'=>$c->dbprefix"
            + ")));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Impossibile leggere config DB da configuration.php: " + err.strip())
    raw = base64.b64decode(out.strip())
    return json.loads(raw.decode("utf-8"))


def main() -> int:
    cfg = load_sftp_config()

    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    remote_root = cfg["remotePath"].rstrip("/")
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_backup_root = posixpath.join("/home", username, "upgrade_backups", ts)
    remote_site_archive = posixpath.join(remote_backup_root, f"site_files_{ts}.tar.gz")
    remote_db_dump = posixpath.join(remote_backup_root, f"db_{ts}.sql.gz")

    local_backup_root = os.path.join(LOCAL_ROOT, "upgrade_backups", ts)
    os.makedirs(local_backup_root, exist_ok=True)
    local_site_archive = os.path.join(local_backup_root, os.path.basename(remote_site_archive))
    local_db_dump = os.path.join(local_backup_root, os.path.basename(remote_db_dump))

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    code, out, err = ssh_exec(ssh, "mkdir -p " + shlex.quote(remote_backup_root))
    if code != 0:
        raise RuntimeError("Impossibile creare cartella backup remota: " + err.strip())

    tar_cmd = (
        "tar --warning=no-file-changed -czf "
        + shlex.quote(remote_site_archive)
        + " -C "
        + shlex.quote(posixpath.dirname(remote_root))
        + " "
        + shlex.quote(posixpath.basename(remote_root))
    )
    code, out, err = ssh_exec(ssh, tar_cmd)
    if code != 0:
        raise RuntimeError("Backup file remoto fallito: " + err.strip())

    db_cfg = get_db_config(ssh, remote_root)
    dump_cmd = (
        "mysqldump --single-transaction --quick --routines --triggers "
        + "-h "
        + shlex.quote(db_cfg["host"])
        + " -u "
        + shlex.quote(db_cfg["user"])
        + " -p"
        + shlex.quote(db_cfg["password"])
        + " "
        + shlex.quote(db_cfg["db"])
        + " | gzip -9 > "
        + shlex.quote(remote_db_dump)
    )
    code, out, err = ssh_exec(ssh, dump_cmd)
    if code != 0:
        raise RuntimeError("Dump DB remoto fallito: " + err.strip())

    sftp = ssh.open_sftp()
    sftp.get(remote_site_archive, local_site_archive)
    sftp.get(remote_db_dump, local_db_dump)
    sftp.close()
    ssh.close()

    manifest = {
        "timestamp": ts,
        "remote_backup_root": remote_backup_root,
        "remote_site_archive": remote_site_archive,
        "remote_db_dump": remote_db_dump,
        "local_site_archive": local_site_archive,
        "local_db_dump": local_db_dump,
        "site_archive_sha256": compute_sha256(local_site_archive),
        "db_dump_sha256": compute_sha256(local_db_dump),
        "db_prefix": db_cfg.get("prefix", ""),
    }

    manifest_path = os.path.join(local_backup_root, "backup_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    print("BACKUP_OK")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
