/**
 * Homegrown Spirits — Shop Nav JS
 * Handles mobile hamburger toggle and active nav link highlighting.
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    var menuToggle = document.querySelector('.menu-toggle');
    var navLinks   = document.querySelector('.hs-nav-links');
    var nav        = document.querySelector('.hs-nav');
    var mq         = window.matchMedia('(max-width: 768px)');

    if (menuToggle && navLinks) {
        if (mq.matches) navLinks.hidden = true;

        menuToggle.addEventListener('click', function () {
            var open = navLinks.classList.contains('active');
            navLinks.classList.toggle('active', !open);
            navLinks.hidden = open;
            menuToggle.setAttribute('aria-expanded', !open ? 'true' : 'false');
        });

        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navLinks.classList.remove('active');
                navLinks.hidden = true;
                menuToggle.setAttribute('aria-expanded', 'false');
            });
        });

        document.addEventListener('click', function (e) {
            if (!mq.matches) return;
            if (!nav || nav.contains(e.target)) return;
            navLinks.classList.remove('active');
            navLinks.hidden = true;
            menuToggle.setAttribute('aria-expanded', 'false');
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                navLinks.hidden = true;
                menuToggle.setAttribute('aria-expanded', 'false');
                menuToggle.focus();
            }
        });

        window.addEventListener('resize', function () {
            if (!mq.matches) {
                navLinks.hidden = false;
                navLinks.classList.remove('active');
                menuToggle.setAttribute('aria-expanded', 'false');
            } else if (!navLinks.classList.contains('active')) {
                navLinks.hidden = true;
            }
        });
    }

    /* Highlight active nav link */
    var path = window.location.pathname;
    document.querySelectorAll('.hs-nav-links a[data-nav]').forEach(function (link) {
        var navVal = link.getAttribute('data-nav');
        if (!navVal) return;
        var isActive = (navVal === 'catalog' && path.indexOf('/catalog') !== -1) ||
                       (navVal === 'artists' && path.indexOf('/artists') !== -1) ||
                       (navVal === 'policies' && path.indexOf('/policies') !== -1) ||
                       (navVal === 'index' && (path === '/' || path === '/index.html'));
        link.classList.toggle('active', isActive);
        if (isActive) link.setAttribute('aria-current', 'page');
    });

    /* Scroll shadow on nav */
    if (nav) {
        window.addEventListener('scroll', function () {
            nav.style.borderBottomColor = window.pageYOffset > 30
                ? 'rgba(200, 144, 80, 0.3)'
                : '';
        });
    }
});
