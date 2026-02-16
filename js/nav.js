document.addEventListener('DOMContentLoaded', function() {
    var menuToggle = document.querySelector('.menu-toggle');
    var navLinks = document.querySelector('.nav-links');
    var nav = document.querySelector('nav');
    var mediaQuery = window.matchMedia('(max-width: 768px)');
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function setMenuState(isOpen) {
        if (!menuToggle || !navLinks) {
            return;
        }

        navLinks.classList.toggle('active', isOpen);
        navLinks.hidden = !isOpen;
        menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }

    function closeMenu(returnFocus) {
        if (!menuToggle || !navLinks) {
            return;
        }

        setMenuState(false);
        if (returnFocus) {
            menuToggle.focus();
        }
    }

    if (menuToggle && navLinks) {
        if (mediaQuery.matches) {
            navLinks.hidden = true;
        }

        menuToggle.addEventListener('click', function() {
            var isOpen = !navLinks.classList.contains('active');
            setMenuState(isOpen);
        });

        navLinks.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                closeMenu(false);
            });
        });

        document.addEventListener('click', function(event) {
            if (!mediaQuery.matches || !navLinks.classList.contains('active')) {
                return;
            }
            if (!nav.contains(event.target)) {
                closeMenu(false);
            }
        });

        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && navLinks.classList.contains('active')) {
                closeMenu(true);
            }
        });

        window.addEventListener('resize', function() {
            if (mediaQuery.matches) {
                if (!navLinks.classList.contains('active')) {
                    navLinks.hidden = true;
                }
                return;
            }
            navLinks.hidden = false;
            navLinks.classList.remove('active');
            menuToggle.setAttribute('aria-expanded', 'false');
        });
    }

    function normalizedRoute(pathname) {
        var cleanedPath = pathname.replace(/\/index\.html$/i, '/');
        var routeMap = {
            '/': 'home',
            '/index.html': 'home',
            '/pages/my-work.html': 'my-work',
            '/pages/projects.html': 'my-work',
            '/pages/passion-projects.html': 'passion-projects',
            '/pages/blog.html': 'blog',
            '/pages/about.html': 'about',
            '/pages/music.html': 'music',
            '/pages/shop.html': 'shop',
            '/pages/projects/fish-detection.html': 'my-work'
        };

        return routeMap[cleanedPath] || '';
    }

    var currentRoute = document.body.getAttribute('data-route') || normalizedRoute(window.location.pathname);
    document.querySelectorAll('.nav-links a[data-nav-route]').forEach(function(link) {
        var isActive = link.getAttribute('data-nav-route') === currentRoute;
        link.classList.toggle('active', isActive);
        if (isActive) {
            link.setAttribute('aria-current', 'page');
        } else {
            link.removeAttribute('aria-current');
        }
    });

    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(event) {
            var href = this.getAttribute('href');
            if (href === '#' || href === '') {
                return;
            }

            var target = document.querySelector(href);
            if (!target) {
                return;
            }

            event.preventDefault();
            target.scrollIntoView({
                behavior: prefersReducedMotion ? 'auto' : 'smooth',
                block: 'start'
            });
        });
    });

    if (nav) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 50) {
                nav.style.borderBottomColor = 'rgba(200, 149, 111, 0.2)';
            } else {
                nav.style.borderBottomColor = '';
            }
        });
    }
});
