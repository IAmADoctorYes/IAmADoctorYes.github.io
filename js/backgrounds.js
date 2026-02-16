(function() {
    var BG_DARK_PATH = '/assets/backgrounds/bg-dark.jpg';
    var BG_LIGHT_PATH = '/assets/backgrounds/bg-light.jpg';
    var META_DARK_PATH = '/assets/backgrounds/bg-dark.json';
    var META_LIGHT_PATH = '/assets/backgrounds/bg-light.json';
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    function getCurrentTheme() {
        var attr = document.documentElement.getAttribute('data-theme');
        if (attr === 'light') return 'light';
        try {
            var saved = localStorage.getItem('sullivan-theme');
            if (saved) return saved;
        } catch (e) {}
        return 'dark';
    }

    function setBackground(url) {
        var apply = function() {
            document.documentElement.style.setProperty('--bg-image', 'url("' + url + '")');
        };

        if (prefersReducedMotion.matches) {
            apply();
            return;
        }

        var img = new Image();
        img.onload = apply;
        img.onerror = function() {
            console.warn('Background image failed to load:', url);
            apply();
        };
        img.src = url;
    }

    function setCreditLink(title, source, href) {
        if (!document.body) {
            document.addEventListener('DOMContentLoaded', function() {
                setCreditLink(title, source, href);
            });
            return;
        }
        var credit = document.querySelector('.bg-credit');
        if (!credit) {
            credit = document.createElement('a');
            credit.className = 'bg-credit';
            credit.target = '_blank';
            credit.rel = 'noopener';
            document.body.appendChild(credit);
        }
        credit.textContent = title + ' — ' + source;
        credit.href = href;
    }

    function loadMetadata(path, callback) {
        fetch(path)
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function(data) {
                if (callback) callback(data);
            })
            .catch(function(err) {
                console.warn('Metadata fetch error:', err);
                if (callback) callback(null);
            });
    }

    function applyForTheme(theme) {
        var bgPath = theme === 'light' ? BG_LIGHT_PATH : BG_DARK_PATH;
        var metaPath = theme === 'light' ? META_LIGHT_PATH : META_DARK_PATH;

        var cacheBust = '?t=' + Math.floor(Date.now() / (1000 * 60 * 60 * 12));
        setBackground(bgPath + cacheBust);

        loadMetadata(metaPath, function(meta) {
            if (meta) {
                setCreditLink(meta.title || 'Background Image', meta.source || 'Unknown', meta.href || '#');
            }
        });
    }

    window.onThemeChange = function(newTheme) {
        applyForTheme(newTheme || getCurrentTheme());
    };

    applyForTheme(getCurrentTheme());
})();
