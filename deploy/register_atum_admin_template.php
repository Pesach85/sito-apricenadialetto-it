<?php

declare(strict_types=1);

require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();

$activate = true;
if (isset($argv[1])) {
    $value = strtolower(trim((string) $argv[1]));
    $activate = !in_array($value, ['0', 'false', 'no', 'off'], true);
}

$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    fwrite(STDERR, 'DB connection failed: ' . mysqli_connect_error() . PHP_EOL);
    exit(3);
}
mysqli_set_charset($mysqli, 'utf8mb4');

$prefix = $config->dbprefix;
$extTable = $prefix . 'extensions';
$styleTable = $prefix . 'template_styles';

function tableColumns(mysqli $db, string $table): array
{
    $res = mysqli_query($db, 'SHOW COLUMNS FROM `' . $table . '`');
    if (!$res) {
        return [];
    }

    $cols = [];
    while ($row = mysqli_fetch_assoc($res)) {
        $cols[] = (string) $row['Field'];
    }
    mysqli_free_result($res);
    return $cols;
}

function quoteValue(mysqli $db, $value): string
{
    if ($value === null) {
        return 'NULL';
    }
    if (is_int($value) || is_float($value)) {
        return (string) $value;
    }
    return "'" . mysqli_real_escape_string($db, (string) $value) . "'";
}

function insertDynamic(mysqli $db, string $table, array $availableColumns, array $values): bool
{
    $fields = [];
    $vals = [];

    foreach ($values as $key => $val) {
        if (!in_array($key, $availableColumns, true)) {
            continue;
        }
        $fields[] = '`' . $key . '`';
        $vals[] = quoteValue($db, $val);
    }

    if (empty($fields)) {
        return false;
    }

    $sql = 'INSERT INTO `' . $table . '` (' . implode(', ', $fields) . ') VALUES (' . implode(', ', $vals) . ')';
    return mysqli_query($db, $sql) !== false;
}

$extCols = tableColumns($mysqli, $extTable);
$styleCols = tableColumns($mysqli, $styleTable);

$report = [
    'activate' => $activate,
    'extension_inserted' => false,
    'style_inserted' => false,
    'activated' => false,
    'extension_id' => null,
    'style_id' => null,
];

$extRes = mysqli_query(
    $mysqli,
    "SELECT extension_id FROM `{$extTable}` WHERE type='template' AND element='atum' AND client_id=1 LIMIT 1"
);

$extensionId = null;
if ($extRes) {
    $row = mysqli_fetch_assoc($extRes);
    if ($row) {
        $extensionId = (int) $row['extension_id'];
    }
    mysqli_free_result($extRes);
}

if ($extensionId === null) {
    $manifestPath = dirname(__DIR__) . '/administrator/templates/atum/templateDetails.xml';
    $manifestCache = '';

    if (is_file($manifestPath)) {
        $xml = @simplexml_load_file($manifestPath);
        if ($xml) {
            $manifestCache = json_encode([
                'name' => (string) ($xml->name ?? 'atum'),
                'type' => 'template',
                'creationDate' => (string) ($xml->creationDate ?? ''),
                'author' => (string) ($xml->author ?? ''),
                'version' => (string) ($xml->version ?? ''),
            ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?: '';
        }
    }

    $ok = insertDynamic($mysqli, $extTable, $extCols, [
        'package_id' => 0,
        'name' => 'tpl_atum',
        'type' => 'template',
        'element' => 'atum',
        'folder' => '',
        'client_id' => 1,
        'enabled' => 1,
        'access' => 1,
        'protected' => 0,
        'manifest_cache' => $manifestCache,
        'params' => '',
        'custom_data' => '',
        'system_data' => '',
        'checked_out' => 0,
        'checked_out_time' => '0000-00-00 00:00:00',
        'ordering' => 0,
        'state' => 0,
    ]);

    if (!$ok) {
        fwrite(STDERR, 'Failed to insert atum extension: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(4);
    }

    $extensionId = (int) mysqli_insert_id($mysqli);
    $report['extension_inserted'] = true;
}

$report['extension_id'] = $extensionId;

$styleRes = mysqli_query(
    $mysqli,
    "SELECT id FROM `{$styleTable}` WHERE template='atum' AND client_id=1 ORDER BY id ASC LIMIT 1"
);

$styleId = null;
if ($styleRes) {
    $row = mysqli_fetch_assoc($styleRes);
    if ($row) {
        $styleId = (int) $row['id'];
    }
    mysqli_free_result($styleRes);
}

if ($styleId === null) {
    $ok = insertDynamic($mysqli, $styleTable, $styleCols, [
        'template' => 'atum',
        'client_id' => 1,
        'home' => 0,
        'title' => 'Atum - Default',
        'params' => '',
        'parent' => '',
        'inheritable' => 0,
    ]);

    if (!$ok) {
        fwrite(STDERR, 'Failed to insert atum style: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(5);
    }

    $styleId = (int) mysqli_insert_id($mysqli);
    $report['style_inserted'] = true;
}

$report['style_id'] = $styleId;

if ($activate) {
    if (!mysqli_query($mysqli, "UPDATE `{$styleTable}` SET home = 0 WHERE client_id = 1")) {
        fwrite(STDERR, 'Failed to reset admin home styles: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(6);
    }

    if (!mysqli_query($mysqli, "UPDATE `{$styleTable}` SET home = 1 WHERE id = {$styleId} AND client_id = 1")) {
        fwrite(STDERR, 'Failed to activate atum style: ' . mysqli_error($mysqli) . PHP_EOL);
        mysqli_close($mysqli);
        exit(7);
    }

    $report['activated'] = true;
}

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
