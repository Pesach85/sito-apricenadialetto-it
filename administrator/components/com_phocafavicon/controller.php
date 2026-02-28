<?php
/*
 * @package Joomla 1.5
 * @copyright Copyright (C) 2005 Open Source Matters. All rights reserved.
 * @license http://www.gnu.org/copyleft/gpl.html GNU/GPL, see LICENSE.php
 *
 * @component Phoca Favicon
 * @copyright Copyright (C) Jan Pavelka www.phoca.cz
 * @license http://www.gnu.org/copyleft/gpl.html GNU/GPL
 */

jimport('joomla.application.component.controller');
// Submenu view
$view	= JRequest::getVar( 'view', '', '', 'string', JREQUEST_ALLOWRAW );

$l['cp']	= JText::_('COM_PHOCAFAVICON_CONTROL_PANEL');
$l['cf']	= JText::_('COM_PHOCAFAVICON_CREATE_FAVICON');
$l['i']		= JText::_('COM_PHOCAFAVICON_INFO');

if ($view == '' || $view == 'phocafaviconcp') {
	JSubMenuHelper::addEntry($l['cp'], 'index.php?option=com_phocafavicon', true);
	JSubMenuHelper::addEntry($l['cf'], 'index.php?option=com_phocafavicon&view=phocafavicon');
	JSubMenuHelper::addEntry($l['i'], 'index.php?option=com_phocafavicon&view=phocafaviconin' );
}

if ($view == 'phocafavicon') {
	JSubMenuHelper::addEntry($l['cp'], 'index.php?option=com_phocafavicon');
	JSubMenuHelper::addEntry($l['cf'], 'index.php?option=com_phocafavicon&view=phocafavicon', true);
	JSubMenuHelper::addEntry($l['i'], 'index.php?option=com_phocafavicon&view=phocafaviconin' );
}

if ($view == 'phocafaviconin') {
	JSubMenuHelper::addEntry($l['cp'], 'index.php?option=com_phocafavicon');
	JSubMenuHelper::addEntry($l['cf'], 'index.php?option=com_phocafavicon&view=phocafavicon');
	JSubMenuHelper::addEntry($l['i'], 'index.php?option=com_phocafavicon&view=phocafaviconin', true );
}

class PhocaFaviconCpController extends JController
{
	function display() {
		parent::display();
	}
}
?>
