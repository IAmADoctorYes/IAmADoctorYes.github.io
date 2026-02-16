(function () {
    'use strict';

    var container = document.getElementById('track-list');
    var statusEl = document.getElementById('track-status');
    if (!container) return;

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function buildTrack(item) {
        var meta = [];
        if (item.instrument) meta.push(escapeHtml(item.instrument));
        if (item.date) meta.push(escapeHtml(item.date));

        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        var playerHtml = '';
        if (item.embed) {
            playerHtml = '  <div class="track-embed">'
                + '<iframe src="' + escapeHtml(item.embed) + '" '
                + 'frameborder="0" allowfullscreen allow="autoplay; encrypted-media" '
                + 'loading="lazy" title="' + escapeHtml(item.title || 'Embedded player') + '">'
                + '</iframe></div>';
        } else if (item.src) {
            playerHtml = '  <audio controls preload="metadata">'
                + '<source src="' + escapeHtml(item.src) + '" type="audio/mpeg">'
                + 'Your browser does not support audio.</audio>';
        }

        return [
            '<div class="track">',
            '  <span class="track-title">' + escapeHtml(item.title || 'Untitled') + '</span>',
            meta.length
                ? '  <span class="track-meta small muted">' + meta.join(' · ') + '</span>'
                : '',
            item.description
                ? '  <p class="small muted" style="margin-bottom:0.75rem">' + escapeHtml(item.description) + '</p>'
                : '',
            playerHtml,
            tags ? '  <div class="track-tags">' + tags + '</div>' : '',
            '</div>'
        ].join('\n');
    }

    function render(items) {
        if (!items.length) {
            container.innerHTML = '<p class="track-empty">No recordings yet. Check back soon.</p>';
            if (statusEl) statusEl.textContent = 'No recordings available';
            return;
        }
        container.innerHTML = items.map(buildTrack).join('');
        if (statusEl) statusEl.textContent = items.length + ' recording(s)';
    }

    fetch('/assets/music.json')
        .then(function (res) {
            if (!res.ok) throw new Error(res.status);
            return res.json();
        })
        .then(render)
        .catch(function () {
            container.innerHTML = '<p class="track-empty">No recordings yet. Check back soon.</p>';
            if (statusEl) statusEl.textContent = '';
        });
})();
