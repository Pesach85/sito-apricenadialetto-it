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
jimport( 'joomla.client.helper' );
jimport( 'joomla.application.component.view');

class PhocaFaviconCpViewPhocaFaviconi extends JView
{

	protected $tmpl;
	protected $folderstate;
	protected $images;
	protected $folders;
	protected $currentFolder;
	protected $session;
	protected $field;
	protected $fce;

	function display($tpl = null) {

		// Do not allow cache
		JResponse::allowCache(false);
		$this->session		= JFactory::getSession();
		$this->field		= JRequest::getVar('field');
		$this->fce 			= 'phocaSelectFileName_'.$this->field;
		$this->folderstate	= $this->get('FolderState');
		$this->images 		= $this->get('images');
		$this->folders		= $this->get('folders');
		
		
		$params 							= JComponentHelper::getParams('com_phocafavicon');
		$this->tmpl['uploadmaxsize'] 		= $params->get( 'upload_maxsize', 3145728 );
		$this->tmpl['uploadmaxsizeread'] 	= PhocaFaviconHelper::getFileSizeReadable($this->tmpl['uploadmaxsize']);
		$this->tmpl['uploadmaxreswidth'] 	= $params->get( 'upload_maxres_width', 3072 );
		$this->tmpl['uploadmaxresheight'] 	= $params->get( 'upload_maxres_height', 2304 );
		
		JHTML::stylesheet('administrator/components/com_phocafavicon/assets/phocafavicon.css' );
		$document	= JFactory::getDocument();
		$document->addCustomTag("<!--[if lt IE 8]>\n<link rel=\"stylesheet\" href=\"../administrator/components/com_phocafavicon/assets/phocafaviconieall.css\" type=\"text/css\" />\n<![endif]-->");
		
		
		$this->currentFolder = '';
		if (isset($this->folderstate->folder) && $this->folderstate->folder != '') {
			$this->currentFolder = $this->folderstate->folder;
		}
		
		// - - - - - - - - - - -
		// Upload
		// - - - - - - - - - - -
		$sU							= new PhocaFaviconFileUploadSingle();
		$sU->returnUrl				= 'index.php?option=com_phocafavicon&view=phocafaviconi&tmpl=component&folder='. $this->currentFolder.'&field='. $this->field;
		$this->tmpl['su_output']	= $sU->getSingleUploadHTML();
		$this->tmpl['su_url']		= JURI::base().'index.php?option=com_phocafavicon&task=phocafaviconu.upload&amp;'
								  .$this->session->getName().'='.$this->session->getId().'&amp;'
								  . JUtility::getToken().'=1&amp;viewback=phocafaviconi&amp;'
								  .'folder='. $this->currentFolder.'&field='. $this->field;
		
		$this->tmpl['ftp'] 			= !JClientHelper::hasCredentials('ftp');
		
		$path 			= PhocaFaviconHelper::getPathSet();
		$path_orig_rel 	= $path['orig_rel_ds'];
		$this->assign('path_orig_rel', $path_orig_rel);
		
		

		parent::display($tpl);
	}

	function setFolder($index = 0)
	{
		if (isset($this->folders[$index])) {
			$this->_tmp_folder = &$this->folders[$index];
		} else {
			$this->_tmp_folder = new JObject;
		}
	}

	function setImage($index = 0)
	{
		if (isset($this->images[$index])) {
			$this->_tmp_img = &$this->images[$index];
		} else {
			$this->_tmp_img = new JObject;
		}
	}
}
