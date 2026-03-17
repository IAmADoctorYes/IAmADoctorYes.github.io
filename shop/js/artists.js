/**
 * Homegrown Spirits — Artists Page JS
 * Loads artists.json + products.json, renders artist cards.
 */
(function () {
    'use strict';

    var grid    = document.getElementById('artists-grid');
    var countEl = document.getElementById('artists-count');
    if (!grid) return;

    function esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function buildArtistCard(artist, productCount) {
        var photoHtml = artist.photo
            ? '<img src="' + esc(artist.photo) + '" alt="' + esc(artist.name) + '" class="artist-card-photo" loading="lazy">'
            : '<div class="artist-card-placeholder"><i class="bi bi-person"></i></div>';

        var mediums = (artist.mediums || []).map(function (m) {
            return '<span class="badge">' + esc(m) + '</span>';
        }).join(' ');

        return [
            '<a href="' + esc(artist.shopPage || ('/artist/' + artist.id + '.html')) + '" class="artist-card">',
            photoHtml,
            '<div class="artist-card-body">',
            '  <h2 class="artist-card-name">' + esc(artist.name) + '</h2>',
            artist.tagline ? '  <p class="artist-card-tagline">' + esc(artist.tagline) + '</p>' : '',
            artist.location ? '  <p class="small muted"><i class="bi bi-geo-alt"></i>' + esc(artist.location) + '</p>' : '',
            mediums ? '  <div class="artist-card-mediums">' + mediums + '</div>' : '',
            '</div>',
            '<div class="artist-card-footer">',
            '  <i class="bi bi-bag"></i>',
            '  ' + productCount + ' product' + (productCount !== 1 ? 's' : ''),
            '  <i class="bi bi-arrow-right" style="margin-left:auto;margin-right:0"></i>',
            '</div>',
            '</a>'
        ].join('\n');
    }

    Promise.all([
        fetch('/assets/artists.json').then(function (r) { if (!r.ok) throw r; return r.json(); }),
        fetch('/assets/products.json').then(function (r) { if (!r.ok) throw r; return r.json(); })
    ]).then(function (data) {
        var artists  = Array.isArray(data[0]) ? data[0] : [];
        var products = Array.isArray(data[1]) ? data[1] : [];

        if (!artists.length) {
            grid.innerHTML = '<div class="empty-state"><i class="bi bi-person-x"></i><p>No artists yet.</p></div>';
            return;
        }

        grid.innerHTML = artists.map(function (artist) {
            var count = products.filter(function (p) { return p.artist === artist.id; }).length;
            return buildArtistCard(artist, count);
        }).join('');

        if (countEl) countEl.textContent = artists.length + ' artist' + (artists.length !== 1 ? 's' : '');
    }).catch(function () {
        grid.innerHTML = '<div class="empty-state"><p>Could not load artists. Check back soon.</p></div>';
    });
})();
