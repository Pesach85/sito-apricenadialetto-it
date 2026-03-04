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

$prefix = $config->dbprefix;
$schema = $config->db;

$sql = "
SELECT t.TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES t
WHERE t.TABLE_SCHEMA = ?
  AND t.TABLE_NAME LIKE CONCAT(?, '%')
ORDER BY t.TABLE_NAME
";

$stmt = mysqli_prepare($mysqli, $sql);
if (!$stmt) {
    fwrite(STDERR, 'Prepare failed: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}
mysqli_stmt_bind_param($stmt, 'ss', $schema, $prefix);
mysqli_stmt_execute($stmt);
$tables = [];
mysqli_stmt_bind_result($stmt, $tableName);
while (mysqli_stmt_fetch($stmt)) {
    $tables[] = (string) $tableName;
}
mysqli_stmt_close($stmt);

$targets = ['client_id', 'note'];
$report = [
    'schema' => $schema,
    'prefix' => $prefix,
    'missing' => [
        'client_id' => [],
        'note' => [],
    ],
    'table_count' => count($tables),
];

foreach ($tables as $table) {
    $colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
    if (!$colsRes) {
        continue;
    }

    $cols = [];
    while ($col = mysqli_fetch_assoc($colsRes)) {
        $cols[(string) $col['Field']] = true;
    }
    mysqli_free_result($colsRes);

    foreach ($targets as $target) {
        if (!isset($cols[$target])) {
            $report['missing'][$target][] = $table;
        }
    }
}

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
