/**
 * Site-wide enhancements loaded on every page:
 *  - Reading time estimates
 *  - Auto-generated sidebar TOC
 *  - Related posts (tag-based)
 *  - Copy-code buttons on <pre> blocks
 *  - Social sharing buttons on articles
 *  - JSON-LD structured data injection
 *  - Auto breadcrumbs
 *  - Back-to-top button
 *  - Reading progress bar
 *  - Scroll-spy TOC highlighting
 *  - Keyboard shortcuts modal
 *  - View Transitions API
 *  - Scroll-reveal animations
 *  - Collapsible sidebar sections
 *  - External link indicators
 *  - Smooth anchor offset
 *  - Color-coded tag pills
 *  - Search keyboard nav
 *  - Image blur-up (progressive load)
 *  - Responsive table wrapper
 *  - Lazy-load sections (IntersectionObserver)
 *  - Page last-updated badge
 *  - Focus-visible rings
 *  - Automatic heading anchors
 *  - Prefetch on hover
 */
(function () {
    'use strict';

    /* -------------------------------------------------------
       1. READING TIME
       ------------------------------------------------------- */
    function injectReadingTime() {
        var content = document.querySelector('.article-content') || document.querySelector('.page-content');
        if (!content) return;

        var text = content.textContent || '';
        var words = text.trim().split(/\s+/).length;
        var minutes = Math.max(1, Math.round(words / 230));

        var metaEl = document.querySelector('.article-meta');
        if (metaEl) {
            var span = document.createElement('span');
            span.innerHTML = '<i class="bi bi-clock"></i> ' + minutes + ' min read';
            metaEl.appendChild(span);
        }
    }

    /* -------------------------------------------------------
       2. AUTO-GENERATE SIDEBAR TOC
       ------------------------------------------------------- */
    function buildAutoToc() {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        var existing = sidebar.querySelector('.toc');
        if (existing) return;

        var main = document.querySelector('.page-content');
        if (!main) return;

        var headings = main.querySelectorAll('h2[id]');
        if (headings.length < 2) return;

        var section = document.createElement('div');
        section.className = 'sidebar-section';
        var h4 = document.createElement('h4');
        h4.textContent = 'On This Page';
        section.appendChild(h4);

        var ul = document.createElement('ul');
        ul.className = 'toc';
        headings.forEach(function (h) {
            var li = document.createElement('li');
            var a = document.createElement('a');
            a.href = '#' + h.id;
            a.textContent = h.textContent.replace(/^#\s*/, '');
            li.appendChild(a);
            ul.appendChild(li);
        });
        section.appendChild(ul);
        sidebar.appendChild(section);
    }

    /* -------------------------------------------------------
       3. RELATED POSTS
       ------------------------------------------------------- */
    function loadRelatedPosts() {
        var article = document.querySelector('.article-content');
        if (!article) return;

        var tagEls = document.querySelectorAll('.article-tags .tag');
        if (!tagEls.length) return;

        var pageTags = [];
        tagEls.forEach(function (el) {
            pageTags.push(el.textContent.trim().toLowerCase());
        });

        var currentHref = window.location.pathname;

        fetch('/assets/search-index.json')
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (entries) {
                var scored = entries
                    .filter(function (e) { return e.href !== currentHref; })
                    .map(function (e) {
                        var eTags = (e.tags || []).map(function (t) { return t.toLowerCase(); });
                        var overlap = pageTags.filter(function (t) { return eTags.indexOf(t) !== -1; }).length;
                        return { entry: e, score: overlap };
                    })
                    .filter(function (s) { return s.score > 0; })
                    .sort(function (a, b) { return b.score - a.score; })
                    .slice(0, 3);

                if (!scored.length) return;

                var section = document.createElement('section');
                section.className = 'section-rule related-posts';
                section.innerHTML = '<h2>Related</h2>';

                var grid = document.createElement('div');
                grid.className = 'auto-grid';
                scored.forEach(function (s) {
                    var e = s.entry;
                    var card = document.createElement('a');
                    card.href = e.href;
                    card.className = 'route-card';
                    card.innerHTML =
                        '<i class="bi ' + (e.icon || 'bi-file-earmark') + ' route-icon"></i>' +
                        '<h3>' + escapeHtml(e.title) + '</h3>' +
                        '<p>' + escapeHtml((e.preview || '').slice(0, 100)) + '</p>';
                    grid.appendChild(card);
                });
                section.appendChild(grid);
                article.after(section);
            })
            .catch(function () { /* silent */ });
    }

    /* -------------------------------------------------------
       7. COPY CODE BUTTON
       ------------------------------------------------------- */
    function addCopyButtons() {
        document.querySelectorAll('pre').forEach(function (pre) {
            if (pre.querySelector('.copy-btn')) return;

            var btn = document.createElement('button');
            btn.className = 'copy-btn';
            btn.setAttribute('aria-label', 'Copy code');
            btn.innerHTML = '<i class="bi bi-clipboard"></i>';
            btn.addEventListener('click', function () {
                var code = pre.querySelector('code');
                var text = code ? code.textContent : pre.textContent;
                navigator.clipboard.writeText(text).then(function () {
                    btn.innerHTML = '<i class="bi bi-check2"></i>';
                    setTimeout(function () {
                        btn.innerHTML = '<i class="bi bi-clipboard"></i>';
                    }, 1500);
                });
            });

            pre.style.position = 'relative';
            pre.appendChild(btn);
        });
    }

    /* -------------------------------------------------------
       8. SOCIAL SHARING BUTTONS
       ------------------------------------------------------- */
    function addShareButtons() {
        var header = document.querySelector('.article-header');
        if (!header) return;

        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent(document.title);

        var div = document.createElement('div');
        div.className = 'share-buttons';
        div.innerHTML =
            '<span class="small muted">Share:</span> ' +
            '<a href="https://twitter.com/intent/tweet?url=' + url + '&text=' + title + '" target="_blank" rel="noopener" class="share-link" aria-label="Share on Twitter"><i class="bi bi-twitter-x"></i></a> ' +
            '<a href="https://www.linkedin.com/sharing/share-offsite/?url=' + url + '" target="_blank" rel="noopener" class="share-link" aria-label="Share on LinkedIn"><i class="bi bi-linkedin"></i></a> ' +
            '<a href="mailto:?subject=' + title + '&body=' + url + '" class="share-link" aria-label="Share via email"><i class="bi bi-envelope"></i></a>';

        header.appendChild(div);
    }

    /* -------------------------------------------------------
       11. JSON-LD STRUCTURED DATA
       ------------------------------------------------------- */
    function injectJsonLd() {
        var route = document.body.getAttribute('data-route') || '';

        var base = {
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            'name': 'Sullivan Steele',
            'url': 'https://www.sullivanrsteele.com'
        };

        if (route === 'about' || route === 'home') {
            base = {
                '@context': 'https://schema.org',
                '@type': 'Person',
                'name': 'Sullivan Steele',
                'url': 'https://www.sullivanrsteele.com',
                'jobTitle': 'Data Scientist',
                'worksFor': { '@type': 'Organization', 'name': 'WorkForce WV' },
                'sameAs': [
                    'https://github.com/IAmADoctorYes',
                    'https://www.linkedin.com/in/sullivan-steele-166102140'
                ]
            };
        }

        var articleHeader = document.querySelector('.article-header');
        if (articleHeader) {
            var dateEl = articleHeader.querySelector('.article-meta span');
            var dateText = dateEl ? dateEl.textContent.replace(/[^\d\-\/]/g, '').trim() : '';
            base = {
                '@context': 'https://schema.org',
                '@type': 'Article',
                'headline': document.title.replace(/ \| Sullivan Steele$/, ''),
                'author': { '@type': 'Person', 'name': 'Sullivan Steele' },
                'publisher': { '@type': 'Person', 'name': 'Sullivan Steele' },
                'url': window.location.href,
                'datePublished': dateText || undefined
            };
        }

        if (route === 'shop') {
            base['@type'] = 'WebPage';
            base['name'] = 'Shop — Sullivan Steele';
        }

        var script = document.createElement('script');
        script.type = 'application/ld+json';
        script.textContent = JSON.stringify(base);
        document.head.appendChild(script);
    }

    /* -------------------------------------------------------
       HELPERS
       ------------------------------------------------------- */
    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* -------------------------------------------------------
       12. AUTO BREADCRUMBS (non-root, non-project pages)
       ------------------------------------------------------- */
    function injectBreadcrumbs() {
        if (document.querySelector('.breadcrumb')) return;

        var path = window.location.pathname;
        if (path === '/' || path === '/index.html') return;

        var routeLabels = {
            'my-work': 'My Work', projects: 'Projects', blog: 'Articles & Reports',
            gallery: 'Gallery', about: 'About', music: 'Music', shop: 'Shop',
            'passion-projects': 'Passion Projects'
        };

        var parts = path.replace(/^\//, '').replace(/\.html$/, '').split('/');
        if (parts[0] === 'pages') parts.shift();
        if (!parts.length) return;

        var main = document.querySelector('.page-content');
        if (!main) return;

        var nav = document.createElement('div');
        nav.className = 'breadcrumb';
        nav.setAttribute('aria-label', 'Breadcrumb');

        var depth = window.location.pathname.split('/').filter(Boolean).length;
        var homeHref = depth <= 2 ? '../index.html' : '../../index.html';
        if (path.indexOf('/pages/') === -1) homeHref = 'index.html';

        nav.innerHTML = '<a href="' + homeHref + '">Home</a>';
        var current = parts[parts.length - 1];
        var label = routeLabels[current] || current.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
        nav.innerHTML += ' <span class="sep">/</span> ' + escapeHtml(label);

        main.insertBefore(nav, main.firstChild);
    }

    /* -------------------------------------------------------
       13. BACK-TO-TOP BUTTON
       ------------------------------------------------------- */
    function createBackToTop() {
        var btn = document.createElement('button');
        btn.className = 'back-to-top';
        btn.setAttribute('aria-label', 'Back to top');
        btn.innerHTML = '<i class="bi bi-chevron-up"></i>';
        btn.hidden = true;
        document.body.appendChild(btn);

        var ticking = false;
        window.addEventListener('scroll', function () {
            if (!ticking) {
                window.requestAnimationFrame(function () {
                    btn.hidden = window.scrollY < 400;
                    ticking = false;
                });
                ticking = true;
            }
        });

        btn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
        });
    }

    /* -------------------------------------------------------
       14. READING PROGRESS BAR
       ------------------------------------------------------- */
    function createProgressBar() {
        var content = document.querySelector('.article-content') || document.querySelector('.page-content');
        if (!content) return;

        var bar = document.createElement('div');
        bar.className = 'reading-progress';
        bar.setAttribute('role', 'progressbar');
        bar.setAttribute('aria-label', 'Reading progress');
        document.body.appendChild(bar);

        var ticking = false;
        window.addEventListener('scroll', function () {
            if (!ticking) {
                window.requestAnimationFrame(function () {
                    var rect = content.getBoundingClientRect();
                    var total = content.scrollHeight - window.innerHeight;
                    var scrolled = -rect.top;
                    var pct = Math.min(100, Math.max(0, (scrolled / total) * 100));
                    bar.style.width = pct + '%';
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    /* -------------------------------------------------------
       15. SCROLL-SPY TOC HIGHLIGHTING
       ------------------------------------------------------- */
    function initScrollSpy() {
        var tocLinks = document.querySelectorAll('.toc a[href^="#"]');
        if (!tocLinks.length) return;

        var sections = [];
        tocLinks.forEach(function (a) {
            var target = document.querySelector(a.getAttribute('href'));
            if (target) sections.push({ el: target, link: a });
        });
        if (!sections.length) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    tocLinks.forEach(function (l) { l.classList.remove('toc-active'); });
                    var match = sections.find(function (s) { return s.el === entry.target; });
                    if (match) match.link.classList.add('toc-active');
                }
            });
        }, { rootMargin: '-20% 0px -60% 0px' });

        sections.forEach(function (s) { observer.observe(s.el); });
    }

    /* -------------------------------------------------------
       16. KEYBOARD SHORTCUTS HELP MODAL
       ------------------------------------------------------- */
    function createShortcutsModal() {
        var overlay = document.createElement('div');
        overlay.className = 'shortcuts-overlay';
        overlay.hidden = true;
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-label', 'Keyboard shortcuts');
        overlay.innerHTML = [
            '<div class="shortcuts-modal">',
            '  <button class="shortcuts-close" aria-label="Close">&times;</button>',
            '  <h2>Keyboard Shortcuts</h2>',
            '  <dl class="shortcuts-list">',
            '    <div><dt><kbd>Ctrl</kbd>+<kbd>K</kbd></dt><dd>Open search</dd></div>',
            '    <div><dt><kbd>Esc</kbd></dt><dd>Close overlay / lightbox</dd></div>',
            '    <div><dt><kbd>←</kbd> <kbd>→</kbd></dt><dd>Navigate lightbox images</dd></div>',
            '    <div><dt><kbd>?</kbd></dt><dd>Show this help</dd></div>',
            '    <div><dt><kbd>T</kbd></dt><dd>Toggle theme</dd></div>',
            '    <div><dt><kbd>H</kbd></dt><dd>Go home</dd></div>',
            '  </dl>',
            '</div>'
        ].join('\n');
        document.body.appendChild(overlay);

        function open()  { overlay.hidden = false; document.body.style.overflow = 'hidden'; }
        function close() { overlay.hidden = true;  document.body.style.overflow = ''; }

        overlay.querySelector('.shortcuts-close').addEventListener('click', close);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close();
        });

        document.addEventListener('keydown', function (e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;

            if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                overlay.hidden ? open() : close();
                return;
            }
            if (!overlay.hidden && e.key === 'Escape') { close(); return; }

            if (overlay.hidden && !e.ctrlKey && !e.metaKey && !e.altKey) {
                if (e.key === 't' || e.key === 'T') {
                    var toggle = document.querySelector('.theme-toggle');
                    if (toggle) toggle.click();
                }
                if (e.key === 'h' || e.key === 'H') {
                    window.location.href = '/';
                }
            }
        });
    }

    /* -------------------------------------------------------
       17. VIEW TRANSITIONS API (progressive enhancement)
       ------------------------------------------------------- */
    function initViewTransitions() {
        /* View Transitions for MPA are handled via CSS:
           @view-transition { navigation: auto; }
           No JS interception needed — the browser handles it natively
           when supported. We only inject the CSS opt-in. */
        if (prefersReducedMotion) return;
        if (!('startViewTransition' in document)) return;

        var style = document.createElement('style');
        style.textContent = '@view-transition { navigation: auto; }';
        document.head.appendChild(style);
    }

    /* -------------------------------------------------------
       18. SCROLL-REVEAL ANIMATIONS
       ------------------------------------------------------- */
    function initScrollReveal() {
        if (prefersReducedMotion) return;

        var revealTargets = document.querySelectorAll(
            '.route-card, .gallery-card, .product-card, .track-card, .section-rule, .blog-card'
        );
        if (!revealTargets.length) return;

        revealTargets.forEach(function (el) { el.classList.add('reveal'); });

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

        revealTargets.forEach(function (el) { observer.observe(el); });
    }

    /* -------------------------------------------------------
       19. COLLAPSIBLE SIDEBAR SECTIONS
       ------------------------------------------------------- */
    function initCollapsibleSidebar() {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        var storageKey = 'sidebar-collapsed';
        var saved = {};
        try { saved = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (e) { /* silent */ }

        sidebar.querySelectorAll('.sidebar-section > h4').forEach(function (h4, i) {
            var key = 'section-' + i;
            var list = h4.nextElementSibling;
            if (!list) return;

            h4.classList.add('sidebar-toggle');
            h4.setAttribute('role', 'button');
            h4.setAttribute('tabindex', '0');
            h4.setAttribute('aria-expanded', saved[key] === false ? 'false' : 'true');

            if (saved[key] === false) {
                list.hidden = true;
                h4.classList.add('collapsed');
            }

            function toggle() {
                var isOpen = !list.hidden;
                list.hidden = isOpen;
                h4.classList.toggle('collapsed', isOpen);
                h4.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
                saved[key] = !isOpen;
                try { localStorage.setItem(storageKey, JSON.stringify(saved)); } catch (e) { /* silent */ }
            }

            h4.addEventListener('click', toggle);
            h4.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
            });
        });
    }

    /* -------------------------------------------------------
       20. EXTERNAL LINK INDICATORS
       Add an icon after links that leave the site.
       ------------------------------------------------------- */
    function markExternalLinks() {
        var host = window.location.hostname;
        document.querySelectorAll('a[href^="http"]').forEach(function (a) {
            try {
                var linkHost = new URL(a.href).hostname;
                if (linkHost === host) return;
            } catch (e) { return; }
            if (a.querySelector('.ext-icon') || a.classList.contains('share-link')) return;
            if (a.closest('nav') || a.closest('footer')) return;
            var icon = document.createElement('i');
            icon.className = 'bi bi-box-arrow-up-right ext-icon';
            icon.setAttribute('aria-hidden', 'true');
            a.appendChild(icon);
            if (!a.getAttribute('rel')) a.setAttribute('rel', 'noopener');
            if (!a.getAttribute('target')) a.setAttribute('target', '_blank');
        });
    }

    /* -------------------------------------------------------
       21. SMOOTH ANCHOR OFFSET
       Offset scroll-to-anchor by nav height so headings
       aren't hidden behind the sticky nav.
       ------------------------------------------------------- */
    function applySmoothAnchorOffset() {
        if (prefersReducedMotion) return;
        document.addEventListener('click', function (e) {
            var link = e.target.closest('a[href^="#"]');
            if (!link) return;
            var id = link.getAttribute('href').slice(1);
            var target = document.getElementById(id);
            if (!target) return;
            e.preventDefault();
            var navH = document.querySelector('nav') ? document.querySelector('nav').offsetHeight : 0;
            var top = target.getBoundingClientRect().top + window.scrollY - navH - 16;
            window.scrollTo({ top: top, behavior: 'smooth' });
            history.pushState(null, '', '#' + id);
        });
    }

    /* -------------------------------------------------------
       22. COLOR-CODED TAG PILLS
       Give each unique tag a deterministic hue so pills
       are visually distinct.
       ------------------------------------------------------- */
    function colorTagPills() {
        var hues = [142, 200, 28, 280, 340, 56, 180, 310, 95, 240];
        function tagHue(tag) {
            var hash = 0;
            for (var i = 0; i < tag.length; i++) hash = ((hash << 5) - hash) + tag.charCodeAt(i);
            return hues[Math.abs(hash) % hues.length];
        }
        document.querySelectorAll('.tag, .filter-btn[data-type]').forEach(function (el) {
            var text = (el.getAttribute('data-type') || el.textContent).trim().toLowerCase();
            if (!text || text === 'all') return;
            var h = tagHue(text);
            el.style.setProperty('--tag-hue', h);
            el.classList.add('tag-colored');
        });
    }

    /* -------------------------------------------------------
       23. SEARCH KEYBOARD NAVIGATION
       Arrow keys + Enter in the search overlay results.
       ------------------------------------------------------- */
    function enhanceSearchKeyNav() {
        var overlay = document.querySelector('.search-overlay');
        if (!overlay) return;

        overlay.addEventListener('keydown', function (e) {
            if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter') return;

            var items = overlay.querySelectorAll('.search-result-card');
            if (!items.length) return;

            var focused = overlay.querySelector('.search-kb-focus');
            var idx = -1;
            items.forEach(function (el, i) { if (el === focused) idx = i; });

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                idx = (idx + 1) % items.length;
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                idx = idx <= 0 ? items.length - 1 : idx - 1;
            } else if (e.key === 'Enter' && focused) {
                e.preventDefault();
                focused.click();
                return;
            }

            if (focused) focused.classList.remove('search-kb-focus');
            items[idx].classList.add('search-kb-focus');
            items[idx].scrollIntoView({ block: 'nearest' });
        });
    }

    /* -------------------------------------------------------
       24. IMAGE BLUR-UP (progressive loading)
       Swap low-res placeholder to high-res on load.
       Requires: <img data-src="hi-res.jpg" src="low-res.jpg" class="blur-up">
       Also lazy-loads any image with data-src.
       ------------------------------------------------------- */
    function initBlurUp() {
        var imgs = document.querySelectorAll('img[data-src]');
        if (!imgs.length) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var img = entry.target;
                var full = img.getAttribute('data-src');
                if (!full) return;
                var loader = new Image();
                loader.onload = function () {
                    img.src = full;
                    img.removeAttribute('data-src');
                    img.classList.add('blur-up-loaded');
                };
                loader.src = full;
                observer.unobserve(img);
            });
        }, { rootMargin: '200px' });

        imgs.forEach(function (img) { observer.observe(img); });
    }

    /* -------------------------------------------------------
       25. RESPONSIVE TABLE WRAPPER
       Wrap bare <table> elements in a scrollable container.
       ------------------------------------------------------- */
    function wrapTables() {
        document.querySelectorAll('.page-content table').forEach(function (table) {
            if (table.parentElement.classList.contains('table-wrap')) return;
            var wrapper = document.createElement('div');
            wrapper.className = 'table-wrap';
            wrapper.setAttribute('role', 'region');
            wrapper.setAttribute('tabindex', '0');
            wrapper.setAttribute('aria-label', 'Scrollable table');
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        });
    }

    /* -------------------------------------------------------
       26. LAZY-LOAD SECTIONS (heavy content)
       Defer rendering of off-screen sections marked with
       data-lazy-section="true" until they scroll near.
       ------------------------------------------------------- */
    function initLazySections() {
        var sections = document.querySelectorAll('[data-lazy-section]');
        if (!sections.length) return;

        sections.forEach(function (sec) { sec.style.contentVisibility = 'auto'; });

        if (!('IntersectionObserver' in window)) {
            sections.forEach(function (sec) { sec.style.contentVisibility = ''; });
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.contentVisibility = '';
                    entry.target.removeAttribute('data-lazy-section');
                    observer.unobserve(entry.target);
                }
            });
        }, { rootMargin: '300px' });

        sections.forEach(function (sec) { observer.observe(sec); });
    }

    /* -------------------------------------------------------
       27. PAGE LAST-UPDATED BADGE
       If the page has a <meta name="last-modified"> or a
       <time data-updated>, show a small "Updated X" badge.
       ------------------------------------------------------- */
    function showLastUpdated() {
        var meta = document.querySelector('meta[name="last-modified"]');
        var time = document.querySelector('time[data-updated]');
        var dateStr = meta ? meta.getAttribute('content') : (time ? time.getAttribute('datetime') || time.textContent : '');
        if (!dateStr) return;

        var d = new Date(dateStr);
        if (isNaN(d)) return;

        var formatted = d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        var badge = document.createElement('span');
        badge.className = 'last-updated-badge small muted';
        badge.innerHTML = '<i class="bi bi-pencil-square"></i> Updated ' + escapeHtml(formatted);

        var target = document.querySelector('.article-meta') || document.querySelector('.hero-sub');
        if (target) target.appendChild(badge);
    }

    /* -------------------------------------------------------
       29. AUTOMATIC HEADING ANCHORS
       Add a clickable # link next to every h2/h3 with an id.
       ------------------------------------------------------- */
    function addHeadingAnchors() {
        document.querySelectorAll('.page-content h2[id], .page-content h3[id]').forEach(function (h) {
            if (h.querySelector('.heading-anchor')) return;
            var a = document.createElement('a');
            a.href = '#' + h.id;
            a.className = 'heading-anchor';
            a.setAttribute('aria-label', 'Link to ' + h.textContent);
            a.textContent = '#';
            h.appendChild(a);
        });
    }

    /* -------------------------------------------------------
       30. PREFETCH ON HOVER
       Preload internal links when the user hovers for > 65 ms
       so navigations feel instant.
       ------------------------------------------------------- */
    function initPrefetch() {
        if (navigator.connection && navigator.connection.saveData) return;

        var prefetched = {};
        var timer = null;

        document.addEventListener('mouseover', function (e) {
            var link = e.target.closest('a[href]');
            if (!link) return;

            var url;
            try { url = new URL(link.href); } catch (err) { return; }
            if (url.origin !== window.location.origin) return;
            if (url.href === window.location.href) return;
            if (prefetched[url.href]) return;
            if (link.target === '_blank' || link.hasAttribute('download')) return;

            timer = setTimeout(function () {
                var el = document.createElement('link');
                el.rel = 'prefetch';
                el.href = url.href;
                el.as = 'document';
                document.head.appendChild(el);
                prefetched[url.href] = true;
            }, 65);
        });

        document.addEventListener('mouseout', function (e) {
            if (e.target.closest('a[href]') && timer) {
                clearTimeout(timer);
                timer = null;
            }
        });
    }

    /* -------------------------------------------------------
       INIT
       ------------------------------------------------------- */
    document.addEventListener('DOMContentLoaded', function () {
        injectReadingTime();
        buildAutoToc();
        loadRelatedPosts();
        addCopyButtons();
        addShareButtons();
        injectJsonLd();
        injectBreadcrumbs();
        createBackToTop();
        createProgressBar();
        initScrollSpy();
        createShortcutsModal();
        initViewTransitions();
        initScrollReveal();
        initCollapsibleSidebar();
        markExternalLinks();
        applySmoothAnchorOffset();
        colorTagPills();
        enhanceSearchKeyNav();
        initBlurUp();
        wrapTables();
        initLazySections();
        showLastUpdated();
        addHeadingAnchors();
        initPrefetch();
    });
})();
