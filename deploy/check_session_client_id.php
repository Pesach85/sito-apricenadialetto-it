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

$table = $config->dbprefix . 'session';
$res = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
if (!$res) {
    fwrite(STDERR, mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}
$cols = [];
while ($row = mysqli_fetch_assoc($res)) {
    $cols[] = $row['Field'];
}
mysqli_free_result($res);
mysqli_close($mysqli);

echo json_encode(['table' => $table, 'columns' => $cols], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;
