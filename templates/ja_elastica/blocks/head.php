<?php
/**
 * ------------------------------------------------------------------------
 * JA T3 System plugin for Joomla 1.7
 * ------------------------------------------------------------------------
 * Copyright (C) 2004-2011 J.O.O.M Solutions Co., Ltd. All Rights Reserved.
 * @license - GNU/GPL, http://www.gnu.org/licenses/gpl.html
 * Author: J.O.O.M Solutions Co., Ltd
 * Websites: http://www.joomlart.com - http://www.joomlancers.com
 * ------------------------------------------------------------------------
 */

// No direct access
defined('_JEXEC') or die;

$doc = JFactory::getDocument();
$config = JFactory::getConfig();

if (trim((string) $doc->getMetaData('description')) === '') {
	$defaultMetaDescription = trim((string) $config->get('MetaDesc', ''));
	if ($defaultMetaDescription !== '') {
		$doc->setMetaData('description', $defaultMetaDescription);
	}
}

if (trim((string) $doc->getMetaData('robots')) === '') {
	$doc->setMetaData('robots', 'index, follow');
}

$googleSiteVerification = trim((string) $config->get('google_site_verification', ''));
$googleTagManagerId = strtoupper(trim((string) $config->get('google_tag_manager_id', '')));
$googleAnalyticsId = strtoupper(trim((string) $config->get('google_analytics_id', '')));

$GLOBALS['googleTagManagerNoScript'] = '';
?>
<script type="text/javascript">
var siteurl='<?php echo JURI::base(true) ?>/';
var tmplurl='<?php echo JURI::base(true)."/templates/".T3_ACTIVE_TEMPLATE ?>/';
var isRTL = <?php echo $this->isRTL()?'true':'false' ?>;
</script>
<script type="text/javascript" src="<?php echo JURI::base(true)."/templates/".T3_ACTIVE_TEMPLATE ?>/js/cookie-consent.js"></script>

<jdoc:include type="head" />

<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=3.0, user-scalable=yes"/>
<meta name="HandheldFriendly" content="true" />

<?php if ($googleSiteVerification !== ''): ?>
<meta name="google-site-verification" content="<?php echo htmlspecialchars($googleSiteVerification, ENT_COMPAT, 'UTF-8'); ?>" />
<?php endif; ?>

<?php if (preg_match('/^GTM-[A-Z0-9]+$/', $googleTagManagerId)): ?>
<script type="text/javascript">
(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','<?php echo $googleTagManagerId; ?>');
</script>
<?php $GLOBALS['googleTagManagerNoScript'] = '<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=' . htmlspecialchars($googleTagManagerId, ENT_COMPAT, 'UTF-8') . '" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>'; ?>
<?php elseif (preg_match('/^G-[A-Z0-9]+$/', $googleAnalyticsId)): ?>
<script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo htmlspecialchars($googleAnalyticsId, ENT_COMPAT, 'UTF-8'); ?>"></script>
<script type="text/javascript">
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '<?php echo $googleAnalyticsId; ?>');
</script>
<?php endif; ?>

<?php if (T3Common::mobile_device_detect()=='iphone'):?>
<meta name="apple-touch-fullscreen" content="YES" />
<?php endif;?>

<link href="<?php echo T3Path::getUrl('images/favicon.ico') ?>" rel="shortcut icon" type="image/x-icon" />

<?php JHTML::stylesheet ('', 'templates/system/css/system.css') ?>
<?php JHTML::stylesheet ('', 'templates/system/css/general.css') ?>
<link rel="stylesheet" type="text/css" href="<?php echo JURI::base(true)."/templates/".T3_ACTIVE_TEMPLATE ?>/css/modernize.css?v=20260228n" />
