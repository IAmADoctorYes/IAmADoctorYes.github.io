document.addEventListener('DOMContentLoaded', function() {
    var menuToggle = document.querySelector('.menu-toggle');
    var navLinks = document.querySelector('.nav-links');

    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            var isOpen = navLinks.classList.toggle('active');
            menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
        document.querySelectorAll('.nav-links a').forEach(function(link) {
            link.addEventListener('click', function() {
                navLinks.classList.remove('active');
                menuToggle.setAttribute('aria-expanded', 'false');
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
