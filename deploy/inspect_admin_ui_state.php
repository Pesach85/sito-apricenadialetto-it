<?php

declare(strict_types=1);

error_reporting(E_ALL);
ini_set('display_errors', '1');

$root = dirname(__DIR__);
require_once $root . '/configuration.php';

$config = new JConfig();
$db = new mysqli($config->host, $config->user, $config->password, $config->db);

if ($db->connect_error) {
    fwrite(STDERR, 'DB_CONNECT_ERROR: ' . $db->connect_error . PHP_EOL);
    exit(1);
}

$prefix = $config->dbprefix;

echo "[ADMIN_TEMPLATE_STYLES]" . PHP_EOL;
$sql = "SELECT id, template, home, title FROM {$prefix}template_styles WHERE client_id = 1 ORDER BY home DESC, id ASC";
$res = $db->query($sql);
if (!$res) {
    fwrite(STDERR, 'SQL_ERROR_TEMPLATE: ' . $db->error . PHP_EOL);
    exit(2);
}
while ($row = $res->fetch_assoc()) {
    echo implode('|', [$row['id'], $row['template'], $row['home'], $row['title']]) . PHP_EOL;
}

echo "[ADMIN_TEMPLATE_ACTIVE_PARAMS]" . PHP_EOL;
$sql = "SELECT id, template, home, params FROM {$prefix}template_styles WHERE client_id = 1 AND home = 1 LIMIT 1";
$res = $db->query($sql);
if ($res && ($row = $res->fetch_assoc())) {
    echo implode('|', [$row['id'], $row['template'], $row['home']]) . PHP_EOL;
    echo (string) $row['params'] . PHP_EOL;
}

$positions = ['header', 'menu', 'title', 'toolbar', 'status', 'cpanel'];
$positionsIn = "'" . implode("','", $positions) . "'";

echo "[ADMIN_MODULES_CORE_POSITIONS]" . PHP_EOL;
$sql = "SELECT id, title, position, published, module FROM {$prefix}modules WHERE client_id = 1 AND position IN ({$positionsIn}) ORDER BY position ASC, id ASC";
$res = $db->query($sql);
if (!$res) {
    fwrite(STDERR, 'SQL_ERROR_MODULES: ' . $db->error . PHP_EOL);
    exit(3);
}
while ($row = $res->fetch_assoc()) {
    echo implode('|', [$row['id'], $row['title'], $row['position'], $row['published'], $row['module']]) . PHP_EOL;
}

$db->close();
