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
defined( '_JEXEC' ) or die( 'Restricted access' );

jimport( 'joomla.filesystem.folder' );

function com_install()
{
	$app	= JFactory::getApplication();
	// -->
	$folder[0][0]	=	'images' . DS . 'phocafavicon' . DS ;
	$folder[0][1]	= 	JPATH_ROOT . DS .  $folder[0][0];
	
	$lang = JFactory::getLanguage();
	$lang->load('com_phocafavicon.sys');
	$lang->load('com_phocafavicon');
	
	
	$message = '';
	$error	 = array();
	foreach ($folder as $key => $value)
	{
		if (!JFolder::exists( $value[1]))
		{
			if (JFolder::create( $value[1], 0755 ))
			{
				
				$data = "<html>\n<body bgcolor=\"#FFFFFF\">\n</body>\n</html>";
				JFile::write($value[1].DS."index.html", $data);
				
				$data = "<html>\n<body bgcolor=\"#FFFFFF\">\n</body>\n</html>";
				JFile::write($value[1].DS."index.html", $data);
				
				$message .= '<span style="color:#009933">Folder</span> ' . $value[0] 
						   .' <span style="color:#009933">created!</span>';
				$message .= '<br /><span >PhocaFavicon successfully installed.</span>';
				$error[] = 0;
			}	 
			else
			{
				$message .= '<span style="color:#CC0033">Folder</span> ' . $value[0]
						   .' <span style="color:#CC0033">creation failed!</span> <span>Please create it manually.</span>';
				$error[] = 1;
			}
		}
		else//Folder exist
		{
			$message .= '<span style="color:#009933">Folder</span> ' . $value[0] 
						   .' <span style="color:#009933">exists!</span>';
			$message .= '<br /><span >PhocaFavicon successfully installed.</span>';
			$error[] = 0;
		}
	}
	
	echo '<div style="padding:15px;background:#fff;color: #777;font-size:105%;">';
	?>
	<a style="text-decoration:none" href="http://www.phoca.cz/" target="_blank"><?php
			echo  JHTML::_('image', 'administrator/components/com_phocafavicon/assets/images/logo.png', 'Phoca.cz');
		?></a>
		<div style="position:relative;float:right;">
			<?php echo  JHTML::_('image', 'administrator/components/com_phocafavicon/assets/images/logo-phoca.png', 'Phoca.cz');?>
		</div>
		<p>&nbsp;</p>
	<?php 
	echo '<div>' . $message . '</div><p>&nbsp;</p>';
	
	echo '<p style="color: #c0c0c0;">';
	echo '<ul><li><a href="index.php?option=com_phocafavicon">Phoca Favicon Component</a></li>';
	echo '<li><a href="http://www.phoca.cz/documentation/category/4-phoca-favicon-component" target="_blank">Phoca Favicon Documentation</a></li>';
	echo '<li><a href="http://www.phoca.cz/forum" target="_blank">Phoca Forum</a></li>';
	echo '<li><a href="http://www.phoca.cz/" target="_blank" >Phoca.cz</a></li></ul>';
	
	
	echo '<p>&nbsp;</p>';
	echo '<div>Go to <a style="text-decoration: underline" href="index.php?option=com_phocafavicon">Phoca Favicon Control Panel</a>.</div>';
	
	echo '<div style="margin-top:30px;height:39px;background: url(\''. JURI::base(true).'/components/com_phocafavicon/assets/images/line.png\') 100% 0 no-repeat;">&nbsp;</div>';
	
	echo '</div>';
	//$link = 'index.php?option=com_phocafavicon';
	//$app->redirect($link, $message);
}

?>