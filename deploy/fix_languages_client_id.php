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
$table = $prefix . 'languages';

$report = [
    'table' => $table,
    'actions' => [],
];

$colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
if (!$colsRes) {
    fwrite(STDERR, 'Cannot read columns from ' . $table . ': ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}

$hasClientId = false;
while ($row = mysqli_fetch_assoc($colsRes)) {
    if (($row['Field'] ?? '') === 'client_id') {
        $hasClientId = true;
    }
}
mysqli_free_result($colsRes);

if (!$hasClientId) {
    $sql = 'ALTER TABLE `' . $table . '` ADD COLUMN `client_id` tinyint unsigned NOT NULL DEFAULT 0 AFTER `access`';
    $ok = mysqli_query($mysqli, $sql);
    $report['actions'][] = [
        'type' => 'add_client_id',
        'ok' => (bool) $ok,
        'error' => $ok ? '' : mysqli_error($mysqli),
    ];

    if (!$ok) {
        mysqli_close($mysqli);
        echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
        exit(5);
    }
}

$idxSql = 'ALTER TABLE `' . $table . '` ADD INDEX `idx_client_id` (`client_id`)';
$idxOk = @mysqli_query($mysqli, $idxSql);
$report['actions'][] = [
    'type' => 'add_idx_client_id',
    'ok' => (bool) $idxOk,
    'error' => $idxOk ? '' : mysqli_error($mysqli),
];

$setIt = "UPDATE `{$table}` SET client_id=0 WHERE lang_code='it-IT'";
$okIt = mysqli_query($mysqli, $setIt);
$report['actions'][] = [
    'type' => 'set_it_it_site',
    'ok' => (bool) $okIt,
    'affected' => mysqli_affected_rows($mysqli),
    'error' => $okIt ? '' : mysqli_error($mysqli),
];

$setEn = "UPDATE `{$table}` SET client_id=1 WHERE lang_code='en-GB'";
$okEn = mysqli_query($mysqli, $setEn);
$affectedEn = mysqli_affected_rows($mysqli);
$report['actions'][] = [
    'type' => 'set_en_gb_admin',
    'ok' => (bool) $okEn,
    'affected' => $affectedEn,
    'error' => $okEn ? '' : mysqli_error($mysqli),
];

$countAdminRes = mysqli_query($mysqli, "SELECT COUNT(*) AS c FROM `{$table}` WHERE client_id=1");
$adminCount = 0;
if ($countAdminRes) {
    $r = mysqli_fetch_assoc($countAdminRes);
    $adminCount = (int) ($r['c'] ?? 0);
    mysqli_free_result($countAdminRes);
}

if ($adminCount === 0) {
    $fallbackSql = "UPDATE `{$table}` SET client_id=1 ORDER BY lang_id ASC LIMIT 1";
    $okFallback = mysqli_query($mysqli, $fallbackSql);
    $report['actions'][] = [
        'type' => 'fallback_set_first_admin',
        'ok' => (bool) $okFallback,
        'affected' => mysqli_affected_rows($mysqli),
        'error' => $okFallback ? '' : mysqli_error($mysqli),
    ];
}

$finalRes = mysqli_query($mysqli, "SELECT lang_id, lang_code, title, published, access, client_id FROM `{$table}` ORDER BY client_id DESC, lang_id ASC");
$finalRows = [];
if ($finalRes) {
    while ($row = mysqli_fetch_assoc($finalRes)) {
        $finalRows[] = $row;
    }
    mysqli_free_result($finalRes);
}
$report['rows'] = $finalRows;

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
