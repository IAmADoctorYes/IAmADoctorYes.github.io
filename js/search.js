(function () {
    'use strict';

    var overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Site search');
    overlay.hidden = true;

    overlay.innerHTML = [
        '<div class="search-overlay-inner">',
        '  <div class="search-header">',
        '    <label for="site-search-input" class="visually-hidden">Search the site</label>',
        '    <i class="bi bi-search search-icon"></i>',
        '    <input id="site-search-input" class="search-input" type="search"',
        '           placeholder="Search pages, projects, articles…" autocomplete="off">',
        '    <kbd class="search-kbd">Esc</kbd>',
        '  </div>',
        '  <div class="search-results" id="search-results" role="listbox" aria-label="Search results"></div>',
        '  <p class="search-footer small muted" id="search-status"></p>',
        '</div>'
    ].join('\n');

    document.body.appendChild(overlay);

    var input = document.getElementById('site-search-input');
    var resultsEl = document.getElementById('search-results');
    var statusEl = document.getElementById('search-status');

    var entries = [];
    var loaded = false;

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function categoryLabel(cat) {
        var labels = {
            'home': 'Home',
            'work': 'Professional Work',
            'project-detail': 'Project',
            'projects': 'Projects',
            'article': 'Article',
            'articles': 'Articles',
            'music': 'Music',
            'shop': 'Shop',
            'about': 'About',
            'gallery': 'Gallery',
            'page': 'Page'
        };
        return labels[cat] || cat;
    }

    function resolveHref(href) {
        if (window.location.protocol === 'file:') {
            return href;
        }
        return href;
    }

    function buildResultCard(entry) {
        var tags = (entry.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        return [
            '<a class="search-result-card" href="' + resolveHref(entry.href) + '" role="option">',
            '  <div class="search-result-header">',
            '    <i class="bi ' + escapeHtml(entry.icon || 'bi-file-earmark') + ' search-result-icon"></i>',
            '    <span class="search-result-category">' + escapeHtml(categoryLabel(entry.category)) + '</span>',
            '  </div>',
            '  <h4 class="search-result-title">' + escapeHtml(entry.title) + '</h4>',
            '  <p class="search-result-preview">' + escapeHtml(entry.preview) + '</p>',
            tags ? '  <div class="search-result-tags">' + tags + '</div>' : '',
            '</a>'
        ].join('\n');
    }

    function render(list, query) {
        if (!list.length) {
            resultsEl.innerHTML = '<p class="search-empty">No results found.</p>';
            statusEl.textContent = query ? '0 results for "' + query + '"' : '';
            return;
        }
        resultsEl.innerHTML = list.map(buildResultCard).join('');
        statusEl.textContent = list.length + (query ? ' result(s) for "' + query + '"' : ' page(s) indexed');
    }

    function filter(query) {
        if (!query) {
            render(entries, '');
            return;
        }
        var q = query.toLowerCase();
        var scored = entries.map(function (e) {
            var title = (e.title || '').toLowerCase();
            var preview = (e.preview || '').toLowerCase();
            var tags = (e.tags || []).join(' ').toLowerCase();
            var cat = (e.category || '').toLowerCase();
            var score = 0;
            if (title.includes(q)) score += 10;
            if (cat.includes(q)) score += 5;
            if (tags.includes(q)) score += 3;
            if (preview.includes(q)) score += 1;
            return { entry: e, score: score };
        }).filter(function (s) { return s.score > 0; });

        scored.sort(function (a, b) { return b.score - a.score; });
        render(scored.map(function (s) { return s.entry; }), query);
    }

    function openSearch() {
        overlay.hidden = false;
        document.body.style.overflow = 'hidden';
        input.value = '';
        if (loaded) {
            render(entries, '');
        } else {
            resultsEl.innerHTML = '<p class="search-empty">Loading index…</p>';
        }
        setTimeout(function () { input.focus(); }, 50);
    }

    function closeSearch() {
        overlay.hidden = true;
        document.body.style.overflow = '';
        var toggle = document.querySelector('.site-search-toggle');
        if (toggle) toggle.focus();
    }

    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) closeSearch();
    });

    input.addEventListener('input', function () {
        filter(input.value.trim());
    });

    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (overlay.hidden) { openSearch(); } else { closeSearch(); }
        }
        if (e.key === 'Escape' && !overlay.hidden) {
            closeSearch();
        }
    });

    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.site-search-toggle');
        if (btn) {
            e.preventDefault();
            openSearch();
        }
    });

    var basePath = '/assets/search-index.json';
    fetch(basePath)
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            entries = Array.isArray(data) ? data : [];
            loaded = true;
            if (!overlay.hidden) render(entries, '');
        })
        .catch(function (err) {
            console.warn('Search index load error:', err);
            loaded = true;
            entries = [];
        });
})();
