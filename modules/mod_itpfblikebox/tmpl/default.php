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
<?php if (!empty($facebookPageLink)): ?>
<?php $facebookPageHref = str_replace('http://', 'https://', $facebookPageLink); ?>
<a class="fb-compact-link" href="<?php echo htmlspecialchars($facebookPageHref, ENT_COMPAT, 'UTF-8');?>" rel="noopener noreferrer" target="_blank">Apri la pagina Facebook</a>
<?php endif; ?>
</div>