<?php
/*
 * @package		Joomla.Framework
 * @copyright	Copyright (C) 2005 - 2010 Open Source Matters, Inc. All rights reserved.
 * @license		GNU General Public License version 2 or later; see LICENSE.txt
 *
 * @component Phoca Component
 * @copyright Copyright (C) Jan Pavelka www.phoca.cz
 * @license http://www.gnu.org/copyleft/gpl.html GNU General Public License version 2 or later;
 */
defined('_JEXEC') or die();
jimport( 'joomla.application.component.view' );
jimport( 'joomla.html.pane' );

class PhocaFaviconCpViewPhocaFaviconcp extends JView
{
	protected $tmpl;
	public function display($tpl = null) {

		JHTML::stylesheet('administrator/components/com_phocafavicon/assets/phocafavicon.css' );

		JHTML::_('behavior.tooltip');
		$this->tmpl['version'] = PhocaFaviconHelper::getPhocaVersion();
		$this->addToolbar();
		parent::display($tpl);
	}
	
	protected function addToolbar() {
		require_once JPATH_COMPONENT.DS.'helpers'.DS.'phocafaviconcp.php';

		$state	= $this->get('State');
		$canDo	= PhocaFaviconHelperControlPanel::getActions();
		JToolBarHelper::title( JText::_( 'COM_PHOCAFAVICON_PF_CONTROL_PANEL' ), 'phoca.png' );
		
		if ($canDo->get('core.admin')) {
			JToolBarHelper::preferences('com_phocafavicon');
			JToolBarHelper::divider();
		}
		
		JToolBarHelper::help( 'screen.phocafavicon', true );
	}
}
?>