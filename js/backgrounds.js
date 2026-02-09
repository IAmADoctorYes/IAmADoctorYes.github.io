(function() {
    // NASA APOD for dark mode, Bing daily for light mode
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

    function fetchBing(callback) {
        var directUrl = 'https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US';
        var proxyUrl = 'https://corsproxy.io/?' + encodeURIComponent(directUrl);

        function parseBing(data) {
            if (data && data.images && data.images[0]) {
                var img = data.images[0];
                var imgUrl = 'https://www.bing.com' + img.url;
                var title = img.title || img.copyright || 'Bing Image of the Day';
                saveToCache(CACHE_KEY_LIGHT, imgUrl, title, 'Bing', 'https://www.bing.com');
                if (callback) callback(imgUrl, title, 'Bing', 'https://www.bing.com');
            }
        }

        // Try direct first, fall back to CORS proxy
        fetch(directUrl)
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(parseBing)
            .catch(function() {
                fetch(proxyUrl)
                    .then(function(res) {
                        if (!res.ok) throw new Error('HTTP ' + res.status);
                        return res.json();
                    })
                    .then(parseBing)
                    .catch(function() {});
            });
    }

    function applyForTheme(theme) {
        var cacheKey = theme === 'light' ? CACHE_KEY_LIGHT : CACHE_KEY_DARK;
        var cached = loadFromCache(cacheKey);

        if (cached) {
            setBackground(cached.imageUrl);
            setCreditLink(cached.title, cached.source || (theme === 'light' ? 'Bing' : 'NASA APOD'), cached.href || '#');
        } else {
            if (theme === 'light') {
                fetchBing(function(url, title, source, href) {
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
                fetchBing(function() {});
            } else {
                fetchAPOD(function() {});
            }
        }
    }

    window.onThemeChange = function() {
        applyForTheme(getCurrentTheme());
    };

    var theme = getCurrentTheme();
    applyForTheme(theme);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            prefetchOtherTheme(getCurrentTheme());
        });
    } else {
        prefetchOtherTheme(getCurrentTheme());
    }
})();
