document.addEventListener('DOMContentLoaded', function() {
    var menuToggle = document.querySelector('.menu-toggle');
    var navLinks = document.querySelector('.nav-links');

    function closeMenu() {
        if (!menuToggle || !navLinks) return;
        navLinks.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
    }

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', function() {
            var isOpen = navLinks.classList.toggle('active');
            menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        menuToggle.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeMenu();
            }
        });

        navLinks.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeMenu();
                menuToggle.focus();
            }
        });

        document.querySelectorAll('.nav-links a').forEach(function(link) {
            link.addEventListener('click', function() {
                closeMenu();
            });
        });
    }

    var path = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(function(link) {
        var href = link.getAttribute('href');

        var linkPath = href.replace(/\.\.\//g, '').replace(/^\.\//g, '');
        if (path.endsWith(linkPath) || (linkPath === 'index.html' && (path === '/' || path.endsWith('/')))) {
            link.classList.add('active');
        }
    });

    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            var href = this.getAttribute('href');
            if (href !== '#' && href !== '') {
                e.preventDefault();
                var target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    target.setAttribute('tabindex', '-1');
                    target.focus({ preventScroll: true });
                }
            }
        });
    });

    var nav = document.querySelector('nav');
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 50) {
            nav.style.borderBottomColor = 'rgba(200, 149, 111, 0.2)';
        } else {
            nav.style.borderBottomColor = '';
        }
    });
});
