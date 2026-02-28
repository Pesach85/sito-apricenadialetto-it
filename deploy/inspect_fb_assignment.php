<?php
require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();
$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    echo "DB_CONNECT_FAIL: " . mysqli_connect_error() . "\n";
    exit(2);
}
mysqli_set_charset($mysqli, 'utf8');

$modulesTable = $config->dbprefix . 'modules';
$mapTable = $config->dbprefix . 'modules_menu';
$menuTable = $config->dbprefix . 'menu';

$sql = "
SELECT m.id, m.title, mm.menuid, mn.title AS menu_title, mn.link
FROM `{$modulesTable}` m
LEFT JOIN `{$mapTable}` mm ON mm.moduleid = m.id
LEFT JOIN `{$menuTable}` mn ON mn.id = mm.menuid
WHERE m.module='mod_itpfblikebox'
ORDER BY mm.menuid
";
$res = mysqli_query($mysqli, $sql);
if (!$res) {
    echo "SQL_FAIL: " . mysqli_error($mysqli) . "\n";
    exit(3);
}

while ($row = mysqli_fetch_assoc($res)) {
    $menuTitle = isset($row['menu_title']) ? $row['menu_title'] : '';
    $menuLink = isset($row['link']) ? $row['link'] : '';
    echo "ID={$row['id']} MENUID={$row['menuid']} MENU_TITLE={$menuTitle} LINK={$menuLink}\n";
}

mysqli_free_result($res);
mysqli_close($mysqli);
