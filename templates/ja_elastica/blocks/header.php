<?php
/**
 * ------------------------------------------------------------------------
 * JA Elastica Template for Joomla 2.5
 * ------------------------------------------------------------------------
 * Copyright (C) 2004-2011 J.O.O.M Solutions Co., Ltd. All Rights Reserved.
 * @license - GNU/GPL, http://www.gnu.org/licenses/gpl.html
 * Author: J.O.O.M Solutions Co., Ltd
 * Websites: http://www.joomlart.com - http://www.joomlancers.com
 * ------------------------------------------------------------------------
 */

// No direct access
defined('_JEXEC') or die;
?>
<?php
$app = & JFactory::getApplication();
$siteName = $app->getCfg('sitename');
if ($this->getParam('logoType', 'image')=='image'): ?>
<h1 class="logo">
    <a href="<?php JURI::base(true) ?>" title="<?php echo $siteName; ?>">
		<img src="<?php echo 'templates/'.T3_ACTIVE_TEMPLATE.'/images/logo-trans.png' ?>" alt="<?php echo $siteName; ?>" />
	</a>
</h1>
<?php else:
$logoText = (trim($this->getParam('logoText'))=='') ? $siteName : JText::_(trim($this->getParam('logoText')));
$sloganText = JText::_(trim($this->getParam('sloganText'))); ?>
<div class="logo-text">
    <h1><a href="<?php JURI::base(true) ?>" title="<?php echo $siteName; ?>"><span><?php echo $logoText; ?></span></a></h1>
    <p class="site-slogan"><?php echo $sloganText;?></p>
</div>
<?php endif; ?>

<?php if (($jamenu = $this->loadMenu())) : ?>
<div id="ja-mainnav" class="clearfix">
	<?php $jamenu->genMenu (); ?>
</div>
<?php endif;?>

<?php if($this->countModules('search') || $this->countModules('social')) : ?>
<div id="ja-top" class="clearfix">
	<?php if($this->countModules('social')) : ?>
	<div id="ja-social">
		<jdoc:include type="modules" name="social" />
	</div>
	<?php endif; ?>

	<?php if($this->countModules('search')) : ?>
	<div id="ja-search">
		<span class="search-btn" tabindex="0" role="button" aria-label="Apri ricerca">Search</span>
		<jdoc:include type="modules" name="search" />
	</div>
	<script type="text/javascript">
		// toggle search box active when click on search button
		var searchInput = $('mod-search-searchword');
		var searchBox = $('ja-search');
		var searchBtn = $$('#ja-search .search-btn')[0];
		$$('.search-btn').addEvent ('mouseenter', function () {
			if (searchInput) {
				searchInput.focus();
			}
		});
		if (searchBtn && searchBox) {
			searchBtn.addEvents({
				'click': function (event) {
					if (event && event.preventDefault) {
						event.preventDefault();
					}
					searchBox.toggleClass('active');
					if (searchBox.hasClass('active') && searchInput) {
						searchInput.focus();
					}
				},
				'keydown': function (event) {
					if (!event) {
						return;
					}
					var keyCode = event.code || event.keyCode;
					if (keyCode === 13 || keyCode === 32) {
						if (event.preventDefault) {
							event.preventDefault();
						}
						searchBox.toggleClass('active');
						if (searchBox.hasClass('active') && searchInput) {
							searchInput.focus();
						}
					}
				}
			});
		}
		if (searchInput && searchBox) {
			searchInput.addEvents ({
				'blur': function () {searchBox.removeClass ('active');},
				'focus': function () {searchBox.addClass ('active');}
			});
		}
	</script>
	<?php endif; ?>
</div>
<?php endif;?>

<script type="text/javascript">
document.addEventListener('DOMContentLoaded', function () {
	var mainNav = document.getElementById('ja-mainnav');
	var megaMenu = document.getElementById('ja-megamenu');
	if (!mainNav || !megaMenu) {
		return;
	}

	var menuButton = document.getElementById('ja-menu-button');
	if (!menuButton) {
		menuButton = document.createElement('div');
		menuButton.id = 'ja-menu-button';
		menuButton.textContent = 'Menu';
		megaMenu.parentNode.insertBefore(menuButton, megaMenu);
	}

	if (!menuButton.hasAttribute('tabindex')) {
		menuButton.setAttribute('tabindex', '0');
	}
	menuButton.setAttribute('role', 'button');
	menuButton.setAttribute('aria-label', 'Apri menu');

	var toggleMenu = function (event) {
		if (event) {
			event.preventDefault();
		}
		if (window.innerWidth > 767) {
			return;
		}
		mainNav.classList.toggle('rjd-active');
	};

	menuButton.addEventListener('click', toggleMenu);
	menuButton.addEventListener('keydown', function (event) {
		if (event.key === 'Enter' || event.key === ' ') {
			toggleMenu(event);
		}
	});
});
</script>

<ul class="no-display">
    <li><a href="<?php echo $this->getCurrentURL();?>#ja-content" title="<?php echo JText::_("SKIP_TO_CONTENT");?>"><?php echo JText::_("SKIP_TO_CONTENT");?></a></li>
</ul>
