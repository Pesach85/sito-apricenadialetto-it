<?php
/*======================================================================*\
|| #################################################################### ||
|| # Package - Joomla Template based on YJSimpleGrid Framework          ||
|| # Copyright (C) 2010  Youjoomla LLC. All Rights Reserved.            ||
|| # license - PHP files are licensed under  GNU/GPL V2                 ||
|| # license - CSS  - JS - IMAGE files  are Copyrighted material        ||
|| # bound by Proprietary License of Youjoomla LLC                      ||
|| # for more information visit http://www.youjoomla.com/license.html   ||
|| # Redistribution and  modification of this software                  ||
|| # is bounded by its licenses                                         ||
|| # websites - http://www.youjoomla.com | http://www.yjsimplegrid.com  ||
|| #################################################################### ||
\*======================================================================*/
// No direct access.
defined('_JEXEC') or die;
$getapps= & JFactory::getApplication();
$template = $getapps->getTemplate();
require( JPATH_SITE.DS."templates".DS.$template.DS."html".DS."mod_menu".DS."yjsg_menuswitch.php");
if ($params->get('class_sfx') =='nav' || $params->get('class_sfx') =='navd' || $params->get('class_sfx') =='split') {
		require( JPATH_SITE.DS."templates".DS.$template.DS."html".DS."mod_menu".DS."yjsg_topmenu.php"); /* top menu only*/ 
}else{
		require( JPATH_SITE.DS."templates".DS.$template.DS."html".DS."mod_menu".DS."yjsg_sidemenus.php");/* side  menus only*/
}
?>