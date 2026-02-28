<?php
require __DIR__ . '/../configuration.php';

$config = new JConfig();
$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);

if (!$mysqli) {
    echo 'DB_CONNECT_FAIL: ' . mysqli_connect_error();
    exit(2);
}

echo 'DB_CONNECT_OK';
mysqli_close($mysqli);
