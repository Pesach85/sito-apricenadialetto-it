<?php

declare(strict_types=1);

define('_JEXEC', 1);
define('JPATH_BASE', dirname(__DIR__));
require JPATH_BASE . '/includes/defines.php';
require JPATH_BASE . '/includes/framework.php';

$db = JFactory::getDbo();
$ref = new ReflectionClass($db);

echo 'DB_CLASS=' . get_class($db) . PHP_EOL;
echo 'DB_FILE=' . $ref->getFileName() . PHP_EOL;
