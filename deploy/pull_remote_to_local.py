from __future__ import annotations

import argparse
import fnmatch
import json
import os
import posixpath
import shlex
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime

import paramiko


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(PROJECT_ROOT, ".vscode", "sftp.json")


@dataclass
class RemoteFile:
    rel_path: str
    size: int
    mtime: int


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_rel(path: str) -> str:
    value = path.replace("\\", "/").strip("/")
    return value


def is_ignored(rel_path: str, ignore_patterns: list[str]) -> bool:
    rel = normalize_rel(rel_path)
    if not rel:
        return False

    for raw in ignore_patterns:
        pattern = normalize_rel(raw)
        if not pattern:
            continue

        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if rel == prefix or rel.startswith(prefix + "/"):
                return True

        if fnmatch.fnmatch(rel, pattern):
            return True

        if "*" not in pattern and "?" not in pattern and "[" not in pattern:
            if rel == pattern or rel.startswith(pattern + "/"):
                return True

    return False


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return code, out, err


def list_remote_paths_via_find(ssh: paramiko.SSHClient, remote_root: str) -> list[RemoteFile]:
    cmd = "find " + shlex.quote(remote_root) + " -type f -printf '%s\\t%T@\\t%p\\n'"
    code, out, err = ssh_exec(ssh, cmd)
    if code != 0:
        raise RuntimeError(f"find remoto fallito: {err.strip() or out.strip()}")

    rows: list[RemoteFile] = []
    root_prefix = remote_root.rstrip("/") + "/"
    for line in out.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split("\t", 2)
        if len(parts) != 3:
            continue

        size_str, mtime_str, path = parts
        if path == remote_root.rstrip("/"):
            continue
        if path.startswith(root_prefix):
            rel = path[len(root_prefix) :]
        else:
            rel = path.lstrip("/")
        rel = normalize_rel(rel)
        if not rel:
            continue

        try:
            size = int(float(size_str))
            mtime = int(float(mtime_str))
        except ValueError:
            continue

        rows.append(RemoteFile(rel_path=rel, size=size, mtime=mtime))
    return rows


def walk_remote_files(
    ssh: paramiko.SSHClient,
    remote_root: str,
    ignore_patterns: list[str],
) -> list[RemoteFile]:
    collected: list[RemoteFile] = []
    remote_rows = list_remote_paths_via_find(ssh, remote_root)

    for index, item in enumerate(remote_rows, start=1):
        if is_ignored(item.rel_path, ignore_patterns):
            continue

        collected.append(item)

        if index % 2000 == 0:
            print(f"SCAN_PROGRESS scanned={index} kept={len(collected)}", flush=True)

    return collected


def create_backup_zip(local_root: str, rel_paths: list[str]) -> str | None:
    if not rel_paths:
        return None

    backup_dir = os.path.join(local_root, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"pull_backup_{stamp}.zip")

    with zipfile.ZipFile(backup_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in rel_paths:
            local_path = os.path.join(local_root, *rel.split("/"))
            if os.path.isfile(local_path):
                archive.write(local_path, arcname=rel)

    return backup_path


def same_file(local_path: str, remote_size: int, remote_mtime: int) -> bool:
    try:
        st = os.stat(local_path)
    except FileNotFoundError:
        return False

    local_size = int(st.st_size)
    local_mtime = int(st.st_mtime)

    if local_size != remote_size:
        return False

    return abs(local_mtime - remote_mtime) <= 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sincronizza file dal server al locale (solo pull) con backup automatico.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica davvero la sincronizzazione. Senza questo flag esegue solo anteprima.",
    )
    parser.add_argument(
        "--remote-root",
        default="",
        help="Override root remota. Default da .vscode/sftp.json -> remotePath",
    )
    parser.add_argument(
        "--local-root",
        default=PROJECT_ROOT,
        help="Cartella locale destinazione (default: root progetto).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
    remote_root = (args.remote_root.strip() or str(cfg["remotePath"]).strip()).rstrip("/")
    local_root = os.path.abspath(args.local_root)
    ignore_patterns = [str(item) for item in cfg.get("ignore", [])]

    print(f"CONNECT {host}:{port} user={username}", flush=True)
    print(f"REMOTE_ROOT={remote_root}", flush=True)
    print(f"LOCAL_ROOT={local_root}", flush=True)
    print(f"MODE={'APPLY' if args.apply else 'DRY_RUN'}", flush=True)

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    try:
        sftp = ssh.open_sftp()
        print("SCAN_START", flush=True)
        remote_files = walk_remote_files(ssh, remote_root, ignore_patterns)
        print("SCAN_DONE", flush=True)

        to_download: list[RemoteFile] = []
        to_backup: list[str] = []

        for item in remote_files:
            local_path = os.path.join(local_root, *item.rel_path.split("/"))
            if same_file(local_path, item.size, item.mtime):
                continue

            to_download.append(item)
            if os.path.isfile(local_path):
                to_backup.append(item.rel_path)

        print(f"REMOTE_FILES={len(remote_files)}")
        print(f"TO_DOWNLOAD={len(to_download)}")
        print(f"TO_BACKUP={len(to_backup)}")
        print(f"MODE={'APPLY' if args.apply else 'DRY_RUN'}", flush=True)

        if not to_download:
            print("SYNC_OK niente da aggiornare", flush=True)
            return 0

        if not args.apply:
            for item in to_download[:30]:
                print("PLAN", item.rel_path, flush=True)
            if len(to_download) > 30:
                print(f"PLAN ... +{len(to_download) - 30} file", flush=True)
            print("Anteprima completata. Esegui con --apply per scaricare realmente.", flush=True)
            return 0

        backup_zip = create_backup_zip(local_root, sorted(set(to_backup)))
        if backup_zip:
            print("BACKUP_OK", backup_zip, flush=True)

        for index, item in enumerate(to_download, start=1):
            if index % 1000 == 0:
                try:
                    sftp.close()
                except Exception:
                    pass
                sftp = ssh.open_sftp()

            remote_path = posixpath.join(remote_root, item.rel_path)
            local_path = os.path.join(local_root, *item.rel_path.split("/"))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            downloaded = False
            last_error: Exception | None = None
            for attempt in (1, 2, 3):
                try:
                    if attempt > 1:
                        try:
                            sftp.close()
                        except Exception:
                            pass
                        sftp = ssh.open_sftp()
                    sftp.get(remote_path, local_path)
                    downloaded = True
                    break
                except Exception as exc:
                    last_error = exc
                    print(f"WARN retry get {item.rel_path} attempt={attempt}: {exc}", flush=True)

            if not downloaded:
                raise RuntimeError(f"Download fallito per {item.rel_path}: {last_error}")

            os.utime(local_path, (item.mtime, item.mtime))
            if index <= 30:
                print("GET", item.rel_path, flush=True)
            elif index == 31:
                print(f"GET ... +{len(to_download) - 30} file", flush=True)

        print("SYNC_OK pull completato", flush=True)
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
