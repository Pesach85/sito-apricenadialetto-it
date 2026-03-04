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

$table = $config->dbprefix . 'template_overrides';

$existsRes = mysqli_query($mysqli, "SHOW TABLES LIKE '" . mysqli_real_escape_string($mysqli, $table) . "'");
$exists = $existsRes && mysqli_num_rows($existsRes) > 0;
if ($existsRes) {
    mysqli_free_result($existsRes);
}

if ($exists) {
    echo json_encode([
        'status' => 'NO_CHANGE',
        'table' => $table,
        'message' => 'Table already exists',
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
    mysqli_close($mysqli);
    exit(0);
}

$sql = "
CREATE TABLE IF NOT EXISTS `{$table}` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `template` varchar(50) NOT NULL DEFAULT '',
  `hash_id` varchar(255) NOT NULL DEFAULT '',
  `extension_id` int DEFAULT 0,
  `state` tinyint NOT NULL DEFAULT 0,
  `action` varchar(50) NOT NULL DEFAULT '',
  `client_id` tinyint unsigned NOT NULL DEFAULT 0,
  `created_date` datetime NOT NULL,
  `modified_date` datetime,
  PRIMARY KEY (`id`),
  KEY `idx_template` (`template`),
  KEY `idx_extension_id` (`extension_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 DEFAULT COLLATE=utf8mb4_unicode_ci
";

if (!mysqli_query($mysqli, $sql)) {
    fwrite(STDERR, 'CREATE TABLE failed: ' . mysqli_error($mysqli) . PHP_EOL);
    mysqli_close($mysqli);
    exit(4);
}

mysqli_close($mysqli);

echo json_encode([
    'status' => 'OK',
    'table' => $table,
    'message' => 'Created with Joomla 4 canonical schema',
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
