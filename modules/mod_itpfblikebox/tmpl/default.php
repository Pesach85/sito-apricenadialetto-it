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
<?php $facebookPageLink = trim((string) $params->get("fbPageLink")); ?>
<div class="itp-fblike-box<?php echo $moduleClassSfx;?>">
<?php if (!empty($facebookPageLink)): ?>
<?php $facebookPageHref = str_replace('http://', 'https://', $facebookPageLink); ?>
<?php $facebookPluginSrc = 'https://www.facebook.com/plugins/page.php?href=' . rawurlencode($facebookPageHref) . '&tabs=timeline&width=340&height=320&small_header=true&adapt_container_width=true&hide_cover=false&show_facepile=false'; ?>
<iframe
	class="fb-page-iframe"
	src="<?php echo htmlspecialchars($facebookPluginSrc, ENT_COMPAT, 'UTF-8');?>"
	width="340"
	height="320"
	style="border:none;overflow:hidden"
	scrolling="no"
	frameborder="0"
	allowfullscreen="true"
	allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
	loading="lazy"
	referrerpolicy="strict-origin-when-cross-origin"></iframe>
<noscript><a href="<?php echo htmlspecialchars($facebookPageHref, ENT_COMPAT, 'UTF-8');?>" rel="noopener noreferrer" target="_blank">Apri la pagina Facebook</a></noscript>
<?php endif; ?>
</div>