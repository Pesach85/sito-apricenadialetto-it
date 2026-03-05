<?php
/**
 * @package     Joomla.Administrator
 * @subpackage  com_menus
 *
 * @copyright   (C) 2011 Open Source Matters, Inc. <https://www.joomla.org>
 * @license     GNU General Public License version 2 or later; see LICENSE.txt
 */

defined('_JEXEC') or die;

/**
 * Menu table
 *
 * @since  1.6
 */
class MenusTableMenu extends JTableMenu
{
	/**
	 * Binds a named array/hash to this object.
	 *
	 * @param   array   $src     An associative array or object to bind to the JTable instance.
	 * @param   mixed   $ignore  An optional array or space separated list of properties to ignore while binding.
	 *
	 * @return  boolean  True on success.
	 *
	 * @since   3.0
	 */
	public function bind($src, $ignore = array())
	{
		$result = parent::bind($src, $ignore);

		if ($result)
		{
			$this->normalizeCheckoutColumns();
		}

		return $result;
	}

	/**
	 * Method to load a row from the database by primary key and normalize nullable checkout fields.
	 *
	 * @param   mixed    $pk     An optional primary key value to load the row by, or an associative array of fields to match.
	 * @param   boolean  $reset  True to reset the default values before loading the new row.
	 *
	 * @return  boolean  True if successful.
	 *
	 * @since   3.0
	 */
	public function load($pk = null, $reset = true)
	{
		$result = parent::load($pk, $reset);

		if ($result)
		{
			$this->normalizeCheckoutColumns();
		}

		return $result;
	}

	/**
	 * Method to store a row in the database from the JTable instance properties.
	 *
	 * @param   boolean  $updateNulls  True to update fields with null values.
	 *
	 * @return  boolean  True on success.
	 *
	 * @since   3.0
	 */
	public function store($updateNulls = false)
	{
		$this->normalizeCheckoutColumns();

		return parent::store($updateNulls);
	}

	/**
	 * Normalize checkout columns to avoid strict SQL errors on NOT NULL fields.
	 *
	 * @return  void
	 */
	protected function normalizeCheckoutColumns()
	{
		if ($this->checked_out === null || $this->checked_out === '')
		{
			$this->checked_out = 0;
		}

		if ($this->checked_out_time === null || $this->checked_out_time === '')
		{
			$this->checked_out_time = $this->_db->getNullDate();
		}
	}

	/**
	 * Method to delete a node and, optionally, its child nodes from the table.
	 *
	 * @param   integer  $pk        The primary key of the node to delete.
	 * @param   boolean  $children  True to delete child nodes, false to move them up a level.
	 *
	 * @return  boolean  True on success.
	 *
	 * @since   2.5
	 */
	public function delete($pk = null, $children = false)
	{
		$return = parent::delete($pk, $children);

		if ($return)
		{
			// Delete key from the #__modules_menu table
			$db = JFactory::getDbo();
			$query = $db->getQuery(true)
				->delete($db->quoteName('#__modules_menu'))
				->where($db->quoteName('menuid') . ' = ' . $pk);
			$db->setQuery($query);
			$db->execute();
		}

		return $return;
	}
}
