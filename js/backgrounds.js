(function() {
    // NASA APOD for dark mode, Unsplash for light mode
    var CACHE_KEY_DARK = 'sullivan-bg-dark';
    var CACHE_KEY_LIGHT = 'sullivan-bg-light';
    var CACHE_DURATION = 1000 * 60 * 60 * 12; // 12 hours

    function getCurrentTheme() {
        var attr = document.documentElement.getAttribute('data-theme');
        if (attr === 'light') return 'light';
        try {
            var saved = localStorage.getItem('sullivan-theme');
            if (saved) return saved;
        } catch (e) {}
        return 'dark';
    }

    function setBackground(url) {
        var img = new Image();
        img.onload = function() {
            document.documentElement.style.setProperty('--bg-image', 'url("' + url + '")');
        };
        img.onerror = function() {};
        img.src = url;
    }

    function setCreditLink(title, source, href) {
        if (!document.body) {
            document.addEventListener('DOMContentLoaded', function() {
                setCreditLink(title, source, href);
            });
            return;
        }
        var credit = document.querySelector('.bg-credit');
        if (!credit) {
            credit = document.createElement('a');
            credit.className = 'bg-credit';
            credit.target = '_blank';
            credit.rel = 'noopener';
            document.body.appendChild(credit);
        }
        credit.textContent = title + ' — ' + source;
        credit.href = href;
    }

    function loadFromCache(key) {
        try {
            var raw = localStorage.getItem(key);
            if (!raw) return null;
            var cached = JSON.parse(raw);
            if (cached && cached.imageUrl && Date.now() - cached.timestamp < CACHE_DURATION) {
                return cached;
            }
        } catch (e) {}
        return null;
    }

    function saveToCache(key, imageUrl, title, source, href) {
        try {
            localStorage.setItem(key, JSON.stringify({
                imageUrl: imageUrl,
                title: title,
                source: source,
                href: href,
                timestamp: Date.now()
            }));
        } catch (e) {}
    }

    try { localStorage.removeItem('sullivan-bg'); } catch (e) {}

    function fetchAPOD(callback) {
        var apiUrl = 'https://api.nasa.gov/planetary/apod?api_key=8dQ1DXwJiWxzb2OAwnAK3iNp8b7N9UMffh63LdpB&thumbs=true';

        fetch(apiUrl)
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function(data) {
                var imgUrl = null;
                if (data.media_type === 'image') {
                    imgUrl = data.hdurl || data.url;
                } else if (data.thumbnail_url) {
                    imgUrl = data.thumbnail_url;
                }
                if (imgUrl) {
                    var title = data.title || 'Astronomy Picture of the Day';
                    saveToCache(CACHE_KEY_DARK, imgUrl, title, 'NASA APOD', 'https://apod.nasa.gov');
                    if (callback) callback(imgUrl, title, 'NASA APOD', 'https://apod.nasa.gov');
                }
            })
            .catch(function() {});
    }

    function fetchUnsplash(callback) {
        // Unsplash random photo API - topics: nature, landscapes
        var apiUrl = 'https://api.unsplash.com/photos/random?topics=nature,landscapes&orientation=landscape&client_id=hVxUw3AI3TR3e25vQ5f9N-vF5cKh8dZJFxXy0kMIFVo';

        fetch(apiUrl)
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function(data) {
                if (data && data.urls && data.urls.regular) {
                    var imgUrl = data.urls.regular;
                    var title = data.description || data.alt_description || 'Nature Photo';
                    var photographer = data.user ? data.user.name : 'Unknown';
                    var credit = photographer + ' on Unsplash';
                    var href = data.links && data.links.html ? data.links.html : 'https://unsplash.com';
                    
                    saveToCache(CACHE_KEY_LIGHT, imgUrl, title, credit, href);
                    if (callback) callback(imgUrl, title, credit, href);
                }
            })
            .catch(function(err) {
                console.warn('Unsplash fetch error:', err);
                // Fallback to a static beautiful landscape
                var fallbackUrl = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?q=80&w=2940&auto=format&fit=crop';
                saveToCache(CACHE_KEY_LIGHT, fallbackUrl, 'Mountain Landscape', 'Unsplash', 'https://unsplash.com');
                if (callback) callback(fallbackUrl, 'Mountain Landscape', 'Unsplash', 'https://unsplash.com');
            });
    }

    function applyForTheme(theme) {
        var cacheKey = theme === 'light' ? CACHE_KEY_LIGHT : CACHE_KEY_DARK;
        var cached = loadFromCache(cacheKey);

        if (cached) {
            setBackground(cached.imageUrl);
            setCreditLink(cached.title, cached.source || (theme === 'light' ? 'Unsplash' : 'NASA APOD'), cached.href || '#');
        } else {
            if (theme === 'light') {
                fetchUnsplash(function(url, title, source, href) {
                    if (getCurrentTheme() === 'light') {
                        setBackground(url);
                        setCreditLink(title, source, href);
                    }
                });
            } else {
                fetchAPOD(function(url, title, source, href) {
                    if (getCurrentTheme() === 'dark') {
                        setBackground(url);
                        setCreditLink(title, source, href);
                    }
                });
            }
        }
    }

    function prefetchOtherTheme(currentTheme) {
        var otherTheme = currentTheme === 'light' ? 'dark' : 'light';
        var otherKey = otherTheme === 'light' ? CACHE_KEY_LIGHT : CACHE_KEY_DARK;
        if (!loadFromCache(otherKey)) {
            if (otherTheme === 'light') {
                fetchUnsplash(function() {});
            } else {
                fetchAPOD(function() {});
            }
        }
    }

    window.onThemeChange = function(newTheme) {
        applyForTheme(newTheme || getCurrentTheme());
    };

    var theme = getCurrentTheme();
    applyForTheme(theme);

    // Fetch both images on load for instant switching
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            var darkCached = loadFromCache(CACHE_KEY_DARK);
            var lightCached = loadFromCache(CACHE_KEY_LIGHT);
            if (!darkCached) fetchAPOD(function() {});
            if (!lightCached) fetchUnsplash(function() {});
        });
    } else {
        var darkCached = loadFromCache(CACHE_KEY_DARK);
        var lightCached = loadFromCache(CACHE_KEY_LIGHT);
        if (!darkCached) fetchAPOD(function() {});
        if (!lightCached) fetchUnsplash(function() {});
    }
})();
