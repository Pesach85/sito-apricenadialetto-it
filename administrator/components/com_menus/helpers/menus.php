<?php

/**
 * @package     Joomla.Administrator
 * @subpackage  com_menus
 *
 * @copyright   (C) 2009 Open Source Matters, Inc. <https://www.joomla.org>
 * @license     GNU General Public License version 2 or later; see LICENSE.txt

 * @phpcs:disable PSR1.Classes.ClassDeclaration.MissingNamespace
 */

// phpcs:disable PSR1.Files.SideEffects
\defined('_JEXEC') or die;
// phpcs:enable PSR1.Files.SideEffects

/**
 * Menus component helper.
 *
 * @since       1.6
 *
 * @deprecated  4.3 will be removed in 6.0
 *              Use \Joomla\Component\Menus\Administrator\Helper\MenusHelper instead
 */
if (class_exists('\\Joomla\\Component\\Menus\\Administrator\\Helper\\MenusHelper')) {
	class MenusHelper extends \Joomla\Component\Menus\Administrator\Helper\MenusHelper
	{
	}
} else {
	class MenusHelper
	{
		protected static $_filter = array('option', 'view', 'layout');

		public static function addSubmenu($vName)
		{
			if (!class_exists('JSubMenuHelper')) {
				return;
			}

			JSubMenuHelper::addEntry(
				JText::_('COM_MENUS_SUBMENU_MENUS'),
				'index.php?option=com_menus&view=menus',
				$vName == 'menus'
			);

			JSubMenuHelper::addEntry(
				JText::_('COM_MENUS_SUBMENU_ITEMS'),
				'index.php?option=com_menus&view=items',
				$vName == 'items'
			);
		}

		public static function getActions($parentId = 0)
		{
			$user = JFactory::getUser();
			$result = class_exists('JObject') ? new JObject : new stdClass();

			$assetName = empty($parentId) ? 'com_menus' : 'com_menus.item.' . (int) $parentId;

			$actions = array('core.admin', 'core.manage', 'core.create', 'core.edit', 'core.edit.state', 'core.delete');
			foreach ($actions as $action) {
				$value = $user->authorise($action, $assetName);
				if (is_object($result) && method_exists($result, 'set')) {
					$result->set($action, $value);
				} else {
					$result->{$action} = $value;
				}
			}

			return $result;
		}

		public static function getLinkKey($request)
		{
			if (empty($request)) {
				return false;
			}

			if (is_string($request)) {
				$args = array();
				if (strpos($request, 'index.php') === 0) {
					parse_str(parse_url(htmlspecialchars_decode($request), PHP_URL_QUERY), $args);
				} else {
					parse_str($request, $args);
				}
				$request = $args;
			}

			foreach ($request as $name => $value) {
				if (!in_array($name, self::$_filter)) {
					unset($request[$name]);
				}
			}

			ksort($request);

			return 'index.php?' . http_build_query($request, '', '&');
		}

		public static function getMenuTypes()
		{
			$db = JFactory::getDbo();
			$db->setQuery('SELECT a.menutype FROM #__menu_types AS a');
			return $db->loadColumn();
		}

		public static function getMenuLinks($menuType = null, $parentId = 0, $mode = 0, $published = array(), $languages = array(), $clientId = null)
		{
			$db = JFactory::getDbo();
			$query = $db->getQuery(true);

			$query->select('a.id AS value, a.title AS text, a.level, a.menutype, a.type, a.template_style_id, a.checked_out');
			$query->from('#__menu AS a');
			$query->join('LEFT', $db->quoteName('#__menu') . ' AS b ON a.lft > b.lft AND a.rgt < b.rgt');

			if ($menuType) {
				$query->where('(a.menutype = ' . $db->quote($menuType) . ' OR a.parent_id = 0)');
			}

			if ($parentId && (int) $mode === 2) {
				$query->join('LEFT', '#__menu AS p ON p.id = ' . (int) $parentId);
				$query->where('(a.lft <= p.lft OR a.rgt >= p.rgt)');
			}

			if (!empty($languages)) {
				if (is_array($languages)) {
					$languages = '(' . implode(',', array_map(array($db, 'quote'), $languages)) . ')';
				}
				$query->where('a.language IN ' . $languages);
			}

			if (!empty($published)) {
				if (is_array($published)) {
					$published = '(' . implode(',', $published) . ')';
				}
				$query->where('a.published IN ' . $published);
			}

			$query->where('a.published != -2');
			$query->group('a.id, a.title, a.level, a.menutype, a.type, a.template_style_id, a.checked_out, a.lft');
			$query->order('a.lft ASC');

			$db->setQuery($query);
			$links = $db->loadObjectList();

			if (!is_array($links)) {
				return array();
			}

			foreach ($links as &$link) {
				$link->text = str_repeat('- ', (int) $link->level) . $link->text;
			}

			if (!empty($menuType)) {
				return $links;
			}

			$query->clear();
			$query->select('*')->from('#__menu_types')->where('menutype <> ' . $db->quote(''))->order('title, menutype');
			$db->setQuery($query);
			$menuTypes = $db->loadObjectList();

			if (!is_array($menuTypes)) {
				return array();
			}

			$rlu = array();
			foreach ($menuTypes as &$type) {
				$rlu[$type->menutype] = &$type;
				$type->links = array();
			}

			foreach ($links as &$link) {
				if (isset($rlu[$link->menutype])) {
					$rlu[$link->menutype]->links[] = &$link;
					unset($link->menutype);
				}
			}

			return $menuTypes;
		}

		public static function getAssociations($pk)
		{
			$associations = array();

			if ((int) $pk <= 0) {
				return $associations;
			}

			$db = JFactory::getDbo();
			$query = $db->getQuery(true)
				->select('m.id, m.language')
				->from('#__associations AS a')
				->join('INNER', '#__associations AS a2 ON a.key = a2.key')
				->join('INNER', '#__menu AS m ON m.id = a2.id')
				->where('a.id = ' . (int) $pk)
				->where('a.context = ' . $db->quote('com_menus.item'))
				->where('a2.context = ' . $db->quote('com_menus.item'))
				->where('a.id <> a2.id');

			$db->setQuery($query);
			$rows = $db->loadObjectList();

			if (is_array($rows)) {
				foreach ($rows as $row) {
					$associations[$row->language] = (int) $row->id;
				}
			}

			return $associations;
		}
	}
}
