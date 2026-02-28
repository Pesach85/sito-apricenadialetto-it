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
defined( '_JEXEC' ) or die();
jimport( 'joomla.application.component.view' );

class PhocaFaviconCpViewPhocaFaviconIn extends JView
{
	protected $tmpl;
	
	public function display($tpl = null) {

		JHTML::stylesheet( 'administrator/components/com_phocafavicon/assets/phocafavicon.css' );		
		$this->tmpl['version'] = PhocaFaviconHelper::getPhocaVersion();
		$this->addToolbar();
		parent::display($tpl);
	}
	
	protected function addToolbar() {
		JToolBarHelper::title( JText::_( 'COM_PHOCAFAVICON_PF_INFO' ), 'info.png' );
		JToolBarHelper::cancel( 'phocafavicon.cancel', 'COM_PHOCAFAVICON_CLOSE' );
		JToolBarHelper::divider();
		JToolBarHelper::help( 'screen.phocafavicon', true );
	}
}
?>
