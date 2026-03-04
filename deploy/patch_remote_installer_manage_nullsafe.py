from __future__ import annotations

import json
import os
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
REMOTE_PATH = "/home/w19158/public_html/administrator/components/com_installer/tmpl/manage/default.php"


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_patch(content: str) -> tuple[str, bool]:
    patched = content

    old_line_1 = "if ($item->locked || $item->protected)"
    new_line_1 = "if (!empty($item->locked) || !empty($item->protected))"
    if old_line_1 in patched:
        patched = patched.replace(old_line_1, new_line_1)

    old_line_2 = "if ($item->package_id !== null)"
    new_line_2 = "if (isset($item->package_id) && $item->package_id !== null)"
    if old_line_2 in patched:
        patched = patched.replace(old_line_2, new_line_2)

    old_line_3 = "echo JText::sprintf('COM_INSTALLER_PACKAGE_COLUMN', $item->package_id);"
    new_line_3 = "echo JText::sprintf('COM_INSTALLER_PACKAGE_COLUMN', $item->package_id ?? '');"
    if old_line_3 in patched:
        patched = patched.replace(old_line_3, new_line_3)

    old_line_4 = "<?php echo $item->package_id ?: '&#160;'; ?>"
    new_line_4 = "<?php echo isset($item->package_id) && $item->package_id ? $item->package_id : '&#160;'; ?>"
    if old_line_4 in patched:
        patched = patched.replace(old_line_4, new_line_4)

    old_line_5 = "<?php echo $item->locked ? Text::_('JYES') : Text::_('JNO'); ?>"
    new_line_5 = "<?php echo !empty($item->locked) ? Text::_('JYES') : Text::_('JNO'); ?>"
    if old_line_5 in patched:
        patched = patched.replace(old_line_5, new_line_5)

    return patched, patched != content


def main() -> int:
    cfg = load_sftp_config()
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg["privateKeyPath"]
    passphrase = cfg.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")

    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=30)

    sftp = ssh.open_sftp()
    with sftp.open(REMOTE_PATH, "r") as handle:
        content = handle.read().decode("utf-8", errors="ignore")

    patched, changed = apply_patch(content)
    if not changed:
        print("NO_CHANGE")
    else:
        backup_path = REMOTE_PATH + ".bak_nullsafe_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        sftp.posix_rename(REMOTE_PATH, backup_path)
        print("BACKUP_OK", backup_path)
        with sftp.open(REMOTE_PATH, "w") as handle:
            handle.write(patched)
        print("PATCH_APPLIED")

    sftp.close()

    cmd = f"php -l {REMOTE_PATH}"
    _, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    print(f"LINT_EXIT={code}")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

    ssh.close()
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
