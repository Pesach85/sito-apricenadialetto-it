from __future__ import annotations

import json
import os
import posixpath
import paramiko

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG = json.load(open(os.path.join(ROOT, ".vscode", "sftp.json"), encoding="utf-8"))
PASS = CFG.get("passphrase") or os.environ.get("SFTP_PASSPHRASE", "")
REMOTE_FILE = posixpath.join(CFG["remotePath"].rstrip("/"), "libraries/src/HTML/Helpers/Behavior.php")

NOFRAMES_METHOD = """
    /**
     * Backward compatibility helper for legacy administrator templates.
     *
     * @param   string  $location  Legacy location target (kept for signature compatibility).
     *
     * @return  void
     */
    public static function noframes($location = 'top.location.href')
    {
        if (isset(static::$loaded[__METHOD__])) {
            return;
        }

        Factory::getDocument()->addScriptDeclaration(
            "if (top.location != self.location) { top.location = self.location; }"
        );

        static::$loaded[__METHOD__] = true;
    }
"""

pkey = paramiko.RSAKey.from_private_key_file(CFG["privateKeyPath"], password=PASS)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CFG["host"], port=int(CFG.get("port", 22)), username=CFG["username"], pkey=pkey, timeout=25)
sftp = ssh.open_sftp()

try:
    with sftp.open(REMOTE_FILE, "r") as handle:
        content = handle.read().decode("utf-8", errors="ignore")

    if "function noframes(" in content:
        print("NOCHANGE already contains noframes")
    else:
        insert_at = content.rfind("}\n")
        if insert_at == -1:
            insert_at = content.rfind("}")
        if insert_at == -1:
            raise RuntimeError("Cannot find class closing brace in Behavior.php")

        patched = content[:insert_at] + NOFRAMES_METHOD + "\n" + content[insert_at:]

        with sftp.open(REMOTE_FILE, "w") as handle:
            handle.write(patched.encode("utf-8"))

        print("PATCH_OK", REMOTE_FILE)
finally:
    sftp.close()
    ssh.close()
