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
defined('_JEXEC') or die;
JHtml::_('behavior.tooltip');
JHtml::_('behavior.formvalidation');
?>
<script type="text/javascript">
	Joomla.submitbutton = function(task)
	{
	
		if (task == 'phocafavicon.cancel' || document.formvalidator.isValid(document.id('phocafavicon-form'))) {
			Joomla.submitform(task, document.getElementById('phocafavicon-form'));
		}
		else {
			alert('<?php echo $this->escape(JText::_('JGLOBAL_VALIDATION_FORM_FAILED'));?>');
		}
	}
</script>

<form action="<?php JRoute::_('index.php?option=com_phocafavicon'); ?>" method="post" name="adminForm" id="phocafavicon-form" class="form-validate">
	<div class="width-60 fltlft">
		<fieldset class="adminform">
			<legend><?php echo  JText::_('COM_PHOCAFAVICON_CREATE_FAVICON'); ?></legend>
		
		<ul class="adminformlist">
			<?php 
			$formArray = array ('template', 'filename');
			foreach ($formArray as $value) {
				echo '<li>'.$this->form->getLabel($value) . $this->form->getInput($value).'</li>' . "\n";
			} ?>
		</ul>
		<div class="clr"></div>
		<p><?php echo JText::_( 'COM_PHOCAFAVICON_INFO_TEXT' ); ?></p>
	</fieldset>
</div>

<div class="clr"></div>


<input type="hidden" name="task" value="" />
<?php echo JHtml::_('form.token'); ?>
</form>

</div>
