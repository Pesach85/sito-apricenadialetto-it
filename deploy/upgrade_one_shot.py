from __future__ import annotations

import argparse
import json
import os
import posixpath
import subprocess
import sys
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEPLOY_DIR = os.path.join(LOCAL_ROOT, "deploy")
BACKUPS_ROOT = os.path.join(LOCAL_ROOT, "upgrade_backups")
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_local_python(script_name: str, args: list[str]) -> tuple[int, str, str]:
    script_path = os.path.join(DEPLOY_DIR, script_name)
    cmd = [sys.executable, script_path] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def list_snapshots() -> list[str]:
    if not os.path.isdir(BACKUPS_ROOT):
        return []
    return sorted([x for x in os.listdir(BACKUPS_ROOT) if os.path.isdir(os.path.join(BACKUPS_ROOT, x))], reverse=True)


def latest_snapshot() -> str:
    snapshots = list_snapshots()
    if not snapshots:
        raise RuntimeError("Nessuno snapshot disponibile in upgrade_backups")
    return snapshots[0]


def load_manifest(snapshot: str) -> dict:
    manifest_path = os.path.join(BACKUPS_ROOT, snapshot, "backup_manifest.json")
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"Manifest non trovato: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ssh_exec(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return code, out, err


def run_preflight() -> dict:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    remote_root = cfg["remotePath"].rstrip("/")
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=25)

    checks: dict[str, dict] = {}

    cmds = {
        "php_version": "php -v | head -n 1",
        "disk_usage": f"df -h {posixpath.dirname(remote_root)} | tail -n 1",
        "cache_writable": f"test -w {remote_root}/cache && echo WRITABLE || echo NOT_WRITABLE",
        "tmp_writable": f"test -w {remote_root}/tmp && echo WRITABLE || echo NOT_WRITABLE",
        "joomla_config": f"test -f {remote_root}/configuration.php && echo OK || echo MISSING",
        "legacy_jat3": f"test -d {remote_root}/plugins/system/jat3 && echo PRESENT || echo ABSENT",
    }

    for key, cmd in cmds.items():
        code, out, err = ssh_exec(ssh, cmd)
        checks[key] = {
            "exit_code": code,
            "stdout": out.strip(),
            "stderr": err.strip(),
            "ok": code == 0,
        }

    ssh.close()
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="One-shot upgrade preparation (preflight + backup + rollback plan)")
    parser.add_argument("--snapshot", help="Usa snapshot esistente per il rollback plan")
    parser.add_argument("--skip-backup", action="store_true", help="Salta backup e usa --snapshot o ultimo snapshot")
    args = parser.parse_args()

    report: dict = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "steps": {},
    }

    print("STEP 1/3: preflight remoto")
    preflight = run_preflight()
    report["steps"]["preflight"] = preflight

    snapshot = args.snapshot

    if not args.skip_backup and not snapshot:
        print("STEP 2/3: backup guardrail")
        code, out, err = run_local_python("upgrade_guardrail_backup.py", [])
        report["steps"]["backup"] = {
            "exit_code": code,
            "stdout_tail": "\n".join(out.strip().splitlines()[-20:]),
            "stderr": err.strip(),
        }
        if code != 0:
            print(out)
            if err.strip():
                print(err)
            raise RuntimeError("Backup fallito: interrompo one-shot")
        snapshot = latest_snapshot()
    elif not snapshot:
        snapshot = latest_snapshot()

    print(f"STEP 3/3: rollback plan dry-run su snapshot {snapshot}")
    code, out, err = run_local_python("rollback_assist.py", ["--snapshot", snapshot])
    report["steps"]["rollback_plan"] = {
        "snapshot": snapshot,
        "exit_code": code,
        "stdout_tail": "\n".join(out.strip().splitlines()[-40:]),
        "stderr": err.strip(),
    }
    if code != 0:
        print(out)
        if err.strip():
            print(err)
        raise RuntimeError("Rollback dry-run fallito")

    manifest = load_manifest(snapshot)
    report["snapshot"] = snapshot
    report["manifest"] = manifest
    report["finished_at"] = datetime.now().isoformat(timespec="seconds")
    report["status"] = "ONE_SHOT_OK"

    report_path = os.path.join(BACKUPS_ROOT, snapshot, "upgrade_one_shot_report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print("ONE_SHOT_OK")
    print("snapshot:", snapshot)
    print("report:", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
