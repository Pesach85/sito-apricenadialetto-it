from __future__ import annotations

import json
import os
import posixpath
from datetime import datetime

import paramiko


LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFTP_CONFIG_PATH = os.path.join(LOCAL_ROOT, ".vscode", "sftp.json")
REMOTE_FILE = "/home/w19158/public_html/libraries/src/Editor/Editor.php"


def load_sftp_config() -> dict:
    with open(SFTP_CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


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

    with sftp.file(REMOTE_FILE, "r") as handle:
        content = handle.read().decode("utf-8", errors="ignore")

    target = "        $this->_editor->params->loadArray($config);"
    replacement = (
        "        if (!isset($this->_editor->params) || !$this->_editor->params instanceof \\Joomla\\Registry\\Registry) {\n"
        "            $this->_editor->params = new \\Joomla\\Registry\\Registry();\n"
        "        }\n\n"
        "        $this->_editor->params->loadArray($config);"
    )

    if replacement in content:
        print("ALREADY_PATCHED")
    elif target in content:
        patched = content.replace(target, replacement, 1)
        backup_path = REMOTE_FILE + ".bak_editor_params_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        sftp.posix_rename(REMOTE_FILE, backup_path)
        print("BACKUP_OK", backup_path)
        with sftp.file(REMOTE_FILE, "w") as handle:
            handle.write(patched.encode("utf-8"))
        print("PATCH_OK", REMOTE_FILE)
    else:
        print("TARGET_NOT_FOUND")
        sftp.close()
        ssh.close()
        return 2

    sftp.close()

    cmd = f"php -l {posixpath.join(REMOTE_FILE)}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
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
