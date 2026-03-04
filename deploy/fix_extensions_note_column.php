<?php

declare(strict_types=1);

require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();

$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    fwrite(STDERR, 'DB connection failed: ' . mysqli_connect_error() . PHP_EOL);
    exit(3);
}
mysqli_set_charset($mysqli, 'utf8mb4');

$table = $config->dbprefix . 'extensions';

$existsRes = mysqli_query($mysqli, "SHOW TABLES LIKE '" . mysqli_real_escape_string($mysqli, $table) . "'");
if (!$existsRes || mysqli_num_rows($existsRes) === 0) {
    fwrite(STDERR, 'Table not found: ' . $table . PHP_EOL);
    if ($existsRes) {
        mysqli_free_result($existsRes);
    }
    mysqli_close($mysqli);
    exit(4);
}
mysqli_free_result($existsRes);

$hasNote = false;
$colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
if ($colsRes) {
    while ($row = mysqli_fetch_assoc($colsRes)) {
        if ((string) ($row['Field'] ?? '') === 'note') {
            $hasNote = true;
            break;
        }
    }
    mysqli_free_result($colsRes);
}

if ($hasNote) {
    echo json_encode([
        'status' => 'NO_CHANGE',
        'table' => $table,
        'message' => 'note already exists',
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
    mysqli_close($mysqli);
    exit(0);
}

$sql = 'ALTER TABLE `' . $table . '` ADD COLUMN `note` VARCHAR(255) NOT NULL DEFAULT \'' . '\'';
if (!mysqli_query($mysqli, $sql)) {
    fwrite(STDERR, 'ALTER TABLE failed: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(5);
}

mysqli_close($mysqli);

echo json_encode([
    'status' => 'OK',
    'table' => $table,
    'message' => 'note column added',
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
