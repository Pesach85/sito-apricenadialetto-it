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

$table = $config->dbprefix . 'content';

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

$columns = [];
$colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
if ($colsRes) {
    while ($row = mysqli_fetch_assoc($colsRes)) {
        $columns[(string) $row['Field']] = true;
    }
    mysqli_free_result($colsRes);
}

$changes = [];

if (!isset($columns['note'])) {
    $sql = 'ALTER TABLE `' . $table . '` ADD COLUMN `note` VARCHAR(255) NOT NULL DEFAULT \'' . '\'';
    if (!mysqli_query($mysqli, $sql)) {
        fwrite(STDERR, 'Failed to add note: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(5);
    }
    $changes[] = 'added note';
}

if (!isset($columns['client_id'])) {
    $sql = 'ALTER TABLE `' . $table . '` ADD COLUMN `client_id` TINYINT(3) UNSIGNED NOT NULL DEFAULT 0';
    if (!mysqli_query($mysqli, $sql)) {
        fwrite(STDERR, 'Failed to add client_id: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(6);
    }

    $idxSql = 'ALTER TABLE `' . $table . '` ADD INDEX `idx_client_id` (`client_id`)';
    if (!mysqli_query($mysqli, $idxSql)) {
        fwrite(STDERR, 'Warning: failed to add idx_client_id: ' . mysqli_error($mysqli) . PHP_EOL);
    }

    $changes[] = 'added client_id';
}

mysqli_close($mysqli);

echo 'TABLE=' . $table . PHP_EOL;
echo 'CHANGES=' . (empty($changes) ? 'none' : implode(', ', $changes)) . PHP_EOL;
