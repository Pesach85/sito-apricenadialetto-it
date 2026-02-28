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
?>
<!-- footer -->
<div id="footer"  style="font-size:<?php echo $css_font; ?>; width:<?php echo $css_width.$css_widthdefined; ?>;background:<?php echo $hi_color?>;">
  <div id="youjoomla">
    <?php if ($this->countModules('footer')) { ?>
        <div id="footmod">
            <jdoc:include type="modules" name="footer" style="raw" />
        </div>
	<?php } ?>
	<?php if (!preg_match("/iphone/i",$who)){ ?>
    	<div id="cp">
		<?php echo getYJLINKS($default_font_family,$yj_copyrightear,$yj_templatename)  ?>
		<?php } ?>
		
		<?php if ($ppbranding_off == 2) { ?>
                <a class="pplogo png" href="https://pixelpointcreative.com/" target="_blank" title="Template by Pixel Point Creative">
					<span>Template by Pixel Point Creative</span>
                </a>
			<?php } ?>
			
      
	<?php if ($branding_off == 2) { ?>
				<a class="yjsglogo png" href="https://yjsimplegrid.com/" target="_blank">
					<span>YJSimpleGrid Joomla! Templates Framework official website</span>
                </a>
			<?php } ?>
 </div>
</div>
</div>
<!-- end footer -->
<?php if (!preg_match("/iphone/i",$who)){ ?>
	<?php if ($joomlacredit_off ==2): ?>
		<div id="joomlacredit"  style="font-size:<?php echo $css_font; ?>; width:<?php echo $css_width.$css_widthdefined; ?>;">
			<a href="https://www.joomla.org" target="_blank">Joomla!</a> is Free Software released under the 
			<a href="https://www.gnu.org/licenses/gpl-2.0.html" target="_blank">GNU/GPL License.</a>
		</div>
	<?php endif; ?>

<?php } ?>
<?php if ($selectors_override_type == 3 && $selectors_override == 1){ ?>
<script type="text/javascript"> Cufon.now(); </script>
<?php } ?>
<div id="cookieConsentBanner" style="display:none; position:fixed; left:0; right:0; bottom:0; z-index:99999; background:#ffffff; border-top:1px solid #cccccc; padding:10px; font-size:12px; line-height:1.4;">
	Questo sito usa cookie tecnici e, previo consenso, cookie analytics/marketing. 
	<a href="https://apricenadialetto.it/index.php/privacy-policy" style="margin-right:8px;">Informativa</a>
	<a href="#" id="cookieConsentAccept" style="margin-right:8px;">Accetta</a>
	<a href="#" id="cookieConsentReject">Rifiuta non essenziali</a>
</div>
<?php echo $add_ga ?>