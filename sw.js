var CACHE_NAME = 'ss-site-v1';
var STATIC_ASSETS = [
    '/',
    '/index.html',
    '/css/main.css',
    '/js/theme.js',
    '/js/nav.js',
    '/js/search.js',
    '/js/backgrounds.js',
    '/js/enhancements.js',
    '/assets/search-index.json'
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(
                names
                    .filter(function (name) { return name !== CACHE_NAME; })
                    .map(function (name) { return caches.delete(name); })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function (event) {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then(function (response) {
                if (response && response.status === 200 && response.type === 'basic') {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) {
                        cache.put(event.request, clone);
                    });
                }
                return response;
            })
            .catch(function () {
                return caches.match(event.request).then(function (cached) {
                    if (cached) return cached;
                    if (event.request.destination === 'document') {
                        return caches.match('/index.html');
                    }
                    return new Response('', { status: 503, statusText: 'Offline' });
                });
            })
    );
});
