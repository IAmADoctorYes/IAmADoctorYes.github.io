/**
 * Homegrown Spirits — Catalog JS
 * Loads products.json + artists.json, renders filterable/sortable product grid.
 * Filters: artist, medium, fulfillment type, price range
 * Sort: featured, price asc/desc, name asc
 */
(function () {
    'use strict';

    /* ── CONFIG ──────────────────────────────────────────────── */
    var PRODUCTS_URL = '/assets/products.json';
    var ARTISTS_URL  = '/assets/artists.json';

    /* ── STATE ───────────────────────────────────────────────── */
    var allProducts = [];
    var allArtists  = [];
    var filters = {
        search:     '',
        artists:    [],   /* array of artist IDs */
        mediums:    [],   /* array of medium strings */
        types:      [],   /* array of type strings: physical, digital, print */
        priceRange: null  /* null | 'under15' | '15-30' | '30-60' | 'over60' */
    };
    var sortMode = 'featured';

    /* ── DOM REFS ────────────────────────────────────────────── */
    var grid         = document.getElementById('catalog-grid');
    var countEl      = document.getElementById('catalog-count');
    var activeFiltersEl = document.getElementById('active-filters');
    var searchInput  = document.getElementById('catalog-search');
    var sortSelect   = document.getElementById('catalog-sort');
    var filterSidebar = document.getElementById('filter-sidebar');
    var mobileToggle = document.getElementById('mobile-filter-toggle');
    if (!grid) return;

    /* ── ESCAPE HTML ─────────────────────────────────────────── */
    function esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    /* ── FILTERING LOGIC ─────────────────────────────────────── */
    function matchesFilters(p) {
        /* Search */
        if (filters.search) {
            var q = filters.search.toLowerCase();
            var haystack = [p.title, p.description, p.artistName, p.medium, p.category]
                .concat(p.tags || []).join(' ').toLowerCase();
            if (haystack.indexOf(q) === -1) return false;
        }

        /* Artist */
        if (filters.artists.length && filters.artists.indexOf(p.artist) === -1) return false;

        /* Medium */
        if (filters.mediums.length && filters.mediums.indexOf(p.medium) === -1) return false;

        /* Type */
        if (filters.types.length && filters.types.indexOf(p.type) === -1) return false;

        /* Price range */
        if (filters.priceRange && p.price > 0) {
            var pr = filters.priceRange;
            var price = parseFloat(p.price) || 0;
            if (pr === 'under15'  && price >= 15) return false;
            if (pr === '15-30'    && (price < 15 || price >= 30)) return false;
            if (pr === '30-60'    && (price < 30 || price >= 60)) return false;
            if (pr === 'over60'   && price < 60) return false;
        }
        return true;
    }

    function sortProducts(items) {
        var arr = items.slice();
        if (sortMode === 'featured') {
            arr.sort(function (a, b) {
                var af = a.featured ? 0 : 1;
                var bf = b.featured ? 0 : 1;
                return af - bf || (a.title || '').localeCompare(b.title || '');
            });
        } else if (sortMode === 'price-asc') {
            arr.sort(function (a, b) { return (a.price || 0) - (b.price || 0); });
        } else if (sortMode === 'price-desc') {
            arr.sort(function (a, b) { return (b.price || 0) - (a.price || 0); });
        } else if (sortMode === 'name-asc') {
            arr.sort(function (a, b) { return (a.title || '').localeCompare(b.title || ''); });
        }
        return arr;
    }

    /* ── BADGE HELPER ────────────────────────────────────────── */
    function badgeClass(type) {
        if (type === 'physical') return 'badge badge-amber';
        if (type === 'digital')  return 'badge badge-green';
        if (type === 'print')    return 'badge badge-rust';
        return 'badge';
    }

    function fulfillLabel(f) {
        if (f === 'handmade') return 'Handmade & shipped by artist';
        if (f === 'printful') return 'Printed & shipped by Printful';
        if (f === 'redbubble') return 'Fulfilled by Redbubble';
        if (f === 'digital')  return 'Instant digital download';
        return '';
    }

    /* ── BUILD PRODUCT CARD ──────────────────────────────────── */
    function buildCard(item) {
        var imgHtml = item.image
            ? '<img src="' + esc(item.image) + '" alt="' + esc(item.title || '') + '" loading="lazy">'
            : '<div class="product-card-placeholder"><i class="bi bi-image"></i></div>';

        var price = parseFloat(item.price) || 0;
        var priceHtml = price ? '<span class="product-price">$' + price.toFixed(2) + '</span>' : '';

        var stockHtml = '';
        if (typeof item.stock === 'number') {
            if (item.stock <= 0) {
                stockHtml = '<span class="product-stock-out">Sold out</span>';
            } else if (item.stock <= 3) {
                stockHtml = '<span class="product-stock-low">Only ' + item.stock + ' left</span>';
            }
        }

        var variantHtml = '';
        (item.variants || []).forEach(function (v) {
            var opts = (v.options || []).map(function (o) {
                return '<option value="' + esc(o) + '">' + esc(o) + '</option>';
            }).join('');
            variantHtml +=
                '<div class="product-variant">' +
                '  <label class="small muted">' + esc(v.name) + '</label>' +
                '  <select class="variant-select" data-variant-name="' + esc(v.name) + '">' + opts + '</select>' +
                '</div>';
        });

        var fl = fulfillLabel(item.fulfillment);
        var fulfillHtml = fl
            ? '<p class="product-fulfill"><i class="bi bi-truck"></i>' + esc(fl) + '</p>'
            : '';

        var soldOut = typeof item.stock === 'number' && item.stock <= 0;
        var addBtnHtml = (price && !item.link)
            ? '<button class="btn btn-primary btn-sm add-to-cart-btn"' + (soldOut ? ' disabled' : '') + '>' +
              '<i class="bi bi-bag-plus"></i> ' + (soldOut ? 'Sold Out' : 'Add to Cart') + '</button>'
            : '';

        var linkHtml = item.link
            ? '<a href="' + esc(item.link) + '" class="btn btn-sm" target="_blank" rel="noopener">' +
              esc(item.linkLabel || 'View') + ' <i class="bi bi-box-arrow-up-right"></i></a>'
            : '';

        var artistLink = item.artist
            ? '<a href="/artist/' + esc(item.artist) + '.html">by ' + esc(item.artistName || item.artist) + '</a>'
            : (item.artistName ? 'by ' + esc(item.artistName) : '');

        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + esc(t) + '</span>';
        }).join(' ');

        return [
            '<div class="product-card" data-id="' + esc(item.id || '') + '"',
            ' data-type="' + esc(item.type || '') + '"',
            ' data-artist="' + esc(item.artist || '') + '">',
            imgHtml,
            '<div class="product-info">',
            '  <div class="product-header">',
            '    <h3 class="product-title">' + esc(item.title || 'Untitled') + '</h3>',
            priceHtml,
            '  </div>',
            artistLink ? '  <p class="product-byline">' + artistLink + '</p>' : '',
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

    /* ── RENDER PRODUCTS ─────────────────────────────────────── */
    function render() {
        var filtered = allProducts.filter(matchesFilters);
        var sorted   = sortProducts(filtered);

        if (!sorted.length) {
            grid.innerHTML = [
                '<div class="empty-state">',
                '  <i class="bi bi-search"></i>',
                '  <p>No products match your filters.</p>',
                '  <button class="btn btn-sm mt-4" onclick="window.HSCatalog.resetFilters()">Reset Filters</button>',
                '</div>'
            ].join('');
        } else {
            grid.innerHTML = sorted.map(buildCard).join('');
        }

        if (countEl) countEl.textContent = sorted.length + ' product' + (sorted.length !== 1 ? 's' : '');

        /* Wire up add-to-cart */
        grid.querySelectorAll('.product-card').forEach(function (card, i) {
            var addBtn = card.querySelector('.add-to-cart-btn');
            if (addBtn) {
                addBtn.addEventListener('click', function () {
                    var productId = card.getAttribute('data-id');
                    var product = allProducts.find(function (p) { return p.id === productId; }) || sorted[i];
                    var parts = [];
                    card.querySelectorAll('.variant-select').forEach(function (sel) { parts.push(sel.value); });
                    var variant = parts.join(' / ');
                    if (window.SiteCart) {
                        window.SiteCart.add(product, variant);
                    }
                });
            }
        });

        renderActiveFilters();
    }

    /* ── ACTIVE FILTER CHIPS ─────────────────────────────────── */
    function renderActiveFilters() {
        if (!activeFiltersEl) return;
        var chips = [];

        filters.artists.forEach(function (id) {
            var artist = allArtists.find(function (a) { return a.id === id; });
            var name = artist ? artist.name : id;
            chips.push({ label: 'Artist: ' + name, clear: function () { removeFromArray(filters.artists, id); } });
        });
        filters.mediums.forEach(function (m) {
            chips.push({ label: 'Medium: ' + m, clear: function () { removeFromArray(filters.mediums, m); } });
        });
        filters.types.forEach(function (t) {
            chips.push({ label: 'Type: ' + t, clear: function () { removeFromArray(filters.types, t); } });
        });
        if (filters.priceRange) {
            var priceLabels = {
                'under15': 'Under $15', '15-30': '$15–$30',
                '30-60': '$30–$60', 'over60': 'Over $60'
            };
            var pr = filters.priceRange;
            chips.push({ label: 'Price: ' + (priceLabels[pr] || pr), clear: function () { filters.priceRange = null; } });
        }
        if (filters.search) {
            var q = filters.search;
            chips.push({ label: 'Search: "' + q + '"', clear: function () {
                filters.search = '';
                if (searchInput) searchInput.value = '';
            }});
        }

        if (!chips.length) {
            activeFiltersEl.innerHTML = '';
            return;
        }

        activeFiltersEl.innerHTML = chips.map(function (chip, i) {
            return '<button class="filter-chip" data-chip-idx="' + i + '">' +
                   esc(chip.label) +
                   ' <i class="bi bi-x"></i></button>';
        }).join('');

        activeFiltersEl.querySelectorAll('.filter-chip').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var idx = parseInt(btn.getAttribute('data-chip-idx'), 10);
                chips[idx].clear();
                rebuildFilterUI();
                render();
            });
        });
    }

    function removeFromArray(arr, val) {
        var i = arr.indexOf(val);
        if (i !== -1) arr.splice(i, 1);
    }

    /* ── BUILD FILTER SIDEBAR ────────────────────────────────── */
    function buildFilters() {
        if (!filterSidebar) return;

        /* Collect unique values */
        var artistIds = [];
        var mediums = [];
        var types = [];

        allProducts.forEach(function (p) {
            if (p.artist && artistIds.indexOf(p.artist) === -1) artistIds.push(p.artist);
            if (p.medium && mediums.indexOf(p.medium) === -1) mediums.push(p.medium);
            if (p.type && types.indexOf(p.type) === -1) types.push(p.type);
        });

        var html = '';

        /* Artist filter */
        if (artistIds.length > 1) {
            html += '<div class="filter-group">';
            html += '<div class="filter-group-title">Artist</div>';
            artistIds.forEach(function (id) {
                var artist = allArtists.find(function (a) { return a.id === id; });
                var name = artist ? artist.name : id;
                var count = allProducts.filter(function (p) { return p.artist === id; }).length;
                html += '<label class="filter-option">' +
                    '<input type="checkbox" class="f-artist" value="' + esc(id) + '"> ' +
                    esc(name) + '<span class="filter-count">' + count + '</span></label>';
            });
            html += '</div>';
        }

        /* Medium filter */
        if (mediums.length > 1) {
            html += '<div class="filter-group">';
            html += '<div class="filter-group-title">Medium</div>';
            mediums.forEach(function (m) {
                var count = allProducts.filter(function (p) { return p.medium === m; }).length;
                html += '<label class="filter-option">' +
                    '<input type="checkbox" class="f-medium" value="' + esc(m) + '"> ' +
                    capitalize(m) + '<span class="filter-count">' + count + '</span></label>';
            });
            html += '</div>';
        }

        /* Type filter */
        if (types.length > 1) {
            html += '<div class="filter-group">';
            html += '<div class="filter-group-title">Type</div>';
            types.forEach(function (t) {
                var count = allProducts.filter(function (p) { return p.type === t; }).length;
                html += '<label class="filter-option">' +
                    '<input type="checkbox" class="f-type" value="' + esc(t) + '"> ' +
                    capitalize(t) + '<span class="filter-count">' + count + '</span></label>';
            });
            html += '</div>';
        }

        /* Price range */
        html += '<div class="filter-group">';
        html += '<div class="filter-group-title">Price</div>';
        html += '<div class="price-options">';
        [
            { val: 'under15', label: 'Under $15' },
            { val: '15-30',   label: '$15 – $30' },
            { val: '30-60',   label: '$30 – $60' },
            { val: 'over60',  label: 'Over $60'  }
        ].forEach(function (pr) {
            html += '<label class="filter-option">' +
                '<input type="radio" name="price-range" class="f-price" value="' + pr.val + '"> ' +
                pr.label + '</label>';
        });
        html += '</div></div>';

        html += '<button class="filter-reset" id="filter-reset-btn">Reset Filters</button>';

        filterSidebar.innerHTML = html;

        /* Wire up checkboxes/radios */
        filterSidebar.querySelectorAll('.f-artist').forEach(function (cb) {
            cb.addEventListener('change', function () {
                var val = cb.value;
                if (cb.checked) {
                    if (filters.artists.indexOf(val) === -1) filters.artists.push(val);
                } else {
                    removeFromArray(filters.artists, val);
                }
                render();
            });
        });
        filterSidebar.querySelectorAll('.f-medium').forEach(function (cb) {
            cb.addEventListener('change', function () {
                var val = cb.value;
                if (cb.checked) {
                    if (filters.mediums.indexOf(val) === -1) filters.mediums.push(val);
                } else {
                    removeFromArray(filters.mediums, val);
                }
                render();
            });
        });
        filterSidebar.querySelectorAll('.f-type').forEach(function (cb) {
            cb.addEventListener('change', function () {
                var val = cb.value;
                if (cb.checked) {
                    if (filters.types.indexOf(val) === -1) filters.types.push(val);
                } else {
                    removeFromArray(filters.types, val);
                }
                render();
            });
        });
        filterSidebar.querySelectorAll('.f-price').forEach(function (rb) {
            rb.addEventListener('change', function () {
                filters.priceRange = rb.checked ? rb.value : null;
                render();
            });
        });

        var resetBtn = document.getElementById('filter-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetFilters);
        }
    }

    function rebuildFilterUI() {
        /* Sync checkboxes/radios to current filter state */
        if (!filterSidebar) return;
        filterSidebar.querySelectorAll('.f-artist').forEach(function (cb) {
            cb.checked = filters.artists.indexOf(cb.value) !== -1;
        });
        filterSidebar.querySelectorAll('.f-medium').forEach(function (cb) {
            cb.checked = filters.mediums.indexOf(cb.value) !== -1;
        });
        filterSidebar.querySelectorAll('.f-type').forEach(function (cb) {
            cb.checked = filters.types.indexOf(cb.value) !== -1;
        });
        filterSidebar.querySelectorAll('.f-price').forEach(function (rb) {
            rb.checked = rb.value === filters.priceRange;
        });
    }

    function resetFilters() {
        filters.search     = '';
        filters.artists    = [];
        filters.mediums    = [];
        filters.types      = [];
        filters.priceRange = null;
        if (searchInput) searchInput.value = '';
        rebuildFilterUI();
        render();
    }

    function capitalize(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    /* ── SEARCH ──────────────────────────────────────────────── */
    if (searchInput) {
        var searchTimer;
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function () {
                filters.search = searchInput.value.trim();
                render();
            }, 200);
        });
    }

    /* ── SORT ────────────────────────────────────────────────── */
    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            sortMode = sortSelect.value;
            render();
        });
    }

    /* ── MOBILE FILTER TOGGLE ────────────────────────────────── */
    if (mobileToggle && filterSidebar) {
        mobileToggle.addEventListener('click', function () {
            filterSidebar.classList.toggle('mobile-open');
            var isOpen = filterSidebar.classList.contains('mobile-open');
            mobileToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            mobileToggle.innerHTML = isOpen
                ? '<i class="bi bi-funnel-fill"></i> Hide Filters'
                : '<i class="bi bi-funnel"></i> Filters';
        });
    }

    /* ── PUBLIC API ──────────────────────────────────────────── */
    window.HSCatalog = { resetFilters: resetFilters };

    /* ── INIT: LOAD DATA ─────────────────────────────────────── */
    Promise.all([
        fetch(PRODUCTS_URL).then(function (r) { if (!r.ok) throw r; return r.json(); }),
        fetch(ARTISTS_URL).then(function (r) { if (!r.ok) throw r; return r.json(); })
    ]).then(function (data) {
        allProducts = Array.isArray(data[0]) ? data[0] : [];
        allArtists  = Array.isArray(data[1]) ? data[1] : [];
        buildFilters();
        render();
    }).catch(function () {
        grid.innerHTML = '<div class="empty-state"><i class="bi bi-exclamation-circle"></i><p>Could not load products. Check back soon.</p></div>';
        if (countEl) countEl.textContent = '';
    });
})();
