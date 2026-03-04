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
$targets = [
    'menu',
    'modules',
    'extensions',
    'template_styles',
    'languages',
    'workflows',
    'workflow_stages',
    'workflow_transitions',
    'workflow_associations',
];

$report = [
    'prefix' => $prefix,
    'checks' => [],
];

foreach ($targets as $suffix) {
    $table = $prefix . $suffix;

    $existsRes = mysqli_query($mysqli, "SHOW TABLES LIKE '" . mysqli_real_escape_string($mysqli, $table) . "'");
    $exists = $existsRes && mysqli_num_rows($existsRes) > 0;
    if ($existsRes) {
        mysqli_free_result($existsRes);
    }

    if (!$exists) {
        $report['checks'][] = [
            'table' => $table,
            'exists' => false,
            'has_client_id' => false,
            'columns' => [],
        ];
        continue;
    }

    $colsRes = mysqli_query($mysqli, 'SHOW COLUMNS FROM `' . $table . '`');
    $cols = [];
    $hasClientId = false;

    if ($colsRes) {
        while ($row = mysqli_fetch_assoc($colsRes)) {
            $field = (string) ($row['Field'] ?? '');
            $cols[] = $field;
            if ($field === 'client_id') {
                $hasClientId = true;
            }
        }
        mysqli_free_result($colsRes);
    }

    $report['checks'][] = [
        'table' => $table,
        'exists' => true,
        'has_client_id' => $hasClientId,
        'columns' => $cols,
    ];
}

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
