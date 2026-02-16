(function () {
    var posts = [];
    var postsContainer = document.getElementById('posts');
    var searchInput = document.getElementById('search');
    var status = document.getElementById('results-status');

    if (!postsContainer || !searchInput || !status) {
        return;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatDate(value) {
        if (!value) {
            return '';
        }

        var date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return '';
        }

        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    function buildCard(post) {
        var tags = Array.isArray(post.tags) ? post.tags : [];
        var tagMarkup = tags.map(function (tag) {
            return '<span class="tag">' + escapeHtml(tag) + '</span>';
        }).join(' ');

        var safeTitle = escapeHtml(post.title || 'Untitled post');
        var safePreview = escapeHtml(post.preview || '');
        var safeSlug = escapeHtml(post.slug || '');
        var formattedDate = formatDate(post.date);

        return [
            '<article class="article-preview">',
                '<h3><a href="blog/' + safeSlug + '">' + safeTitle + '</a></h3>',
                '<div class="preview-meta">',
                    formattedDate ? '<span><i class="bi bi-calendar3"></i> ' + formattedDate + '</span>' : '',
                    tags.length ? '<span><i class="bi bi-tags"></i> ' + tags.length + ' tag(s)</span>' : '<span><i class="bi bi-tags"></i> No tags</span>',
                '</div>',
                '<p>' + safePreview + '...</p>',
                tagMarkup ? '<div class="article-tags">' + tagMarkup + '</div>' : '',
                '<a class="read-more" href="blog/' + safeSlug + '">Read article <i class="bi bi-arrow-right"></i></a>',
            '</article>'
        ].join('');
    }

    function setStatus(resultCount, query) {
        if (query) {
            status.textContent = resultCount + ' result(s) for "' + query + '"';
            return;
        }

        status.textContent = resultCount + ' total article(s)';
    }

    function render(list, query) {
        if (!list.length) {
            postsContainer.innerHTML = '<p class="empty-state">No posts found. Try a broader search or check blog/readme.md for indexing setup.</p>';
            setStatus(0, query);
            return;
        }

        postsContainer.innerHTML = list.map(buildCard).join('');
        setStatus(list.length, query);
    }

    function filterPosts(query) {
        if (!query) {
            render(posts, '');
            return;
        }

        var normalizedQuery = query.toLowerCase();
        var filtered = posts.filter(function (post) {
            var title = String(post.title || '').toLowerCase();
            var preview = String(post.preview || '').toLowerCase();
            var tags = Array.isArray(post.tags) ? post.tags.join(' ').toLowerCase() : '';
            return title.includes(normalizedQuery) || preview.includes(normalizedQuery) || tags.includes(normalizedQuery);
        });

        render(filtered, query);
    }

    fetch('../assets/search-index.json')
        .then(function (response) {
            if (!response.ok) {
                throw new Error('Failed to load search index');
            }

            return response.json();
        })
        .then(function (data) {
            posts = Array.isArray(data) ? data : [];
            render(posts, '');
        })
        .catch(function () {
            postsContainer.innerHTML = '<p class="empty-state">Search index unavailable. Run scripts/sync-google-docs.py to regenerate assets/search-index.json.</p>';
            status.textContent = 'Search index unavailable';
        });

    searchInput.addEventListener('input', function (event) {
        filterPosts(event.target.value.trim());
    });
})();
