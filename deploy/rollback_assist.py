from __future__ import annotations

import argparse
import json
import os
import posixpath
import shlex
import sys

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
LOCAL_BACKUPS_ROOT = os.path.join(LOCAL_ROOT, "upgrade_backups")


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_local_snapshots() -> list[str]:
    if not os.path.isdir(LOCAL_BACKUPS_ROOT):
        return []
    return sorted(
        [name for name in os.listdir(LOCAL_BACKUPS_ROOT) if os.path.isdir(os.path.join(LOCAL_BACKUPS_ROOT, name))],
        reverse=True,
    )


def load_manifest(snapshot: str) -> tuple[str, dict]:
    snapshot_dir = os.path.join(LOCAL_BACKUPS_ROOT, snapshot)
    manifest_path = os.path.join(snapshot_dir, "backup_manifest.json")
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"Manifest non trovato: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    return snapshot_dir, manifest


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return code, out, err


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
            + "'host'=>$c->host,'user'=>$c->user,'password'=>$c->password,'db'=>$c->db"
            + ")));"
        )
    )
    code, out, err = ssh_exec(ssh, php_cmd)
    if code != 0 or not out.strip():
        raise RuntimeError("Impossibile leggere config DB: " + err.strip())

    import base64

    return json.loads(base64.b64decode(out.strip()).decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente rollback sito+DB da snapshot backup")
    parser.add_argument("--snapshot", help="Timestamp snapshot (es. 20260228_092042)")
    parser.add_argument("--list", action="store_true", help="Elenca snapshot locali disponibili")
    parser.add_argument("--apply", action="store_true", help="Esegue il rollback (altrimenti dry-run)")
    parser.add_argument("--confirm", default="", help="Conferma esplicita: I_UNDERSTAND")
    args = parser.parse_args()

    if args.list:
        snapshots = list_local_snapshots()
        if not snapshots:
            print("Nessuno snapshot trovato in upgrade_backups")
            return 0
        print("Snapshot disponibili:")
        for snapshot in snapshots:
            print("-", snapshot)
        return 0

    if not args.snapshot:
        print("Errore: specificare --snapshot oppure usare --list")
        return 2

    snapshot_dir, manifest = load_manifest(args.snapshot)
    local_site_archive = manifest["local_site_archive"]
    local_db_dump = manifest["local_db_dump"]
    remote_site_archive = manifest["remote_site_archive"]
    remote_db_dump = manifest["remote_db_dump"]
    remote_backup_root = manifest["remote_backup_root"]

    if not os.path.isfile(local_site_archive) or not os.path.isfile(local_db_dump):
        raise FileNotFoundError("File backup locale mancanti nello snapshot selezionato")

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    remote_root = cfg["remotePath"].rstrip("/")
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")

    print("ROLLBACK_PLAN")
    print(json.dumps({
        "snapshot": args.snapshot,
        "snapshot_dir": snapshot_dir,
        "remote_backup_root": remote_backup_root,
        "remote_site_archive": remote_site_archive,
        "remote_db_dump": remote_db_dump,
        "remote_root": remote_root,
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        print("DRY_RUN: aggiungi --apply --confirm I_UNDERSTAND per eseguire")
        return 0

    if args.confirm != "I_UNDERSTAND":
        print("Conferma mancante: usare --confirm I_UNDERSTAND")
        return 3

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    sftp = ssh.open_sftp()
    try:
        ssh_exec(ssh, "mkdir -p " + shlex.quote(remote_backup_root))
        sftp.put(local_site_archive, remote_site_archive)
        sftp.put(local_db_dump, remote_db_dump)
    finally:
        sftp.close()

    restore_files_cmd = (
        "find "
        + shlex.quote(remote_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(remote_root + "/tmp")
        + " -type f ! -name index.html -delete; "
        + "tar -xzf "
        + shlex.quote(remote_site_archive)
        + " -C "
        + shlex.quote(posixpath.dirname(remote_root))
    )
    code, out, err = ssh_exec(ssh, restore_files_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("Ripristino file fallito: " + err.strip())

    db_cfg = get_db_config(ssh, remote_root)
    restore_db_cmd = (
        "gzip -dc "
        + shlex.quote(remote_db_dump)
        + " | mysql -h "
        + shlex.quote(db_cfg["host"])
        + " -u "
        + shlex.quote(db_cfg["user"])
        + " -p"
        + shlex.quote(db_cfg["password"])
        + " "
        + shlex.quote(db_cfg["db"])
    )
    code, out, err = ssh_exec(ssh, restore_db_cmd)
    if code != 0:
        ssh.close()
        raise RuntimeError("Ripristino DB fallito: " + err.strip())

    code, out, err = ssh_exec(
        ssh,
        "find "
        + shlex.quote(remote_root + "/cache")
        + " -type f ! -name index.html -delete; "
        + "find "
        + shlex.quote(remote_root + "/tmp")
        + " -type f ! -name index.html -delete",
    )
    ssh.close()

    print("ROLLBACK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
