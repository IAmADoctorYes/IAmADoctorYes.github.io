/**
 * Homegrown Spirits — Artist Page JS
 * Reads data-artist-id from the body element, loads that artist's
 * profile from artists.json and their products from products.json.
 */
(function () {
    'use strict';

    var PRODUCTS_URL = '/assets/products.json';
    var ARTISTS_URL  = '/assets/artists.json';

    var artistId = document.body.getAttribute('data-artist-id');
    if (!artistId) return;

    var productsGrid  = document.getElementById('artist-products-grid');
    var productCount  = document.getElementById('artist-product-count');
    var profileBlock  = document.getElementById('artist-profile');

    function esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function badgeClass(type) {
        if (type === 'physical') return 'badge badge-amber';
        if (type === 'digital')  return 'badge badge-green';
        if (type === 'print')    return 'badge badge-rust';
        return 'badge';
    }

    function fulfillLabel(f) {
        if (f === 'handmade')  return 'Handmade & shipped by artist';
        if (f === 'printful')  return 'Printed & shipped by Printful';
        if (f === 'redbubble') return 'Fulfilled by Redbubble';
        if (f === 'digital')   return 'Instant digital download';
        return '';
    }

    function buildCard(item) {
        var imgHtml = item.image
            ? '<img src="' + esc(item.image) + '" alt="' + esc(item.title||'') + '" loading="lazy">'
            : '<div class="product-card-placeholder"><i class="bi bi-image"></i></div>';

        var price = parseFloat(item.price) || 0;
        var priceHtml = price ? '<span class="product-price">$' + price.toFixed(2) + '</span>' : '';

        var stockHtml = '';
        if (typeof item.stock === 'number') {
            if (item.stock <= 0) stockHtml = '<span class="product-stock-out">Sold out</span>';
            else if (item.stock <= 3) stockHtml = '<span class="product-stock-low">Only ' + item.stock + ' left</span>';
        }

        var variantHtml = (item.variants || []).map(function (v) {
            var opts = (v.options || []).map(function (o) {
                return '<option value="' + esc(o) + '">' + esc(o) + '</option>';
            }).join('');
            return '<div class="product-variant">' +
                   '<label class="small muted">' + esc(v.name) + '</label>' +
                   '<select class="variant-select">' + opts + '</select>' +
                   '</div>';
        }).join('');

        var fl = fulfillLabel(item.fulfillment);
        var fulfillHtml = fl ? '<p class="product-fulfill"><i class="bi bi-truck"></i>' + esc(fl) + '</p>' : '';

        var soldOut = typeof item.stock === 'number' && item.stock <= 0;
        var addBtnHtml = (price && !item.link)
            ? '<button class="btn btn-primary btn-sm add-to-cart-btn"' + (soldOut ? ' disabled' : '') + '>' +
              '<i class="bi bi-bag-plus"></i> ' + (soldOut ? 'Sold Out' : 'Add to Cart') + '</button>'
            : '';

        var linkHtml = item.link
            ? '<a href="' + esc(item.link) + '" class="btn btn-sm" target="_blank" rel="noopener">' +
              esc(item.linkLabel || 'View') + ' <i class="bi bi-box-arrow-up-right"></i></a>'
            : '';

        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + esc(t) + '</span>';
        }).join(' ');

        return [
            '<div class="product-card" data-id="' + esc(item.id||'') + '">',
            imgHtml,
            '<div class="product-info">',
            '  <div class="product-header">',
            '    <h3 class="product-title">' + esc(item.title || 'Untitled') + '</h3>',
            priceHtml,
            '  </div>',
            '  <div class="product-meta">',
            item.type ? '    <span class="' + badgeClass(item.type) + '">' + esc(item.type) + '</span>' : '',
            item.medium ? '    <span class="badge">' + esc(item.medium) + '</span>' : '',
            stockHtml,
            '  </div>',
            item.description ? '  <p class="product-desc">' + esc(item.description) + '</p>' : '',
            variantHtml,
            fulfillHtml,
            tags ? '  <div class="tags mb-4">' + tags + '</div>' : '',
            '  <div class="product-actions">',
            addBtnHtml,
            linkHtml,
            '  </div>',
            '</div>',
            '</div>'
        ].join('\n');
    }

    function renderProducts(products) {
        if (!productsGrid) return;
        var artistProducts = products.filter(function (p) { return p.artist === artistId; });
        if (!artistProducts.length) {
            productsGrid.innerHTML = '<div class="empty-state"><i class="bi bi-bag"></i><p>No products listed yet.</p></div>';
        } else {
            /* Featured first */
            artistProducts.sort(function (a, b) {
                var af = a.featured ? 0 : 1, bf = b.featured ? 0 : 1;
                return af - bf || (a.title||'').localeCompare(b.title||'');
            });
            productsGrid.innerHTML = artistProducts.map(buildCard).join('');
        }
        if (productCount) productCount.textContent = artistProducts.length;

        /* Wire up add-to-cart */
        productsGrid.querySelectorAll('.product-card').forEach(function (card) {
            var addBtn = card.querySelector('.add-to-cart-btn');
            if (addBtn) {
                addBtn.addEventListener('click', function () {
                    var productId = card.getAttribute('data-id');
                    var product = products.find(function (p) { return p.id === productId; });
                    if (!product) return;
                    var parts = [];
                    card.querySelectorAll('.variant-select').forEach(function (s) { parts.push(s.value); });
                    if (window.SiteCart) window.SiteCart.add(product, parts.join(' / '));
                });
            }
        });
    }

    function renderProfile(artist) {
        if (!profileBlock || !artist) return;
        var photoHtml = artist.photo
            ? '<img src="' + esc(artist.photo) + '" alt="' + esc(artist.name) + '" class="artist-hero-photo">'
            : '';

        var mediumTags = (artist.mediums || []).map(function (m) {
            return '<span class="badge badge-amber">' + esc(m) + '</span>';
        }).join(' ');

        var socialHtml = '';
        if (artist.social) {
            var links = [];
            if (artist.social.instagram) links.push('<a href="' + esc(artist.social.instagram) + '" target="_blank" rel="noopener"><i class="bi bi-instagram"></i> Instagram</a>');
            if (artist.social.etsy)      links.push('<a href="' + esc(artist.social.etsy) + '" target="_blank" rel="noopener"><i class="bi bi-shop"></i> Etsy</a>');
            if (artist.social.github)    links.push('<a href="' + esc(artist.social.github) + '" target="_blank" rel="noopener"><i class="bi bi-github"></i> GitHub</a>');
            if (artist.website)          links.push('<a href="' + esc(artist.website) + '" target="_blank" rel="noopener"><i class="bi bi-globe"></i> Website</a>');
            if (links.length) socialHtml = '<div class="artist-social">' + links.join('') + '</div>';
        }

        profileBlock.innerHTML = [
            '<div class="artist-hero">',
            photoHtml ? '  <div>' + photoHtml + '</div>' : '',
            '  <div>',
            '    <h1 class="artist-hero-name">' + esc(artist.name) + '</h1>',
            artist.tagline ? '    <p class="artist-hero-tagline">' + esc(artist.tagline) + '</p>' : '',
            artist.bio ? '    <p class="artist-hero-bio">' + esc(artist.bio) + '</p>' : '',
            '    <div class="artist-medium-tags">' + mediumTags + '</div>',
            artist.location ? '    <div class="artist-hero-meta"><span><i class="bi bi-geo-alt"></i>' + esc(artist.location) + '</span></div>' : '',
            socialHtml,
            '  </div>',
            '</div>'
        ].join('\n');
    }

    /* ── INIT ────────────────────────────────────────────────── */
    Promise.all([
        fetch(PRODUCTS_URL).then(function (r) { if (!r.ok) throw r; return r.json(); }),
        fetch(ARTISTS_URL).then(function (r) { if (!r.ok) throw r; return r.json(); })
    ]).then(function (data) {
        var products = Array.isArray(data[0]) ? data[0] : [];
        var artists  = Array.isArray(data[1]) ? data[1] : [];
        var artist   = artists.find(function (a) { return a.id === artistId; });
        renderProfile(artist);
        renderProducts(products);
    }).catch(function () {
        if (productsGrid) productsGrid.innerHTML = '<div class="empty-state"><p>Could not load products.</p></div>';
    });
})();
