(function () {
    'use strict';

    var grid = document.getElementById('product-grid');
    var statusEl = document.getElementById('shop-status');
    var filterRow = document.getElementById('shop-filters');
    if (!grid) return;

    var allProducts = [];
    var activeFilter = 'all';

    /* Lightbox for product images */
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
        '    <a class="gallery-lightbox-link btn btn-primary" href="#" style="display:none" target="_blank" rel="noopener">',
        '      View listing <i class="bi bi-box-arrow-up-right"></i>',
        '    </a>',
        '  </div>',
        '</div>'
    ].join('\n');
    document.body.appendChild(lightbox);

    var lbImg = lightbox.querySelector('.gallery-lightbox-img');
    var lbTitle = lightbox.querySelector('.gallery-lightbox-title');
    var lbDesc = lightbox.querySelector('.gallery-lightbox-desc');
    var lbLink = lightbox.querySelector('.gallery-lightbox-link');
    var lbClose = lightbox.querySelector('.gallery-lightbox-close');
    var currentProductIndex = -1;
    var currentProductList = [];

    function showProduct(item) {
        lbImg.src = item.image || '';
        lbImg.alt = item.title || '';
        lbTitle.textContent = item.title || '';
        lbDesc.textContent = (item.description || '') + (item.price ? ' — ' + item.price : '');
        if (item.link) {
            lbLink.href = item.link;
            lbLink.style.display = '';
        } else {
            lbLink.style.display = 'none';
        }
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

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function badgeClass(type) {
        if (type === 'physical') return 'product-badge product-badge-physical';
        if (type === 'digital') return 'product-badge product-badge-digital';
        if (type === 'custom') return 'product-badge product-badge-custom';
        return 'product-badge';
    }

    function buildCard(item) {
        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        var imgHtml = item.image
            ? '<img src="' + escapeHtml(item.image) + '" alt="' + escapeHtml(item.title || '') + '" loading="lazy" class="product-img-clickable" style="cursor:zoom-in">'
            : '';

        var linkLabel = item.linkLabel || 'View';
        var linkHtml = item.link
            ? '<a href="' + escapeHtml(item.link) + '" class="btn btn-primary" target="_blank" rel="noopener">' + escapeHtml(linkLabel) + ' <i class="bi bi-box-arrow-up-right"></i></a>'
            : '';

        return [
            '<div class="product-card" data-type="' + escapeHtml(item.type || '') + '">',
            imgHtml,
            '  <div class="product-info">',
            '    <div class="product-header">',
            '      <h3 class="product-title">' + escapeHtml(item.title || 'Untitled') + '</h3>',
            item.price ? '      <span class="product-price">' + escapeHtml(item.price) + '</span>' : '',
            '    </div>',
            '    <div class="product-meta">',
            item.type ? '      <span class="' + badgeClass(item.type) + '">' + escapeHtml(item.type) + '</span>' : '',
            '    </div>',
            item.description ? '    <p class="product-desc">' + escapeHtml(item.description) + '</p>' : '',
            tags ? '    <div class="gallery-tags" style="margin-bottom:0.75rem">' + tags + '</div>' : '',
            '    <div class="product-actions">',
            linkHtml,
            '    </div>',
            '  </div>',
            '</div>'
        ].join('\n');
    }

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

        grid.querySelectorAll('.product-card').forEach(function (card, i) {
            var img = card.querySelector('.product-img-clickable');
            if (img) {
                img.addEventListener('click', function (e) {
                    e.preventDefault();
                    openProductLightbox(filtered[i], filtered, i);
                });
            }
        });
    }

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
