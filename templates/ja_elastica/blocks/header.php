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

	if (mainNav && megaMenu) {
		var menuButton = document.getElementById('ja-menu-button');
		if (!menuButton) {
			menuButton = document.createElement('button');
			menuButton.id = 'ja-menu-button';
			menuButton.type = 'button';
			menuButton.innerHTML = '<span class="menu-icon" aria-hidden="true">☰</span><span class="menu-label">Menu</span>';
			megaMenu.parentNode.insertBefore(menuButton, megaMenu);
		} else {
			menuButton.innerHTML = '<span class="menu-icon" aria-hidden="true">☰</span><span class="menu-label">Menu</span>';
		}

		menuButton.setAttribute('aria-label', 'Apri menu principale');
		menuButton.setAttribute('aria-expanded', 'false');
		menuButton.setAttribute('aria-controls', 'ja-megamenu');
		mainNav.classList.add('mobile-nav-ready');

		var mobileMode = function () {
			return window.innerWidth <= 767;
		};

		var closeAllSubmenus = function () {
			var items = megaMenu.querySelectorAll('li.haschild.mobile-open');
			for (var index = 0; index < items.length; index++) {
				items[index].classList.remove('mobile-open');
			}
		};

		var openMenu = function () {
			mainNav.classList.add('rjd-active');
			menuButton.setAttribute('aria-expanded', 'true');
		};

		var closeMenu = function () {
			mainNav.classList.remove('rjd-active');
			menuButton.setAttribute('aria-expanded', 'false');
			closeAllSubmenus();
		};

		menuButton.addEventListener('click', function (event) {
			if (!mobileMode()) {
				return;
			}
			event.preventDefault();
			if (mainNav.classList.contains('rjd-active')) {
				closeMenu();
			} else {
				openMenu();
			}
		});

		menuButton.addEventListener('keydown', function (event) {
			if ((event.key === 'Enter' || event.key === ' ') && mobileMode()) {
				event.preventDefault();
				menuButton.click();
			}
		});

		var parents = megaMenu.querySelectorAll('li.haschild');
		for (var i = 0; i < parents.length; i++) {
			var item = parents[i];
			var link = item.querySelector('a');
			if (!link) {
				continue;
			}

			if (!item.querySelector('.submenu-toggle')) {
				var toggle = document.createElement('button');
				toggle.type = 'button';
				toggle.className = 'submenu-toggle';
				toggle.setAttribute('aria-label', 'Apri sottomenu');
				toggle.innerHTML = '<span aria-hidden="true">▾</span>';
				link.parentNode.insertBefore(toggle, link.nextSibling);
			}
		}

		megaMenu.addEventListener('click', function (event) {
			if (!mobileMode()) {
				return;
			}

			var target = event.target;
			while (target && target !== megaMenu && !target.classList.contains('submenu-toggle')) {
				target = target.parentNode;
			}

			if (!target || target === megaMenu || !target.classList.contains('submenu-toggle')) {
				return;
			}

			event.preventDefault();
			var parent = target;
			while (parent && parent !== megaMenu && (!parent.classList || !parent.classList.contains('haschild') || parent.tagName.toLowerCase() !== 'li')) {
				parent = parent.parentNode;
			}
			if (!parent) {
				return;
			}

			if (parent.classList.contains('mobile-open')) {
				parent.classList.remove('mobile-open');
			} else {
				var siblings = parent.parentNode ? parent.parentNode.children : [];
				for (var j = 0; j < siblings.length; j++) {
					var sibling = siblings[j];
					if (sibling !== parent && sibling.classList && sibling.classList.contains('haschild') && sibling.classList.contains('mobile-open')) {
						sibling.classList.remove('mobile-open');
					}
				}
				parent.classList.add('mobile-open');
			}
		});

		window.addEventListener('resize', function () {
			if (!mobileMode()) {
				closeMenu();
			}
		});
	}

	var resizePdfEmbeds = function () {
		var selectors = [
			'iframe[src*=".pdf"]',
			'iframe[src*="pdf"]',
			'object[data*=".pdf"]',
			'object[type="application/pdf"]',
			'embed[src*=".pdf"]',
			'embed[type="application/pdf"]'
		];
		var nodes = document.querySelectorAll(selectors.join(','));
		for (var k = 0; k < nodes.length; k++) {
			var node = nodes[k];
			node.style.width = '100%';
			node.style.maxWidth = '100%';
			node.style.boxSizing = 'border-box';
			node.removeAttribute('width');
			var height = Math.max(420, Math.min(window.innerHeight * 0.78, window.innerWidth * 1.35));
			node.style.height = Math.round(height) + 'px';
		}
	};

	var normalizeSpacerCells = function () {
		var cells = document.querySelectorAll('#ja-content td, #ja-content-main td, .ja-content td');
		for (var cellIndex = 0; cellIndex < cells.length; cellIndex++) {
			var cell = cells[cellIndex];
			var plainText = (cell.textContent || '').replace(/\u00a0/g, '').trim();
			if (plainText === '') {
				cell.classList.add('is-spacer-cell');
			}
		}
	};

	resizePdfEmbeds();
	normalizeSpacerCells();
	window.addEventListener('resize', resizePdfEmbeds);
});
</script>

<ul class="no-display">
    <li><a href="<?php echo $this->getCurrentURL();?>#ja-content" title="<?php echo JText::_("SKIP_TO_CONTENT");?>"><?php echo JText::_("SKIP_TO_CONTENT");?></a></li>
</ul>
