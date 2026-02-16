(function () {
    'use strict';

    var grid = document.getElementById('gallery-grid');
    var statusEl = document.getElementById('gallery-status');
    var filterRow = document.getElementById('gallery-filters');
    if (!grid) return;

    var allItems = [];
    var activeTag = 'all';

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function buildCard(item) {
        var linkOpen = item.link
            ? '<a href="' + escapeHtml(item.link) + '" class="gallery-card-link">'
            : '<div class="gallery-card-link">';
        var linkClose = item.link ? '</a>' : '</div>';

        var tags = (item.tags || []).map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
        }).join(' ');

        return [
            '<figure class="gallery-card" tabindex="0"',
            '  data-title="' + escapeHtml(item.title || '') + '"',
            '  data-description="' + escapeHtml(item.description || '') + '"',
            '  data-src="' + escapeHtml(item.src || '') + '"',
            '  data-link="' + escapeHtml(item.link || '') + '">',
            linkOpen,
            '  <img src="' + escapeHtml(item.src) + '"',
            '       alt="' + escapeHtml(item.alt || item.title || '') + '"',
            '       loading="lazy">',
            '  <figcaption class="gallery-caption">',
            '    <strong>' + escapeHtml(item.title || '') + '</strong>',
            item.description
                ? '<span class="gallery-desc">' + escapeHtml(item.description) + '</span>'
                : '',
            tags ? '<div class="gallery-tags">' + tags + '</div>' : '',
            '  </figcaption>',
            linkClose,
            '</figure>'
        ].join('\n');
    }

    var lightbox = document.createElement('div');
    lightbox.className = 'gallery-lightbox';
    lightbox.hidden = true;
    lightbox.setAttribute('role', 'dialog');
    lightbox.setAttribute('aria-label', 'Image detail');
    lightbox.innerHTML = [
        '<div class="gallery-lightbox-inner">',
        '  <button class="gallery-lightbox-close" aria-label="Close">&times;</button>',
        '  <img class="gallery-lightbox-img" src="" alt="">',
        '  <div class="gallery-lightbox-info">',
        '    <h3 class="gallery-lightbox-title"></h3>',
        '    <p class="gallery-lightbox-desc"></p>',
        '    <a class="gallery-lightbox-link btn btn-primary" href="#" style="display:none">',
        '      View page <i class="bi bi-arrow-right"></i>',
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
    var currentIndex = -1;
    var currentList = [];

    function showItem(item) {
        lbImg.src = item.src || '';
        lbImg.alt = item.alt || item.title || '';
        lbTitle.textContent = item.title || '';
        lbDesc.textContent = item.description || '';
        if (item.link) {
            lbLink.href = item.link;
            lbLink.style.display = '';
        } else {
            lbLink.style.display = 'none';
        }
    }

    function openLightbox(item, list, index) {
        currentList = list || allItems;
        currentIndex = typeof index === 'number' ? index : currentList.indexOf(item);
        showItem(item);
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
        lbClose.focus();
    }

    function closeLightbox() {
        lightbox.hidden = true;
        document.body.style.overflow = '';
    }

    lbClose.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', function (e) {
        if (e.target === lightbox) closeLightbox();
    });
    document.addEventListener('keydown', function (e) {
        if (lightbox.hidden) return;
        if (e.key === 'Escape') { closeLightbox(); return; }
        if (e.key === 'ArrowRight' && currentList.length) {
            currentIndex = (currentIndex + 1) % currentList.length;
            showItem(currentList[currentIndex]);
        }
        if (e.key === 'ArrowLeft' && currentList.length) {
            currentIndex = (currentIndex - 1 + currentList.length) % currentList.length;
            showItem(currentList[currentIndex]);
        }
    });

    function renderGallery(items) {
        var filtered = activeTag === 'all'
            ? items
            : items.filter(function (it) {
                return (it.tags || []).indexOf(activeTag) !== -1;
            });

        if (!filtered.length) {
            grid.innerHTML = '<p class="empty-state">No items match this filter.</p>';
            if (statusEl) statusEl.textContent = '0 items';
            return;
        }
        grid.innerHTML = filtered.map(buildCard).join('');
        if (statusEl) statusEl.textContent = filtered.length + ' item(s)';

        grid.querySelectorAll('.gallery-card').forEach(function (card, i) {
            function open(e) {
                if (e.target.closest('.gallery-card-link') && filtered[i].link) return;
                e.preventDefault();
                openLightbox(filtered[i], filtered, i);
            }
            card.addEventListener('click', open);
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openLightbox(filtered[i], filtered, i);
                }
            });
        });
    }

    function setupFilters(items) {
        if (!filterRow) return;
        var tags = [];
        items.forEach(function (it) {
            (it.tags || []).forEach(function (t) {
                if (tags.indexOf(t) === -1) tags.push(t);
            });
        });
        if (tags.length < 2) {
            filterRow.style.display = 'none';
            return;
        }

        var html = '<button class="shop-filter-btn active" data-filter="all">All</button>';
        tags.forEach(function (t) {
            html += '<button class="shop-filter-btn" data-filter="' + escapeHtml(t) + '">'
                + escapeHtml(t.charAt(0).toUpperCase() + t.slice(1)) + '</button>';
        });
        filterRow.innerHTML = html;

        filterRow.addEventListener('click', function (e) {
            var btn = e.target.closest('.shop-filter-btn');
            if (!btn) return;
            activeTag = btn.getAttribute('data-filter');
            filterRow.querySelectorAll('.shop-filter-btn').forEach(function (b) {
                b.classList.toggle('active', b === btn);
            });
            renderGallery(allItems);
        });
    }

    fetch('/assets/gallery.json')
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            allItems = Array.isArray(data) ? data : [];
            setupFilters(allItems);
            renderGallery(allItems);
        })
        .catch(function (err) {
            console.warn('Gallery load error:', err);
            grid.innerHTML = '<p class="empty-state">Could not load gallery. Check assets/gallery.json.</p>';
        });
})();
