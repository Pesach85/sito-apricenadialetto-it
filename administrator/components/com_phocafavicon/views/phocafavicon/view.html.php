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

class PhocaFaviconCpViewPhocaFavicon extends JView
{

	protected $form;
	protected $tmpl;

	public function display($tpl = null) {

		$this->form		= $this->get('Form');
		
		JHTML::stylesheet( 'administrator/components/com_phocafavicon/assets/phocafavicon.css' );
		
		$this->addToolbar();
		parent::display($tpl);
	}
	
	protected function addToolbar() {
	
		require_once JPATH_COMPONENT.DS.'helpers'.DS.'phocafaviconcp.php';
	
		$canDo	= PhocaFaviconHelperControlPanel::getActions();
	
		$text = JText::_( 'COM_PHOCAFAVICON_CREATE' );
		JToolBarHelper::title( JText::_( 'COM_PHOCAFAVICON_FAVICON' ).': <small><small>[ ' . $text.' ]</small></small>' , 'favicon.png');
		
		if ($canDo->get('core.create')) {
			JToolBarHelper::custom('phocafavicon.create', 'new.png', '','COM_PHOCAFAVICON_CREATE', false);
		}
		JToolBarHelper::cancel( 'phocafavicon.cancel', 'COM_PHOCAFAVICON_CLOSE' );
		JToolBarHelper::divider();
		JToolBarHelper::help( 'screen.phocafavicon', true );
	}
}
?>
