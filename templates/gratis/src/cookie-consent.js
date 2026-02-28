(function () {
  function setCookie(name, value, days) {
    var expires = '';
    if (days) {
      var date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + value + expires + '; path=/; SameSite=Lax';
  }

  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) {
      return parts.pop().split(';').shift();
    }
    return null;
  }

  function hasChoice() {
    return getCookie('cookie_consent_choice') === '1';
  }

  function acceptAll() {
    setCookie('cookie_consent_choice', '1', 180);
    setCookie('cookie_consent_analytics', '1', 180);
    setCookie('cookie_consent_marketing', '1', 180);
    location.reload();
  }

  function rejectNonEssential() {
    setCookie('cookie_consent_choice', '1', 180);
    setCookie('cookie_consent_analytics', '0', 180);
    setCookie('cookie_consent_marketing', '0', 180);
    location.reload();
  }

  function initBanner() {
    var banner = document.getElementById('cookieConsentBanner');
    if (!banner) {
      return;
    }

    if (!hasChoice()) {
      banner.style.display = 'block';
    }

    var acceptBtn = document.getElementById('cookieConsentAccept');
    var rejectBtn = document.getElementById('cookieConsentReject');

    if (acceptBtn) {
      acceptBtn.onclick = function (event) {
        if (event && event.preventDefault) {
          event.preventDefault();
        }
        acceptAll();
      };
    }

    if (rejectBtn) {
      rejectBtn.onclick = function (event) {
        if (event && event.preventDefault) {
          event.preventDefault();
        }
        rejectNonEssential();
      };
    }
  }

  if (window.addEvent) {
    window.addEvent('domready', initBanner);
  } else if (document.addEventListener) {
    document.addEventListener('DOMContentLoaded', initBanner);
  } else {
    window.onload = initBanner;
  }
})();
