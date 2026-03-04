<?php

declare(strict_types=1);

function parseArgs(array $argv): array
{
    $out = [];
    foreach ($argv as $i => $arg) {
        if ($i === 0) {
            continue;
        }
        if (strpos($arg, '--') !== 0) {
            continue;
        }
        $eqPos = strpos($arg, '=');
        if ($eqPos === false) {
            $key = substr($arg, 2);
            $out[$key] = true;
            continue;
        }
        $key = substr($arg, 2, $eqPos - 2);
        $val = substr($arg, $eqPos + 1);
        $out[$key] = $val;
    }
    return $out;
}

function randomPassword(int $length = 16): string
{
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
    $max = strlen($chars) - 1;
    $password = '';
    for ($i = 0; $i < $length; $i++) {
        $password .= $chars[random_int(0, $max)];
    }
    return $password;
}

$args = parseArgs($argv);

require dirname(__DIR__) . '/configuration.php';
$config = new JConfig();

$mysqli = @mysqli_connect($config->host, $config->user, $config->password, $config->db);
if (!$mysqli) {
    fwrite(STDERR, 'DB connection failed: ' . mysqli_connect_error() . PHP_EOL);
    exit(3);
}
mysqli_set_charset($mysqli, 'utf8mb4');

$prefix = $config->dbprefix;
$usersTable = $prefix . 'users';
$mapTable = $prefix . 'user_usergroup_map';
$extTable = $prefix . 'extensions';
$groupsTable = $prefix . 'usergroups';

$report = [
    'prefix' => $prefix,
    'groups' => [],
    'admin_candidates' => [],
    'super_users' => [],
    'plugins' => [],
    'actions' => [],
];

$userColumns = [];
$colsRes = mysqli_query($mysqli, "SHOW COLUMNS FROM {$usersTable}");
if ($colsRes) {
    while ($row = mysqli_fetch_assoc($colsRes)) {
        if (isset($row['Field'])) {
            $userColumns[$row['Field']] = true;
        }
    }
    mysqli_free_result($colsRes);
}

$groupsSql = "SELECT id,title,parent_id FROM {$groupsTable} ORDER BY id ASC";
$groupsRes = mysqli_query($mysqli, $groupsSql);
if ($groupsRes) {
    while ($row = mysqli_fetch_assoc($groupsRes)) {
        $report['groups'][] = $row;
    }
    mysqli_free_result($groupsRes);
}

$adminCandidatesSql = "SELECT DISTINCT u.id,u.name,u.username,u.email,u.block,m.group_id "
    . "FROM {$usersTable} u "
    . "INNER JOIN {$mapTable} m ON m.user_id = u.id "
    . "WHERE m.group_id IN (6,7,8) "
    . "ORDER BY u.id ASC, m.group_id ASC";
$adminCandidatesRes = mysqli_query($mysqli, $adminCandidatesSql);
if ($adminCandidatesRes) {
    while ($row = mysqli_fetch_assoc($adminCandidatesRes)) {
        $report['admin_candidates'][] = $row;
    }
    mysqli_free_result($adminCandidatesRes);
}

$superSql = "SELECT u.id,u.name,u.username,u.email,u.block,u.lastvisitDate "
    . "FROM {$usersTable} u "
    . "INNER JOIN {$mapTable} m ON m.user_id = u.id "
    . "WHERE m.group_id = 8 "
    . "ORDER BY u.id ASC";

$superRes = mysqli_query($mysqli, $superSql);
if ($superRes) {
    while ($row = mysqli_fetch_assoc($superRes)) {
        $report['super_users'][] = $row;
    }
    mysqli_free_result($superRes);
}

$pluginSql = "SELECT extension_id,folder,element,enabled "
    . "FROM {$extTable} "
    . "WHERE type='plugin' AND folder IN ('authentication','user') "
    . "ORDER BY folder, element";
$pluginRes = mysqli_query($mysqli, $pluginSql);
if ($pluginRes) {
    while ($row = mysqli_fetch_assoc($pluginRes)) {
        $report['plugins'][] = $row;
    }
    mysqli_free_result($pluginRes);
}

$enableCoreAuth = isset($args['enable-core-auth']);
if ($enableCoreAuth) {
    $updates = [
        "UPDATE {$extTable} SET enabled=1 WHERE type='plugin' AND folder='authentication' AND element='joomla'",
        "UPDATE {$extTable} SET enabled=1 WHERE type='plugin' AND folder='user' AND element='joomla'",
    ];
    foreach ($updates as $sql) {
        $ok = mysqli_query($mysqli, $sql);
        $report['actions'][] = [
            'type' => 'enable_core_auth',
            'sql' => $sql,
            'ok' => (bool) $ok,
            'affected' => mysqli_affected_rows($mysqli),
            'error' => $ok ? '' : mysqli_error($mysqli),
        ];
    }
}

