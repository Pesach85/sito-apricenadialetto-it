<?php

defined('_JEXEC') or define('_JEXEC', 1);

if (!class_exists('JRequest')) {
	class JRequest
	{
		protected static function getInput()
		{
			if (class_exists('Joomla\\CMS\\Factory')) {
				$app = call_user_func(array('Joomla\\CMS\\Factory', 'getApplication'));

				if (is_object($app) && isset($app->input)) {
					return $app->input;
				}
			}

			if (class_exists('JFactory')) {
				$app = call_user_func(array('JFactory', 'getApplication'));

				if (is_object($app) && isset($app->input)) {
					return $app->input;
				}
			}

			return null;
		}

		protected static function normalizeType($type)
		{
			$type = strtolower((string) $type);

			if ($type === '' || $type === 'none') {
				return 'raw';
			}

			if ($type === 'boolean') {
				return 'bool';
			}

			if ($type === 'integer') {
				return 'int';
			}

			if ($type === 'base64') {
				return 'string';
			}

			return $type;
		}

		protected static function sanitizeFallback($value, $type)
		{
			$type = self::normalizeType($type);

			switch ($type) {
				case 'int':
					return (int) $value;

				case 'array':
					return is_array($value) ? $value : (array) $value;

				case 'uint':
					return max(0, (int) $value);

				case 'float':
					return (float) $value;

				case 'bool':
					return (bool) $value;

				case 'word':
					return preg_replace('/[^A-Z0-9_\\-]/i', '', (string) $value);

				case 'cmd':
					return preg_replace('/[^A-Z0-9_\\.\\-]/i', '', (string) $value);

				case 'alnum':
					return preg_replace('/[^A-Z0-9]/i', '', (string) $value);

				case 'string':
				case 'raw':
				default:
					return is_scalar($value) ? (string) $value : $value;
			}
		}

		public static function _cleanVar($var, $mask = 0, $type = null, $length = null)
		{
			if (is_array($var)) {
				$clean = array();

				foreach ($var as $key => $value) {
					$clean[$key] = self::_cleanVar($value, $mask, $type, $length);
				}

				return $clean;
			}

			if ($type === null || $type === '' || strtolower((string) $type) === 'none') {
				return $var;
			}

			$value = self::sanitizeFallback($var, $type);

			if (is_string($value) && $length !== null && is_numeric($length) && (int) $length > 0) {
				$value = substr($value, 0, (int) $length);
			}

			return $value;
		}

		public static function getVar($name, $default = null, $hash = 'default', $type = 'none', $mask = 0)
		{
			$input = self::getInput();
			$type = self::normalizeType($type);
			$hash = strtolower((string) $hash);

			if ($input) {
				if ($hash && $hash !== 'default' && isset($input->$hash) && is_object($input->$hash) && method_exists($input->$hash, 'get')) {
					return $input->$hash->get($name, $default, $type);
				}

				if (method_exists($input, 'get')) {
					return $input->get($name, $default, $type);
				}
			}

			if (isset($_REQUEST[$name])) {
				return self::sanitizeFallback($_REQUEST[$name], $type);
			}

			return $default;
		}

		public static function get($hash = 'default', $mask = 0)
		{
			$hash = strtolower((string) $hash);

			if ($hash === 'request' || $hash === 'default' || $hash === '') {
				return $_REQUEST;
			}

			if ($hash === 'get') {
				return $_GET;
			}

			if ($hash === 'post') {
				return $_POST;
			}

			if ($hash === 'files') {
				return $_FILES;
			}

			if ($hash === 'cookie') {
				return $_COOKIE;
			}

			if ($hash === 'server') {
				return $_SERVER;
			}

			if ($hash === 'env') {
				return $_ENV;
			}

			return $_REQUEST;
		}

		public static function getCmd($name, $default = '')
		{
			return self::getVar($name, $default, 'default', 'cmd');
		}

		public static function getInt($name, $default = 0)
		{
			return self::getVar($name, $default, 'default', 'int');
		}

		public static function getBool($name, $default = false)
		{
			return self::getVar($name, $default, 'default', 'bool');
		}

		public static function getString($name, $default = '')
		{
			return self::getVar($name, $default, 'default', 'string');
		}

		public static function getWord($name, $default = '')
		{
			return self::getVar($name, $default, 'default', 'word');
		}

		public static function getMethod()
		{
			if (isset($_SERVER['REQUEST_METHOD'])) {
				return strtoupper((string) $_SERVER['REQUEST_METHOD']);
			}

			return 'GET';
		}

		public static function setVar($name, $value, $hash = 'method', $overwrite = true)
		{
			$input = self::getInput();

			if ($input && method_exists($input, 'set')) {
				$input->set($name, $value);
			}

			if ($overwrite || !isset($_REQUEST[$name])) {
				$_REQUEST[$name] = $value;
			}

			return $value;
		}

		public static function checkToken($method = 'post')
		{
			if (class_exists('Joomla\\CMS\\Session\\Session')) {
				return (bool) call_user_func(array('Joomla\\CMS\\Session\\Session', 'checkToken'), $method);
			}

			if (class_exists('JSession')) {
				return (bool) call_user_func(array('JSession', 'checkToken'), $method);
			}

			return true;
		}
	}
}

if (!class_exists('MenusHelper')) {
	$menusHelperPath = dirname(__DIR__) . '/components/com_menus/helpers/menus.php';

	if (is_file($menusHelperPath)) {
		require_once $menusHelperPath;
	}
}
