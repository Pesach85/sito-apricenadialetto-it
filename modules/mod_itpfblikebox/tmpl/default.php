<?php
/**
 * @package      ITPrism Modules
 * @subpackage   ITPFacebookLikeBox
 * @author       Todor Iliev
 * @copyright    Copyright (C) 2010 Todor Iliev <todor@itprism.com>. All rights reserved.
 * @license      http://www.gnu.org/copyleft/gpl.html GNU/GPL
 * ITPFacebookLikeBox is free software. This version may have been modified pursuant
 * to the GNU General Public License, and as distributed it includes or
 * is derivative of works licensed under the GNU General Public License or
 * other free or open source software licenses.
 */

// no direct access
defined( "_JEXEC" ) or die;?>
<?php $hasMarketingConsent = isset($_COOKIE['cookie_consent_marketing']) && $_COOKIE['cookie_consent_marketing'] == '1'; ?>
<?php $facebookPageLink = trim((string) $params->get("fbPageLink")); ?>
<div class="itp-fblike-box<?php echo $moduleClassSfx;?>">
<?php if (!$hasMarketingConsent): ?>
<?php if (!empty($facebookPageLink)): ?>
<a href="<?php echo htmlspecialchars($facebookPageLink, ENT_COMPAT, 'UTF-8');?>" rel="noopener noreferrer" target="_blank">Visita la nostra pagina Facebook</a>
<?php endif; ?>
</div>
<?php return; ?>
<?php endif; ?>

<?php
$fbWidth = (int) $params->get("fbWidth", 340);
$fbHeight = (int) $params->get("fbHeight", 480);
$fbShowFaces = $params->get("fbFaces", 1) ? 'true' : 'false';
$fbShowTimeline = $params->get("fbStream", 1) ? 'timeline' : '';
$fbHideCover = $params->get("fbHeader", 1) ? 'false' : 'true';
$facebookPageHref = str_replace('http://', 'https://', $facebookPageLink);
$facebookIframeSrc = 'https://www.facebook.com/plugins/page.php?href=' . rawurlencode($facebookPageHref)
    . '&tabs=' . rawurlencode($fbShowTimeline)
    . '&width=' . $fbWidth
    . '&height=' . $fbHeight
    . '&small_header=false&adapt_container_width=true&hide_cover=' . $fbHideCover
    . '&show_facepile=' . $fbShowFaces;
?>

<?php if (!empty($facebookPageLink)): ?>
<iframe
src="<?php echo htmlspecialchars($facebookIframeSrc, ENT_COMPAT, 'UTF-8');?>"
scrolling="no"
frameborder="0"
style="border:none; overflow:hidden; width:100%; max-width:<?php echo $fbWidth;?>px; height:<?php echo $fbHeight;?>px;"
allow="encrypted-media; web-share"
allowfullscreen="true"></iframe>
<?php endif; ?>

<?php if (!empty($facebookPageLink)): ?>
<div style="margin-top:8px;">
  <a href="<?php echo htmlspecialchars($facebookPageLink, ENT_COMPAT, 'UTF-8');?>" rel="noopener noreferrer" target="_blank">Visita la nostra pagina Facebook</a>
</div>
<?php endif; ?>
</div>