$resetSuper = isset($args['reset-super']);
$promoteToSuper = isset($args['promote-to-super']);

if ($promoteToSuper) {
    $targetId = isset($args['user-id']) ? (int) $args['user-id'] : 0;
    $target = null;

    if ($targetId > 0) {
        foreach ($report['admin_candidates'] as $candidate) {
            if ((int) $candidate['id'] === $targetId) {
                $target = $candidate;
                break;
            }
        }
    }

    if (!$target && !empty($report['admin_candidates'])) {
        foreach ($report['admin_candidates'] as $candidate) {
            if ((int) $candidate['block'] === 0) {
                $target = $candidate;
                break;
            }
        }
    }

    if (!$target && !empty($report['admin_candidates'])) {
        $target = $report['admin_candidates'][0];
    }

    if (!$target) {
        $report['actions'][] = [
            'type' => 'promote_to_super',
            'ok' => false,
            'error' => 'No admin candidate found in groups 6/7/8',
        ];
    } else {
        $id = (int) $target['id'];
        $checkSql = "SELECT COUNT(*) AS c FROM {$mapTable} WHERE user_id={$id} AND group_id=8";
        $checkRes = mysqli_query($mysqli, $checkSql);
        $already = false;
        if ($checkRes) {
            $r = mysqli_fetch_assoc($checkRes);
            $already = ((int) ($r['c'] ?? 0) > 0);
            mysqli_free_result($checkRes);
        }

        if (!$already) {
            $insertSql = "INSERT INTO {$mapTable} (user_id, group_id) VALUES ({$id}, 8)";
            $ok = mysqli_query($mysqli, $insertSql);
            $report['actions'][] = [
                'type' => 'promote_to_super',
                'ok' => (bool) $ok,
                'user_id' => $id,
                'username' => $target['username'],
                'affected' => mysqli_affected_rows($mysqli),
                'error' => $ok ? '' : mysqli_error($mysqli),
            ];
        } else {
            $report['actions'][] = [
                'type' => 'promote_to_super',
                'ok' => true,
                'user_id' => $id,
                'username' => $target['username'],
                'affected' => 0,
                'error' => '',
                'note' => 'Already mapped to group_id=8',
            ];
        }
    }
}

if ($resetSuper) {
    $targetId = isset($args['user-id']) ? (int) $args['user-id'] : 0;
    $target = null;

    $superCandidates = [];
    if (!empty($report['super_users'])) {
        $superCandidates = $report['super_users'];
    } else {
        foreach ($report['admin_candidates'] as $candidate) {
            if ((int) $candidate['group_id'] === 8) {
                $superCandidates[] = $candidate;
            }
        }
    }

    if (!empty($superCandidates)) {
        if ($targetId > 0) {
            foreach ($superCandidates as $su) {
                if ((int) $su['id'] === $targetId) {
                    $target = $su;
                    break;
                }
            }
        }

        if (!$target) {
            foreach ($superCandidates as $su) {
                if ((int) $su['block'] === 0) {
                    $target = $su;
                    break;
                }
            }
        }

        if (!$target) {
            $target = $superCandidates[0];
        }
    }

    if (!$target) {
        $report['actions'][] = [
            'type' => 'reset_super',
            'ok' => false,
            'error' => 'No super user found in group_id=8',
        ];
    } else {
        $newPassword = isset($args['new-password']) && is_string($args['new-password']) && $args['new-password'] !== ''
            ? $args['new-password']
            : randomPassword(16);

        $hash = password_hash($newPassword, PASSWORD_BCRYPT);
        $id = (int) $target['id'];
        $setParts = [];
        $setParts[] = "password='" . mysqli_real_escape_string($mysqli, $hash) . "'";
        if (isset($userColumns['block'])) {
            $setParts[] = "block=0";
        }
        if (isset($userColumns['requireReset'])) {
            $setParts[] = "requireReset=0";
        }
        if (isset($userColumns['activation'])) {
            $setParts[] = "activation=''";
        }

        $sql = "UPDATE {$usersTable} SET " . implode(', ', $setParts) . " WHERE id={$id} LIMIT 1";
        $ok = mysqli_query($mysqli, $sql);

        $report['actions'][] = [
            'type' => 'reset_super',
            'ok' => (bool) $ok,
            'user_id' => $id,
            'username' => $target['username'],
            'new_password' => $newPassword,
            'error' => $ok ? '' : mysqli_error($mysqli),
        ];
    }
}

mysqli_close($mysqli);

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . PHP_EOL;
