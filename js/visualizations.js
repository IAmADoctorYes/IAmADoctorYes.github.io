(function () {
    'use strict';

    var container = document.getElementById('viz-grid');
    var statusEl = document.getElementById('viz-status');
    var filterRow = document.getElementById('viz-filters');
    if (!container) return;

    var allItems = [];
    var activeFilter = 'all';

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function typeLabel(type) {
        if (type === 'p5js') return 'p5.js sketch';
        if (type === 'map') return 'Interactive map';
        return type || 'Visualization';
    }

    function typeIcon(type) {
        if (type === 'p5js') return 'bi-circle-square';
        if (type === 'map') return 'bi-map';
        return 'bi-display';
    }

    function buildCard(item) {
        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        var imgHtml = item.thumbnail
            ? '<img src="' + escapeHtml(item.thumbnail) + '" alt="' + escapeHtml(item.title || '') + '" loading="lazy" class="viz-card-img">'
            : '<div class="viz-card-placeholder"><i class="bi ' + typeIcon(item.type) + '"></i></div>';

        var actionHtml = '';
        if (item.embed && item.url) {
            actionHtml = '<button class="btn btn-primary viz-embed-btn" data-url="' + escapeHtml(item.url) + '">Open <i class="bi bi-play-circle"></i></button>';
        } else if (item.url) {
            actionHtml = '<a href="' + escapeHtml(item.url) + '" class="btn btn-primary" target="_blank" rel="noopener">Open <i class="bi bi-box-arrow-up-right"></i></a>';
        } else {
            actionHtml = '<span class="viz-coming-soon small muted">Coming soon</span>';
        }

        return [
            '<div class="viz-card" data-type="' + escapeHtml(item.type || '') + '">',
            imgHtml,
            '  <div class="viz-card-body">',
            '    <div class="viz-card-meta">',
            '      <i class="bi ' + typeIcon(item.type) + '"></i>',
            '      <span class="small muted">' + escapeHtml(typeLabel(item.type)) + '</span>',
            '    </div>',
            '    <h3 class="viz-card-title">' + escapeHtml(item.title || 'Untitled') + '</h3>',
            item.description ? '<p class="viz-card-desc">' + escapeHtml(item.description) + '</p>' : '',
            tags ? '<div class="viz-card-tags">' + tags + '</div>' : '',
            '    <div class="viz-card-actions">' + actionHtml + '</div>',
            '  </div>',
            '</div>'
        ].join('\n');
    }

    function render(items) {
        var filtered = activeFilter === 'all'
            ? items
            : items.filter(function (v) { return v.type === activeFilter; });

        if (!filtered.length) {
            container.innerHTML = '<p class="empty-state">No visualizations in this category yet.</p>';
            if (statusEl) statusEl.textContent = '';
            return;
        }
        container.innerHTML = filtered.map(buildCard).join('');
        if (statusEl) statusEl.textContent = filtered.length + ' visualization(s)';

        /* wire up embed buttons */
        container.querySelectorAll('.viz-embed-btn').forEach(function (btn, i) {
            btn.addEventListener('click', function () {
                var url = btn.getAttribute('data-url');
                var card = btn.closest('.viz-card');
                if (!card || !url) return;
                var existing = card.querySelector('.viz-embed-frame');
                if (existing) { existing.remove(); btn.textContent = 'Open'; return; }
                var frame = document.createElement('iframe');
                frame.src = url;
                frame.className = 'viz-embed-frame';
                frame.setAttribute('allowfullscreen', '');
                frame.setAttribute('loading', 'lazy');
                card.querySelector('.viz-card-placeholder, .viz-card-img').after(frame);
                btn.innerHTML = 'Close <i class="bi bi-x-circle"></i>';
            });
        });
    }

    function setupFilters(items) {
        if (!filterRow) return;
        var types = [];
        items.forEach(function (v) {
            if (v.type && types.indexOf(v.type) === -1) types.push(v.type);
        });
        if (types.length < 2) { filterRow.style.display = 'none'; return; }

        var html = '<button class="shop-filter-btn active" data-filter="all">All</button>';
        types.forEach(function (t) {
            html += '<button class="shop-filter-btn" data-filter="' + escapeHtml(t) + '">' + escapeHtml(typeLabel(t)) + '</button>';
        });
        filterRow.innerHTML = html;

        filterRow.addEventListener('click', function (e) {
            var btn = e.target.closest('.shop-filter-btn');
            if (!btn) return;
            activeFilter = btn.getAttribute('data-filter');
            filterRow.querySelectorAll('.shop-filter-btn').forEach(function (b) {
                b.classList.toggle('active', b === btn);
            });
            render(allItems);
        });
    }

    fetch('/assets/visualizations.json')
        .then(function (res) {
            if (!res.ok) throw new Error(res.status);
            return res.json();
        })
        .then(function (items) {
            allItems = Array.isArray(items) ? items : [];
            setupFilters(allItems);
            render(allItems);
        })
        .catch(function () {
            container.innerHTML = '<p class="empty-state">Could not load visualizations. Check back soon.</p>';
            if (statusEl) statusEl.textContent = '';
        });
})();
