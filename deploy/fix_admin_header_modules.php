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

$updateSql = "UPDATE {$prefix}modules SET published = 1 WHERE client_id = 1 AND position = 'header' AND module IN ('mod_unread','mod_online')";
if (!$db->query($updateSql)) {
    fwrite(STDERR, 'SQL_UPDATE_ERROR: ' . $db->error . PHP_EOL);
    exit(2);
}

echo 'UPDATED_ROWS=' . $db->affected_rows . PHP_EOL;

echo "[HEADER_MODULES_STATUS]" . PHP_EOL;
$checkSql = "SELECT id, title, position, published, module FROM {$prefix}modules WHERE client_id = 1 AND position = 'header' ORDER BY id ASC";
$res = $db->query($checkSql);
if (!$res) {
    fwrite(STDERR, 'SQL_CHECK_ERROR: ' . $db->error . PHP_EOL);
    exit(3);
}

while ($row = $res->fetch_assoc()) {
    echo implode('|', [$row['id'], $row['title'], $row['position'], $row['published'], $row['module']]) . PHP_EOL;
}

$db->close();
