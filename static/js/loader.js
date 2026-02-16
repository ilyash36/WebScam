/**
 * Плавная загрузка страницы с анимацией.
 * Показывается при первой загрузке сайта (переход извне, прямая ссылка).
 * При навигации внутри сайта анимация не показывается.
 */
(function () {
    'use strict';

    const LOADER_MIN_DURATION = 600;
    const LOADER_MAX_WAIT = 2500;

    const loader = document.getElementById('pageLoader');
    const content = document.getElementById('pageContent');
    const body = document.body;

    if (!loader || !content) {
        return;
    }

    function isNavigationWithinSite() {
        var ref = document.referrer;
        var origin = window.location.origin;
        return ref && ref.indexOf(origin) === 0;
    }

    function skipLoader() {
        document.documentElement.classList.add('skip-loader');
        body.classList.remove('loading');
        content.classList.add('loaded');
    }

    if (isNavigationWithinSite()) {
        skipLoader();
        return;
    }

    let startTime = Date.now();
    let isHidden = false;

    function hideLoader() {
        if (isHidden) return;
        isHidden = true;

        const elapsed = Date.now() - startTime;
        const delay = Math.max(0, LOADER_MIN_DURATION - elapsed);

        setTimeout(function () {
            body.classList.remove('loading');
            loader.classList.add('hidden');
            content.classList.add('loaded');

            setTimeout(function () {
                loader.style.display = 'none';
            }, 600);
        }, delay);
    }

    function init() {
        body.classList.add('loading');

        if (document.readyState === 'complete') {
            hideLoader();
        } else {
            window.addEventListener('load', hideLoader);
        }

        setTimeout(hideLoader, LOADER_MAX_WAIT);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
