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

// no direct access
defined( '_JEXEC' ) or die( 'Restricted access' );

jimport( 'joomla.filesystem.folder' );

function com_uninstall()
{
	$folder[1][0]	=	'images' . DS . 'phocafavicon' . DS ;
	$folder[1][1]	= 	JPATH_ROOT . DS .  $folder[1][0];

	$message = '<p><b><span style="color:#009933">Folder</span> ' . $folder[1][0] 
					   .' <span style="color:#009933">still exists!</span></b> Please delete it manually, if you want.</p>';
	echo $message;
}

?>