(function () {
    'use strict';

    var grid = document.getElementById('product-grid');
    var statusEl = document.getElementById('shop-status');
    var filterRow = document.getElementById('shop-filters');
    if (!grid) return;

    var allProducts = [];
    var activeFilter = 'all';

    /* -------------------------------------------------------
       LIGHTBOX (product image zoom)
       ------------------------------------------------------- */
    var lightbox = document.createElement('div');
    lightbox.className = 'gallery-lightbox';
    lightbox.hidden = true;
    lightbox.setAttribute('role', 'dialog');
    lightbox.setAttribute('aria-label', 'Product image');
    lightbox.innerHTML = [
        '<div class="gallery-lightbox-inner">',
        '  <button class="gallery-lightbox-close" aria-label="Close">&times;</button>',
        '  <img class="gallery-lightbox-img" src="" alt="">',
        '  <div class="gallery-lightbox-info">',
        '    <h3 class="gallery-lightbox-title"></h3>',
        '    <p class="gallery-lightbox-desc"></p>',
        '  </div>',
        '</div>'
    ].join('\n');
    document.body.appendChild(lightbox);

    var lbImg = lightbox.querySelector('.gallery-lightbox-img');
    var lbTitle = lightbox.querySelector('.gallery-lightbox-title');
    var lbDesc = lightbox.querySelector('.gallery-lightbox-desc');
    var lbClose = lightbox.querySelector('.gallery-lightbox-close');
    var currentProductIndex = -1;
    var currentProductList = [];

    function showProduct(item) {
        lbImg.src = item.image || '';
        lbImg.alt = item.title || '';
        lbTitle.textContent = item.title || '';
        lbDesc.textContent = (item.description || '') + (item.price ? ' — $' + parseFloat(item.price).toFixed(2) : '');
    }

    function openProductLightbox(item, list, index) {
        currentProductList = list || allProducts;
        currentProductIndex = typeof index === 'number' ? index : currentProductList.indexOf(item);
        showProduct(item);
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
        lbClose.focus();
    }

    function closeProductLightbox() {
        lightbox.hidden = true;
        document.body.style.overflow = '';
    }

    lbClose.addEventListener('click', closeProductLightbox);
    lightbox.addEventListener('click', function (e) {
        if (e.target === lightbox) closeProductLightbox();
    });
    document.addEventListener('keydown', function (e) {
        if (lightbox.hidden) return;
        if (e.key === 'Escape') { closeProductLightbox(); return; }
        if (e.key === 'ArrowRight' && currentProductList.length) {
            currentProductIndex = (currentProductIndex + 1) % currentProductList.length;
            showProduct(currentProductList[currentProductIndex]);
        }
        if (e.key === 'ArrowLeft' && currentProductList.length) {
            currentProductIndex = (currentProductIndex - 1 + currentProductList.length) % currentProductList.length;
            showProduct(currentProductList[currentProductIndex]);
        }
    });

    /* -------------------------------------------------------
       HELPERS
       ------------------------------------------------------- */
    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function badgeClass(type) {
        if (type === 'physical') return 'product-badge product-badge-physical';
        if (type === 'digital') return 'product-badge product-badge-digital';
        if (type === 'custom') return 'product-badge product-badge-custom';
        if (type === 'printful') return 'product-badge product-badge-digital';
        return 'product-badge';
    }

    function fulfillmentLabel(f) {
        if (f === 'printful') return 'Printed & shipped by Printful';
        if (f === 'digital') return 'Instant digital download';
        return '';
    }

    /* -------------------------------------------------------
       CARD BUILDER
       ------------------------------------------------------- */
    function buildCard(item) {
        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        var imgHtml = item.image
            ? '<img src="' + escapeHtml(item.image) + '" alt="' + escapeHtml(item.title || '') + '" loading="lazy" class="product-img-clickable" style="cursor:zoom-in">'
            : '';

        var price = parseFloat(item.price) || 0;
        var priceHtml = price ? '<span class="product-price">$' + price.toFixed(2) + '</span>' : '';

        /* Stock indicator */
        var stockHtml = '';
        if (typeof item.stock === 'number') {
            if (item.stock <= 0) {
                stockHtml = '<span class="product-stock product-stock-out">Sold out</span>';
            } else if (item.stock <= 3) {
                stockHtml = '<span class="product-stock product-stock-low">Only ' + item.stock + ' left</span>';
            }
        }

        /* Variant selector */
        var variantHtml = '';
        if (item.variants && item.variants.length) {
            item.variants.forEach(function (v) {
                var options = (v.options || []).map(function (opt) {
                    return '<option value="' + escapeHtml(opt) + '">' + escapeHtml(opt) + '</option>';
                }).join('');
                variantHtml +=
                    '<div class="product-variant">' +
                    '  <label class="small muted">' + escapeHtml(v.name) + '</label>' +
                    '  <select class="variant-select" data-variant-name="' + escapeHtml(v.name) + '">' +
                    options + '</select>' +
                    '</div>';
            });
        }

        /* Fulfillment note */
        var fulfillHtml = '';
        var fl = fulfillmentLabel(item.fulfillment);
        if (fl) {
            fulfillHtml = '<p class="product-fulfill small muted"><i class="bi bi-truck"></i> ' + escapeHtml(fl) + '</p>';
        }

        /* Add to cart button */
        var soldOut = typeof item.stock === 'number' && item.stock <= 0;
        var addBtnHtml = price
            ? '<button class="btn btn-primary add-to-cart-btn"' + (soldOut ? ' disabled' : '') + '>' +
              '<i class="bi bi-bag-plus"></i> ' + (soldOut ? 'Sold Out' : 'Add to Cart') + '</button>'
            : '';

        /* External link */
        var linkHtml = '';
        if (item.link) {
            var linkLabel = item.linkLabel || 'View';
            linkHtml = '<a href="' + escapeHtml(item.link) + '" class="btn btn-secondary" target="_blank" rel="noopener">' +
                       escapeHtml(linkLabel) + ' <i class="bi bi-box-arrow-up-right"></i></a>';
        }

        return [
            '<div class="product-card" data-type="' + escapeHtml(item.type || '') + '">',
            imgHtml,
            '  <div class="product-info">',
            '    <div class="product-header">',
            '      <h3 class="product-title">' + escapeHtml(item.title || 'Untitled') + '</h3>',
            priceHtml,
            '    </div>',
            '    <div class="product-meta">',
            item.type ? '      <span class="' + badgeClass(item.type) + '">' + escapeHtml(item.type) + '</span>' : '',
            stockHtml,
            '    </div>',
            item.description ? '    <p class="product-desc">' + escapeHtml(item.description) + '</p>' : '',
            variantHtml,
            fulfillHtml,
            tags ? '    <div class="gallery-tags" style="margin-bottom:0.75rem">' + tags + '</div>' : '',
            '    <div class="product-actions">',
            addBtnHtml,
            linkHtml,
            '    </div>',
            '  </div>',
            '</div>'
        ].join('\n');
    }

    /* -------------------------------------------------------
       RENDER
       ------------------------------------------------------- */
    function render(items) {
        var filtered = activeFilter === 'all'
            ? items
            : items.filter(function (p) { return p.type === activeFilter; });

        if (!filtered.length) {
            grid.innerHTML = '<p class="shop-empty">No products in this category yet.</p>';
            if (statusEl) statusEl.textContent = '0 products';
            return;
        }
        grid.innerHTML = filtered.map(buildCard).join('');
        if (statusEl) statusEl.textContent = filtered.length + ' product(s)';

        /* Wire up image lightbox clicks */
        grid.querySelectorAll('.product-card').forEach(function (card, i) {
            var img = card.querySelector('.product-img-clickable');
            if (img) {
                img.addEventListener('click', function (e) {
                    e.preventDefault();
                    openProductLightbox(filtered[i], filtered, i);
                });
            }

            /* Wire up Add to Cart */
            var addBtn = card.querySelector('.add-to-cart-btn');
            if (addBtn) {
                addBtn.addEventListener('click', function () {
                    var product = filtered[i];
                    var variant = '';
                    var selects = card.querySelectorAll('.variant-select');
                    if (selects.length) {
                        var parts = [];
                        selects.forEach(function (sel) { parts.push(sel.value); });
                        variant = parts.join(' / ');
                    }
                    if (window.SiteCart) {
                        window.SiteCart.add(product, variant);
                    }
                });
            }
        });
    }

    /* -------------------------------------------------------
       FILTERS
       ------------------------------------------------------- */
    function setupFilters(items) {
        if (!filterRow) return;
        var types = [];
        items.forEach(function (p) {
            if (p.type && types.indexOf(p.type) === -1) types.push(p.type);
        });
        if (types.length < 2) {
            filterRow.style.display = 'none';
            return;
        }

        var html = '<button class="shop-filter-btn active" data-filter="all">All</button>';
        types.forEach(function (t) {
            html += '<button class="shop-filter-btn" data-filter="' + escapeHtml(t) + '">'
                + t.charAt(0).toUpperCase() + t.slice(1) + '</button>';
        });
        filterRow.innerHTML = html;

        filterRow.addEventListener('click', function (e) {
            var btn = e.target.closest('.shop-filter-btn');
            if (!btn) return;
            activeFilter = btn.getAttribute('data-filter');
            filterRow.querySelectorAll('.shop-filter-btn').forEach(function (b) {
                b.classList.toggle('active', b === btn);
            });
            render(allProducts);
        });
    }

    /* -------------------------------------------------------
       FETCH & INIT
       ------------------------------------------------------- */
    fetch('/assets/shop.json')
        .then(function (res) {
            if (!res.ok) throw new Error(res.status);
            return res.json();
        })
        .then(function (items) {
            allProducts = items;
            setupFilters(items);
            render(items);
        })
        .catch(function () {
            grid.innerHTML = '<p class="shop-empty">No products listed yet. Check back soon.</p>';
            if (statusEl) statusEl.textContent = '';
        });
})();
