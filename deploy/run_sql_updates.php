<?php
if ($argc < 2) {
    fwrite(STDERR, "Usage: php run_sql_updates.php /path/to/file.sql\n");
    exit(1);
}

$sqlFile = $argv[1];
if (!is_file($sqlFile)) {
    fwrite(STDERR, "SQL file not found: {$sqlFile}\n");
    exit(2);
}

require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();

$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    fwrite(STDERR, "DB connection failed: " . mysqli_connect_error() . "\n");
    exit(3);
}
mysqli_set_charset($mysqli, 'utf8mb4');

$sql = file_get_contents($sqlFile);
$sql = str_replace('#__', $config->dbprefix, $sql);

$lines = preg_split('/\R/', $sql);
$buffer = '';
$executed = 0;

foreach ($lines as $line) {
    $trim = trim($line);
    if ($trim === '' || substr($trim, 0, 2) === '--') {
        continue;
    }

    $buffer .= $line . "\n";
    if (substr(rtrim($line), -1) === ';') {
        if (!mysqli_query($mysqli, $buffer)) {
            fwrite(STDERR, "SQL error: " . mysqli_error($mysqli) . "\nStatement:\n{$buffer}\n");
            mysqli_close($mysqli);
            exit(4);
        }
        $executed++;
        $buffer = '';
    }
}

if (trim($buffer) !== '') {
    if (!mysqli_query($mysqli, $buffer)) {
        fwrite(STDERR, "SQL error: " . mysqli_error($mysqli) . "\nStatement:\n{$buffer}\n");
        mysqli_close($mysqli);
        exit(5);
    }
    $executed++;
}

mysqli_close($mysqli);
echo "SQL_OK statements={$executed}\n";
