/**
 * Homegrown Spirits — Homepage Featured Products JS
 * Loads products.json and renders featured items.
 */
(function () {
    'use strict';

    var grid = document.getElementById('featured-grid');
    if (!grid) return;

    function esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function buildCard(item) {
        var imgHtml = item.image
            ? '<img src="' + esc(item.image) + '" alt="' + esc(item.title||'') + '" loading="lazy">'
            : '<div class="product-card-placeholder"><i class="bi bi-image"></i></div>';

        var price = parseFloat(item.price) || 0;
        var priceHtml = price ? '<span class="product-price">$' + price.toFixed(2) + '</span>' : '';

        var artistLink = item.artist
            ? '<a href="/artist/' + esc(item.artist) + '.html">by ' + esc(item.artistName || item.artist) + '</a>'
            : '';

        return [
            '<div class="product-card">',
            imgHtml,
            '<div class="product-info">',
            '  <div class="product-header">',
            '    <h3 class="product-title">' + esc(item.title || 'Untitled') + '</h3>',
            priceHtml,
            '  </div>',
            artistLink ? '  <p class="product-byline">' + artistLink + '</p>' : '',
            item.description ? '  <p class="product-desc">' + esc(item.description) + '</p>' : '',
            '  <div class="product-actions">',
            '    <a href="/catalog.html" class="btn btn-sm">See in Catalog</a>',
            '  </div>',
            '</div>',
            '</div>'
        ].join('\n');
    }

    fetch('/assets/products.json')
        .then(function (r) { if (!r.ok) throw r; return r.json(); })
        .then(function (items) {
            var featured = items.filter(function (p) { return p.featured; });
            if (!featured.length) featured = items.slice(0, 4);
            grid.innerHTML = featured.map(buildCard).join('');
        })
        .catch(function () {
            grid.innerHTML = '<div class="empty-state"><p>Products loading...</p></div>';
        });
})();
