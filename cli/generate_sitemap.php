<?php
/**
 * Standalone sitemap generator (no Joomla framework bootstrap required).
 * Usage:
 *   php cli/generate_sitemap.php
 *   php cli/generate_sitemap.php --base-url=https://apricenadialetto.it
 */

if (array_key_exists('REQUEST_METHOD', $_SERVER)) {
    die();
}

require dirname(__DIR__) . '/configuration.php';

$config = new JConfig();

function arg_base_url()
{
    if (empty($_SERVER['argv']) || !is_array($_SERVER['argv'])) {
        return '';
    }

    foreach ($_SERVER['argv'] as $arg) {
        if (strpos($arg, '--base-url=') === 0) {
            return trim(substr($arg, strlen('--base-url=')));
        }
    }

    return '';
}

function format_lastmod(...$dates)
{
    foreach ($dates as $value) {
        $value = trim((string) $value);
        if ($value === '' || $value === '0000-00-00 00:00:00') {
            continue;
        }
        $ts = strtotime($value);
        if ($ts !== false) {
            return date('c', $ts);
        }
    }

    return date('c');
}

function absolute_url($baseUrl, $relative)
{
    return rtrim($baseUrl, '/') . '/' . ltrim((string) $relative, '/');
}

$baseUrl = arg_base_url();
if ($baseUrl === '') {
    $baseUrl = trim((string) $config->live_site);
}
if ($baseUrl === '') {
    $baseUrl = 'https://apricenadialetto.it';
}
$baseUrl = rtrim($baseUrl, '/');

$useMysqli = function_exists('mysqli_connect');
$usePdo = class_exists('PDO') && in_array('mysql', PDO::getAvailableDrivers(), true);

$mysqli = null;
$pdo = null;

if ($useMysqli) {
    $mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
    if ($mysqli) {
        mysqli_set_charset($mysqli, 'utf8mb4');
    }
}

if (!$mysqli && $usePdo) {
    try {
        $dsn = 'mysql:host=' . $config->host . ';dbname=' . $config->db . ';charset=utf8mb4';
        $pdo = new PDO($dsn, $config->user, $config->password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
    } catch (Exception $e) {
        $pdo = null;
    }
}

if (!$mysqli && !$pdo) {
    fwrite(STDERR, 'DB connection failed: enable mysqli or pdo_mysql extension in PHP CLI.' . PHP_EOL);
    exit(3);
}

$prefix = $config->dbprefix;

$urls = [];
$urls[] = [
    'loc' => $baseUrl . '/',
    'lastmod' => date('c'),
    'changefreq' => 'daily',
    'priority' => '1.0',
];

$menuSql = "
SELECT link, modified, publish_up
FROM `{$prefix}menu`
WHERE published = 1
  AND client_id = 0
  AND type = 'component'
  AND link <> ''
  AND link LIKE 'index.php%'
  AND link NOT LIKE 'index.php?option=com_users%'
";

if ($mysqli) {
    $menuResult = mysqli_query($mysqli, $menuSql);
    while ($menuResult && ($row = mysqli_fetch_assoc($menuResult))) {
        $urls[] = [
            'loc' => absolute_url($baseUrl, $row['link']),
            'lastmod' => format_lastmod($row['modified'], $row['publish_up']),
            'changefreq' => 'weekly',
            'priority' => '0.7',
        ];
    }
    if ($menuResult) {
        mysqli_free_result($menuResult);
    }
} elseif ($pdo) {
    foreach ($pdo->query($menuSql) as $row) {
        $urls[] = [
            'loc' => absolute_url($baseUrl, $row['link']),
            'lastmod' => format_lastmod($row['modified'], $row['publish_up']),
            'changefreq' => 'weekly',
            'priority' => '0.7',
        ];
    }
}

$contentSql = "
SELECT id, catid, modified, publish_up, created
FROM `{$prefix}content`
WHERE state = 1
  AND (publish_up = '0000-00-00 00:00:00' OR publish_up <= NOW())
  AND (publish_down = '0000-00-00 00:00:00' OR publish_down >= NOW())
";

if ($mysqli) {
    $contentResult = mysqli_query($mysqli, $contentSql);
    while ($contentResult && ($row = mysqli_fetch_assoc($contentResult))) {
        $link = 'index.php?option=com_content&view=article&id=' . (int) $row['id'];
        if ((int) $row['catid'] > 0) {
            $link .= '&catid=' . (int) $row['catid'];
        }

        $urls[] = [
            'loc' => absolute_url($baseUrl, $link),
            'lastmod' => format_lastmod($row['modified'], $row['publish_up'], $row['created']),
            'changefreq' => 'monthly',
            'priority' => '0.8',
        ];
    }
    if ($contentResult) {
        mysqli_free_result($contentResult);
    }
} elseif ($pdo) {
    foreach ($pdo->query($contentSql) as $row) {
        $link = 'index.php?option=com_content&view=article&id=' . (int) $row['id'];
        if ((int) $row['catid'] > 0) {
            $link .= '&catid=' . (int) $row['catid'];
        }

        $urls[] = [
            'loc' => absolute_url($baseUrl, $link),
            'lastmod' => format_lastmod($row['modified'], $row['publish_up'], $row['created']),
            'changefreq' => 'monthly',
            'priority' => '0.8',
        ];
    }
}

if ($mysqli) {
    mysqli_close($mysqli);
}

$seen = [];
$deduped = [];
foreach ($urls as $url) {
    if (isset($seen[$url['loc']])) {
        continue;
    }
    $seen[$url['loc']] = true;
    $deduped[] = $url;
}

$lines = [];
$lines[] = '<?xml version="1.0" encoding="UTF-8"?>';
$lines[] = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
foreach ($deduped as $url) {
    $lines[] = '  <url>';
    $lines[] = '    <loc>' . htmlspecialchars($url['loc'], ENT_QUOTES, 'UTF-8') . '</loc>';
    $lines[] = '    <lastmod>' . htmlspecialchars($url['lastmod'], ENT_QUOTES, 'UTF-8') . '</lastmod>';
    $lines[] = '    <changefreq>' . htmlspecialchars($url['changefreq'], ENT_QUOTES, 'UTF-8') . '</changefreq>';
    $lines[] = '    <priority>' . htmlspecialchars($url['priority'], ENT_QUOTES, 'UTF-8') . '</priority>';
    $lines[] = '  </url>';
}
$lines[] = '</urlset>';

$target = dirname(__DIR__) . '/sitemap.xml';
$xml = implode("\n", $lines) . "\n";

if (file_put_contents($target, $xml) === false) {
    fwrite(STDERR, 'ERROR: unable to write sitemap.xml' . PHP_EOL);
    exit(2);
}

echo 'SITEMAP_OK urls=' . count($deduped) . ' file=' . $target . PHP_EOL;
