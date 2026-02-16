(function() {
    const STORAGE_KEY = 'sullivan-theme';

    function getPreferred() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return saved;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            return 'light';
        }
        return 'dark';
    }

    function apply(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.innerHTML = theme === 'light'
                ? '<i class="bi bi-moon" aria-hidden="true"></i>'
                : '<i class="bi bi-sun" aria-hidden="true"></i>';
            btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
            btn.setAttribute('aria-pressed', theme === 'dark' ? 'false' : 'true');
        }
    }

    function toggle() {
        const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        localStorage.setItem(STORAGE_KEY, next);
        apply(next);
        if (window.onThemeChange) window.onThemeChange(next);
    }

    apply(getPreferred());

    document.addEventListener('DOMContentLoaded', function() {
        apply(getPreferred());

        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggle);
        }

        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function(e) {
                if (!localStorage.getItem(STORAGE_KEY)) {
                    apply(e.matches ? 'light' : 'dark');
                }
            });
        }
    });
})();
