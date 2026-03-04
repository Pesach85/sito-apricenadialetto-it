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

$table = $config->dbprefix . 'modules';

$keep = [
    'mod_login',
    'mod_menu',
    'mod_status',
    'mod_toolbar',
    'mod_title',
    'mod_submenu',
    'mod_custom',
];

$report = [
    'table' => $table,
    'kept' => $keep,
    'disabled' => [],
];

$listSql = "SELECT id,title,module,position,published,client_id FROM `{$table}` WHERE client_id=1 ORDER BY id ASC";
$listRes = mysqli_query($mysqli, $listSql);
$rows = [];
if ($listRes) {
    while ($row = mysqli_fetch_assoc($listRes)) {
        $rows[] = $row;
    }
    mysqli_free_result($listRes);
}

foreach ($rows as $row) {
    $module = (string) $row['module'];
    if (in_array($module, $keep, true)) {
        continue;
    }

    if ((int) $row['published'] === 0) {
        continue;
    }

    $id = (int) $row['id'];
    $sql = "UPDATE `{$table}` SET published=0 WHERE id={$id} LIMIT 1";
    $ok = mysqli_query($mysqli, $sql);

    $report['disabled'][] = [
        'id' => $id,
        'title' => $row['title'],
        'module' => $module,
        'ok' => (bool) $ok,
        'error' => $ok ? '' : mysqli_error($mysqli),
    ];
}

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
