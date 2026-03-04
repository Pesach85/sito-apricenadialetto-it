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
$extTable = $prefix . 'extensions';
$styleTable = $prefix . 'template_styles';

$result = [
    'extension' => null,
    'styles' => [],
];

$sqlExt = "SELECT extension_id, name, type, element, client_id, enabled, access, protected, manifest_cache, params, state FROM `{$extTable}` WHERE type='template' AND element='atum' AND client_id=1 LIMIT 1";
$resExt = mysqli_query($mysqli, $sqlExt);
if ($resExt) {
    $row = mysqli_fetch_assoc($resExt);
    if ($row) {
        $result['extension'] = $row;
    }
    mysqli_free_result($resExt);
}

$sqlStyles = "SELECT id, template, client_id, home, title FROM `{$styleTable}` WHERE template='atum' AND client_id=1 ORDER BY id ASC";
$resStyles = mysqli_query($mysqli, $sqlStyles);
if ($resStyles) {
    while ($row = mysqli_fetch_assoc($resStyles)) {
        $result['styles'][] = $row;
    }
    mysqli_free_result($resStyles);
}

mysqli_close($mysqli);

echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
