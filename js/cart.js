/**
 * Client-side shopping cart backed by localStorage + PayPal Checkout.
 *
 * Features:
 *  - Persistent cart across pages (localStorage)
 *  - Slide-out cart drawer with item management
 *  - Quantity adjustment and removal
 *  - Variant tracking (size, style, etc.)
 *  - Cart badge count in nav
 *  - PayPal Smart Payment Buttons for checkout
 *  - Toast notifications for cart actions
 *
 * Cart items shape:
 *  { id, title, price, image, quantity, variant, fulfillment }
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'ss-cart';
    var cart = loadCart();

    /* -------------------------------------------------------
       PERSISTENCE
       ------------------------------------------------------- */
    function loadCart() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveCart() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
        } catch (e) { /* quota exceeded — silent */ }
    }

    /* -------------------------------------------------------
       CART OPERATIONS
       ------------------------------------------------------- */
    function generateId(title, variant) {
        var base = (title || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');
        return variant ? base + '--' + variant.toLowerCase().replace(/[^a-z0-9]+/g, '-') : base;
    }

    function addItem(product, variant) {
        var id = generateId(product.title, variant);
        var existing = cart.find(function (c) { return c.id === id; });

        if (existing) {
            if (product.stock && existing.quantity >= product.stock) {
                showToast('Only ' + product.stock + ' in stock', 'warning');
                return;
            }
            existing.quantity++;
        } else {
            cart.push({
                id: id,
                title: product.title + (variant ? ' — ' + variant : ''),
                price: parseFloat(product.price) || 0,
                image: product.image || '',
                quantity: 1,
                variant: variant || '',
                fulfillment: product.fulfillment || 'handmade'
            });
        }

        saveCart();
        updateBadge();
        renderDrawer();
        showToast('Added to cart');
    }

    function removeItem(id) {
        cart = cart.filter(function (c) { return c.id !== id; });
        saveCart();
        updateBadge();
        renderDrawer();
    }

    function updateQuantity(id, delta) {
        var item = cart.find(function (c) { return c.id === id; });
        if (!item) return;
        item.quantity = Math.max(1, item.quantity + delta);
        saveCart();
        renderDrawer();
        updateBadge();
    }

    function clearCart() {
        cart = [];
        saveCart();
        updateBadge();
        renderDrawer();
    }

    function cartTotal() {
        return cart.reduce(function (sum, item) {
            return sum + (item.price * item.quantity);
        }, 0);
    }

    function cartCount() {
        return cart.reduce(function (sum, item) {
            return sum + item.quantity;
        }, 0);
    }

    /* -------------------------------------------------------
       NAV CART ICON (injected on every page)
       ------------------------------------------------------- */
    var badge = null;

    function injectCartIcon() {
        var navLinks = document.querySelector('.nav-links');
        if (!navLinks) return;

        var searchToggle = navLinks.querySelector('.site-search-toggle');
        var li = document.createElement('li');
        li.innerHTML =
            '<button class="cart-toggle" aria-label="Open shopping cart">' +
            '  <i class="bi bi-bag"></i>' +
            '  <span class="cart-badge" hidden>0</span>' +
            '</button>';

        if (searchToggle) {
            searchToggle.closest('li').before(li);
        } else {
            navLinks.appendChild(li);
        }

        badge = li.querySelector('.cart-badge');
        li.querySelector('.cart-toggle').addEventListener('click', toggleDrawer);
        updateBadge();
    }

    function updateBadge() {
        if (!badge) return;
        var count = cartCount();
        badge.textContent = count;
        badge.hidden = count === 0;
    }

    /* -------------------------------------------------------
       CART DRAWER
       ------------------------------------------------------- */
    var drawer = null;
    var drawerBody = null;
    var drawerFooter = null;

    function createDrawer() {
        drawer = document.createElement('div');
        drawer.className = 'cart-drawer';
        drawer.hidden = true;
        drawer.setAttribute('role', 'dialog');
        drawer.setAttribute('aria-label', 'Shopping cart');
        drawer.innerHTML = [
            '<div class="cart-drawer-backdrop"></div>',
            '<div class="cart-drawer-panel">',
            '  <div class="cart-drawer-header">',
            '    <h2>Your Cart</h2>',
            '    <button class="cart-drawer-close" aria-label="Close cart">&times;</button>',
            '  </div>',
            '  <div class="cart-drawer-body"></div>',
            '  <div class="cart-drawer-footer"></div>',
            '</div>'
        ].join('\n');
        document.body.appendChild(drawer);

        drawerBody = drawer.querySelector('.cart-drawer-body');
        drawerFooter = drawer.querySelector('.cart-drawer-footer');

        drawer.querySelector('.cart-drawer-backdrop').addEventListener('click', closeDrawer);
        drawer.querySelector('.cart-drawer-close').addEventListener('click', closeDrawer);

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
        });
    }

    function toggleDrawer() {
        if (!drawer) createDrawer();
        drawer.hidden ? openDrawer() : closeDrawer();
    }

    function openDrawer() {
        if (!drawer) createDrawer();
        renderDrawer();
        drawer.hidden = false;
        document.body.style.overflow = 'hidden';
        drawer.querySelector('.cart-drawer-close').focus();
    }

    function closeDrawer() {
        if (!drawer) return;
        drawer.hidden = true;
        document.body.style.overflow = '';
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderDrawer() {
        if (!drawerBody) return;

        if (!cart.length) {
            drawerBody.innerHTML =
                '<div class="cart-empty">' +
                '  <i class="bi bi-bag" style="font-size:2rem;opacity:0.3"></i>' +
                '  <p>Your cart is empty</p>' +
                '</div>';
            drawerFooter.innerHTML = '';
            return;
        }

        var html = cart.map(function (item) {
            return [
                '<div class="cart-item" data-id="' + escapeHtml(item.id) + '">',
                item.image ? '  <img src="' + escapeHtml(item.image) + '" alt="" class="cart-item-img">' : '',
                '  <div class="cart-item-info">',
                '    <p class="cart-item-title">' + escapeHtml(item.title) + '</p>',
                '    <p class="cart-item-price">$' + item.price.toFixed(2) + '</p>',
                '  </div>',
                '  <div class="cart-item-actions">',
                '    <div class="cart-qty">',
                '      <button class="cart-qty-btn" data-action="minus" data-id="' + escapeHtml(item.id) + '" aria-label="Decrease">−</button>',
                '      <span class="cart-qty-val">' + item.quantity + '</span>',
                '      <button class="cart-qty-btn" data-action="plus" data-id="' + escapeHtml(item.id) + '" aria-label="Increase">+</button>',
                '    </div>',
                '    <button class="cart-remove" data-id="' + escapeHtml(item.id) + '" aria-label="Remove">' +
                '      <i class="bi bi-trash3"></i>' +
                '    </button>',
                '  </div>',
                '</div>'
            ].join('\n');
        }).join('');

        drawerBody.innerHTML = html;

        /* Wire up quantity and remove buttons */
        drawerBody.querySelectorAll('.cart-qty-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-id');
                var delta = btn.getAttribute('data-action') === 'plus' ? 1 : -1;
                updateQuantity(id, delta);
            });
        });

        drawerBody.querySelectorAll('.cart-remove').forEach(function (btn) {
            btn.addEventListener('click', function () {
                removeItem(btn.getAttribute('data-id'));
            });
        });

        /* Footer: total + checkout */
        var total = cartTotal();
        drawerFooter.innerHTML = [
            '<div class="cart-total">',
            '  <span>Subtotal</span>',
            '  <strong>$' + total.toFixed(2) + '</strong>',
            '</div>',
            '<p class="cart-shipping-note small muted">Shipping calculated at checkout</p>',
            '<div id="paypal-button-container"></div>',
            '<button class="cart-clear-btn small muted" aria-label="Clear cart">Clear cart</button>'
        ].join('\n');

        drawerFooter.querySelector('.cart-clear-btn').addEventListener('click', function () {
            if (confirm('Remove all items from your cart?')) clearCart();
        });

        /* Render PayPal buttons if SDK is loaded */
        renderPayPalButtons();
    }

    /* -------------------------------------------------------
       PAYPAL CHECKOUT
       ------------------------------------------------------- */
    function renderPayPalButtons() {
        var container = document.getElementById('paypal-button-container');
        if (!container) return;
        if (typeof paypal === 'undefined') {
            container.innerHTML =
                '<a href="https://www.paypal.com" target="_blank" rel="noopener" class="btn btn-primary" style="width:100%;text-align:center;margin-top:0.5rem">' +
                '  <i class="bi bi-paypal"></i> Checkout with PayPal' +
                '</a>';
            return;
        }

        container.innerHTML = '';
        paypal.Buttons({
            style: {
                layout: 'vertical',
                color: 'gold',
                shape: 'rect',
                label: 'checkout'
            },
            createOrder: function (data, actions) {
                var items = cart.map(function (item) {
                    return {
                        name: item.title,
                        unit_amount: {
                            currency_code: 'USD',
                            value: item.price.toFixed(2)
                        },
                        quantity: String(item.quantity)
                    };
                });
                var total = cartTotal();
                return actions.order.create({
                    purchase_units: [{
                        description: 'Order from sullivanrsteele.com',
                        amount: {
                            currency_code: 'USD',
                            value: total.toFixed(2),
                            breakdown: {
                                item_total: {
                                    currency_code: 'USD',
                                    value: total.toFixed(2)
                                }
                            }
                        },
                        items: items
                    }]
                });
            },
            onApprove: function (data, actions) {
                return actions.order.capture().then(function (details) {
                    showToast('Payment complete — thank you, ' + details.payer.name.given_name + '!', 'success');
                    clearCart();
                    closeDrawer();
                });
            },
            onError: function (err) {
                showToast('Payment error — please try again', 'error');
                console.error('PayPal error:', err);
            }
        }).render('#paypal-button-container');
    }

    /* -------------------------------------------------------
       TOAST NOTIFICATIONS
       ------------------------------------------------------- */
    var toastContainer = null;

    function showToast(message, type) {
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }

        var icons = {
            success: 'bi-check-circle',
            warning: 'bi-exclamation-triangle',
            error: 'bi-x-circle'
        };
        var icon = icons[type] || 'bi-bag-check';

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + (type || 'info');
        toast.innerHTML = '<i class="bi ' + icon + '"></i> ' + escapeHtml(message);
        toastContainer.appendChild(toast);

        /* trigger enter animation */
        requestAnimationFrame(function () {
            toast.classList.add('toast-visible');
        });

        setTimeout(function () {
            toast.classList.remove('toast-visible');
            toast.addEventListener('transitionend', function () {
                toast.remove();
            });
        }, 2800);
    }

    /* -------------------------------------------------------
       PUBLIC API (for shop.js to call)
       ------------------------------------------------------- */
    window.SiteCart = {
        add: addItem,
        remove: removeItem,
        clear: clearCart,
        count: cartCount,
        total: cartTotal,
        open: openDrawer,
        close: closeDrawer,
        toast: showToast
    };

    /* -------------------------------------------------------
       INIT
       ------------------------------------------------------- */
    document.addEventListener('DOMContentLoaded', function () {
        injectCartIcon();
    });
})();
