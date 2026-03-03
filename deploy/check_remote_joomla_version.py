from __future__ import annotations

import json
import os
import paramiko

cfg = json.load(open('.vscode/sftp.json', 'r', encoding='utf-8'))
passphrase = cfg.get('passphrase') or os.environ.get('SFTP_PASSPHRASE', '')

pkey = paramiko.RSAKey.from_private_key_file(cfg['privateKeyPath'], password=passphrase)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(cfg['host'], port=int(cfg.get('port', 22)), username=cfg['username'], pkey=pkey, timeout=25)

remote_root = cfg['remotePath'].rstrip('/')

cmd_xml = (
    "php -r '"
    + '$f="' + remote_root + '/administrator/manifests/files/joomla.xml";'
    + '$x=@simplexml_load_file($f);'
    + 'if($x && isset($x->version)){echo trim((string)$x->version);} '
    + "'"
)

cmd_class = (
    "php -r '"
    + '$f="' + remote_root + '/libraries/cms/version/version.php";'
    + 'if(!file_exists($f)){echo "MISSING"; exit;} '
    + "define('_JEXEC',1);"
    + 'require $f;'
    + '$v=new JVersion();'
    + 'echo $v->RELEASE.".".$v->DEV_LEVEL;'
    + "'"
)

for name, cmd in [('REMOTE_JOOMLA_XML_VERSION', cmd_xml), ('REMOTE_JVERSION_CLASS', cmd_class)]:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    print(f"{name}={out} EXIT={code}")
    if err:
        print(f"{name}_ERR={err}")

cmd_j4 = (
    "php -r '"
    + '$f="' + remote_root + '/libraries/src/Version.php";'
    + 'if(!file_exists($f)){echo "J4_VERSION_FILE=MISSING"; exit;} '
    + 'require $f;'
    + 'echo "J4_VERSION_FILE=FOUND\n";'
    + 'echo "J4_CLASS_EXISTS=".(class_exists("Joomla\\CMS\\Version")?"YES":"NO")."\n";'
    + 'if(class_exists("Joomla\\CMS\\Version")){'
    + '$v=new Joomla\\CMS\\Version();'
    + 'echo "J4_VERSION_CLASS=".$v::MAJOR_VERSION.".".$v::MINOR_VERSION.".".$v::PATCH_VERSION;'
    + '}'
    + "'"
)

stdin, stdout, stderr = ssh.exec_command(cmd_j4)
code = stdout.channel.recv_exit_status()
out = stdout.read().decode('utf-8', errors='ignore').strip()
err = stderr.read().decode('utf-8', errors='ignore').strip()
print(f"REMOTE_J4_FILE_CHECK_EXIT={code}")
if out:
    print(out)
if err:
    print(f"REMOTE_J4_FILE_CHECK_ERR={err}")

shell_checks = [
    ("REMOTE_FILE_J4_SRC", f"test -f {remote_root}/libraries/src/Version.php && echo FOUND || echo MISSING"),
    ("REMOTE_FILE_LEGACY_VERSION", f"test -f {remote_root}/libraries/cms/version/version.php && echo FOUND || echo MISSING"),
    ("REMOTE_JOOMLA_XML_VERSION_LINE", f"grep -n '<version>' {remote_root}/administrator/manifests/files/joomla.xml"),
    ("REMOTE_LEGACY_RELEASE_LINE", f"grep -n 'RELEASE\\|DEV_LEVEL' {remote_root}/libraries/cms/version/version.php"),
]

for name, cmd in shell_checks:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    print(f"{name}_EXIT={code}")
    if out:
        print(out)
    if err:
        print(f"{name}_ERR={err}")

ssh.close()
