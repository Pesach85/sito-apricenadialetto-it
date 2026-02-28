<?php
require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();
$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    echo "DB_CONNECT_FAIL: " . mysqli_connect_error() . "\n";
    exit(2);
}
mysqli_set_charset($mysqli, 'utf8');

$table = $config->dbprefix . 'modules';
$sql = "SELECT id, title, module, position, published, params FROM `{$table}` WHERE module='mod_itpfblikebox'";
$res = mysqli_query($mysqli, $sql);
if (!$res) {
    echo "SQL_FAIL: " . mysqli_error($mysqli) . "\n";
    exit(3);
}

while ($row = mysqli_fetch_assoc($res)) {
    echo "ID={$row['id']} TITLE={$row['title']} POS={$row['position']} PUB={$row['published']}\n";
    echo "PARAMS={$row['params']}\n";
    echo "----\n";
}

mysqli_free_result($res);
mysqli_close($mysqli);
