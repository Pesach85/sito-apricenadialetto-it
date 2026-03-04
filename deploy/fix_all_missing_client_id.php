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

$schema = $config->db;
$prefix = $config->dbprefix;

$stmt = mysqli_prepare(
    $mysqli,
    "SELECT t.TABLE_NAME
     FROM INFORMATION_SCHEMA.TABLES t
     WHERE t.TABLE_SCHEMA = ?
       AND t.TABLE_NAME LIKE CONCAT(?, '%')
     ORDER BY t.TABLE_NAME"
);

if (!$stmt) {
    fwrite(STDERR, 'Prepare failed: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}

mysqli_stmt_bind_param($stmt, 'ss', $schema, $prefix);
mysqli_stmt_execute($stmt);
mysqli_stmt_bind_result($stmt, $tableName);

$tables = [];
while (mysqli_stmt_fetch($stmt)) {
    $tables[] = (string) $tableName;
}
mysqli_stmt_close($stmt);

$updated = [];
$skipped = [];
$errors = [];

foreach ($tables as $table) {
    $colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
    if (!$colsRes) {
        $errors[] = 'Cannot read columns for ' . $table . ': ' . mysqli_error($mysqli);
        continue;
    }

    $hasClientId = false;
    while ($row = mysqli_fetch_assoc($colsRes)) {
        if ((string) $row['Field'] === 'client_id') {
            $hasClientId = true;
            break;
        }
    }
    mysqli_free_result($colsRes);

    if ($hasClientId) {
        $skipped[] = $table;
        continue;
    }

    $alter = 'ALTER TABLE `' . $table . '` ADD COLUMN `client_id` TINYINT(3) UNSIGNED NOT NULL DEFAULT 0';
    if (!mysqli_query($mysqli, $alter)) {
        $errors[] = 'ALTER failed for ' . $table . ': ' . mysqli_error($mysqli);
        continue;
    }

    mysqli_query($mysqli, 'ALTER TABLE `' . $table . '` ADD INDEX `idx_client_id` (`client_id`)');
    $updated[] = $table;
}

mysqli_close($mysqli);

$report = [
    'schema' => $schema,
    'prefix' => $prefix,
    'updated_count' => count($updated),
    'updated_tables' => $updated,
    'skipped_count' => count($skipped),
    'errors_count' => count($errors),
    'errors' => $errors,
];

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
