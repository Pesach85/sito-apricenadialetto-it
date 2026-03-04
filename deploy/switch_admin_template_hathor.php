<?php

declare(strict_types=1);

require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();

$targetTemplate = $argv[1] ?? 'hathor';
$targetTemplate = trim((string) $targetTemplate);
if ($targetTemplate === '') {
    fwrite(STDERR, 'Target template cannot be empty' . PHP_EOL);
    exit(2);
}

$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    fwrite(STDERR, 'DB connection failed: ' . mysqli_connect_error() . PHP_EOL);
    exit(3);
}
mysqli_set_charset($mysqli, 'utf8mb4');

$table = $config->dbprefix . 'template_styles';

$findSql = 'SELECT id, template, title, home FROM `' . $table . '` WHERE client_id = 1 ORDER BY id ASC';
$res = mysqli_query($mysqli, $findSql);
if (!$res) {
    fwrite(STDERR, 'Query failed: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}

$styles = [];
$currentHomeId = null;
$targetId = null;

while ($row = mysqli_fetch_assoc($res)) {
    $styles[] = $row;
    if ((string) $row['home'] === '1') {
        $currentHomeId = (int) $row['id'];
    }
    if ((string) $row['template'] === $targetTemplate) {
        $targetId = (int) $row['id'];
    }
}
mysqli_free_result($res);

if ($targetId === null) {
    fwrite(STDERR, 'Target style not found in ' . $table . ' template=' . $targetTemplate . PHP_EOL);
    mysqli_close($mysqli);
    exit(5);
}

if ($currentHomeId === $targetId) {
    echo json_encode([
        'status' => 'NO_CHANGE',
        'message' => 'Target already active',
        'template' => $targetTemplate,
        'home_id' => $currentHomeId,
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
    mysqli_close($mysqli);
    exit(0);
}

if (!mysqli_query($mysqli, 'UPDATE `' . $table . '` SET home = 0 WHERE client_id = 1')) {
    fwrite(STDERR, 'Failed to reset admin home styles: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(6);
}

if (!mysqli_query($mysqli, 'UPDATE `' . $table . '` SET home = 1 WHERE id = ' . $targetId . ' AND client_id = 1')) {
    fwrite(STDERR, 'Failed to activate target style: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(7);
}

mysqli_close($mysqli);

echo json_encode([
    'status' => 'OK',
    'template' => $targetTemplate,
    'previous_home_id' => $currentHomeId,
    'new_home_id' => $targetId,
    'note' => 'Administrator template switched',
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
