<?php
defined('_JEXEC') or die;
JHTML::_('behavior.tooltip');
echo '<div class="phoca-adminform">'
	.'<form action="index.php" method="post" name="adminForm">'
	.'<div style="float:right;margin:10px;">'
	. JHTML::_('image', 'administrator/components/com_phocafavicon/assets/images/logo-phoca.png', 'Phoca.cz' )
	.'</div>'
	. JHTML::_('image', 'administrator/components/com_phocafavicon/assets/images/icon-phoca-logo.png', 'Phoca.cz')
	.'<h3>'. JText::_('COM_PHOCAFAVICON_INFORMATION').'</h3>';


echo '<h3>'.  JText::_('COM_PHOCAFAVICON_VERSION').'</h3>'
.'<p>'.  $this->tmpl['version'] .'</p>';

echo '<h3>'.  JText::_('COM_PHOCAFAVICON_COPYRIGHT').'</h3>'
.'<p>© 2007 - '.  date("Y"). ' Jan Pavelka</p>'
.'<p><a href="http://www.phoca.cz/" target="_blank">www.phoca.cz</a></p>';

echo '<h3>'.  JText::_('COM_PHOCAFAVICON_LICENCE').'</h3>'
.'<p><a href="http://www.gnu.org/licenses/gpl-2.0.html" target="_blank">GPLv2</a></p>';

echo '<h3>'.  JText::_('COM_PHOCAFAVICON_TRANSLATION').': '. JText::_('COM_PHOCAFAVICON_TRANSLATION_LANGUAGE_TAG').'</h3>'
.'<p>© 2007 - '.  date("Y"). ' '. JText::_('COM_PHOCAFAVICON_TRANSLATER'). '</p>'
.'<p>'.JText::_('COM_PHOCAFAVICON_TRANSLATION_SUPPORT_URL').'</p>';



echo '<input type="hidden" name="task" value="" />'
.'<input type="hidden" name="option" value="com_phocafavicon" />'
.'<input type="hidden" name="controller" value="phocafaviconin" />'
.'</form>';

echo '<p>&nbsp;</p>';

echo '<div style="border-top:1px solid #c2c2c2"></div>'
.'<div id="pg-update"><a href="http://www.phoca.cz/version/index.php?phocafavicon='.  $this->tmpl['version'] .'" target="_blank">'.  JText::_('COM_PHOCAFAVICON_CHECK_FOR_UPDATE') .'</a></div>';

echo '</div>';