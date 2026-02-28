<?php 
defined('_JEXEC') or die('Restricted access');
echo '<div id="phocafavicon-upload">';
echo '<div style="font-size:1px;height:1px;margin:0px;padding:0px;">&nbsp;</div>';
echo '<form action="'. $this->tmpl['su_url'] .'" id="uploadFormU" method="post" enctype="multipart/form-data">';
if ($this->tmpl['ftp']) { echo PhocaFaviconHelper::renderFTPaccess();}  
echo '<fieldset class="actions">'
	.' <legend>'; 
echo JText::_( 'COM_PHOCAFAVICON_UPLOAD_FILE' ).' [ '. JText::_( 'COM_PHOCAFAVICON_MAX_SIZE' ).':&nbsp;'.$this->tmpl['uploadmaxsizeread'].','
	.' '.JText::_('COM_PHOCAFAVICON_MAX_RESOLUTION').':&nbsp;'. $this->tmpl['uploadmaxreswidth'].' x '.$this->tmpl['uploadmaxresheight'].' px ]';
echo ' </legend>';
echo $this->tmpl['su_output']
	.'</fieldset>';
echo '</form>';	 
echo '</div>';