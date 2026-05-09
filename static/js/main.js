// TasteGo Main JS
document.addEventListener('DOMContentLoaded', function() {
    // Mobile hamburger menu
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', (e) => {
            e.stopPropagation();
            navLinks.classList.toggle('show');
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.navbar')) navLinks.classList.remove('show');
        });
    }

    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle?.querySelector('i');
    
    function updateThemeIcon() {
        if (!themeIcon) return;
        if (document.documentElement.getAttribute('data-theme') === 'dark') {
            themeIcon.className = 'fa-solid fa-sun';
        } else {
            themeIcon.className = 'fa-solid fa-moon';
        }
    }
    
    if (themeToggle) {
        updateThemeIcon();
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon();
        });
    }

    // Auto-dismiss flash messages
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 400); }, 4000);
    });

    // Live search
    const searchInput = document.getElementById('live-search');
    const searchResults = document.getElementById('search-results');
    let debounce;
    if (searchInput && searchResults) {
        searchInput.addEventListener('input', function() {
            clearTimeout(debounce);
            const q = this.value.trim();
            if (q.length < 2) { searchResults.innerHTML = ''; searchResults.style.display = 'none'; return; }
            debounce = setTimeout(() => {
                fetch('/search?q=' + encodeURIComponent(q))
                    .then(r => r.json())
                    .then(data => {
                        let html = '';
                        if (data.restaurants.length) {
                            html += '<div class="search-section"><h4>Restaurants</h4>';
                            data.restaurants.forEach(r => {
                                html += `<a href="/customer/restaurant/${r.id}/menu" class="search-item">
                                    <span>${r.name}</span><span class="text-muted">${r.cuisine_type || ''}</span></a>`;
                            });
                            html += '</div>';
                        }
                        if (data.items.length) {
                            html += '<div class="search-section"><h4>Food Items</h4>';
                            data.items.forEach(i => {
                                html += `<a href="/customer/restaurant/${i.restaurant_id}/menu" class="search-item">
                                    <span>${i.name}</span><span class="text-muted">₹${i.price} · ${i.restaurant_name}</span></a>`;
                            });
                            html += '</div>';
                        }
                        if (!html) html = '<div class="search-empty">No results found</div>';
                        searchResults.innerHTML = html;
                        searchResults.style.display = 'block';
                    });
            }, 300);
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-bar')) { searchResults.style.display = 'none'; }
        });
    }

    // Order status auto-refresh
    const statusEl = document.getElementById('order-status-live');
    const orderId = statusEl?.dataset?.orderId;
    if (statusEl && orderId) {
        setInterval(() => {
            fetch(`/customer/api/order-status/${orderId}`)
                .then(r => r.json())
                .then(data => {
                    if (data.status) {
                        // Update status text
                        const badge = document.getElementById('status-badge');
                        if (badge) badge.textContent = data.status;
                        // Update timeline
                        const steps = ['Pending','Preparing','Ready for Pickup','Out for Delivery','Delivered'];
                        const idx = steps.indexOf(data.status);
                        document.querySelectorAll('.timeline-step').forEach((el, i) => {
                            el.classList.remove('active','completed');
                            if (i < idx) el.classList.add('completed');
                            else if (i === idx) el.classList.add('active');
                        });
                        // Update partner info
                        if (data.partner) {
                            const pInfo = document.getElementById('partner-info');
                            if (pInfo) pInfo.style.display = 'block';
                            const pName = document.getElementById('partner-name');
                            if (pName) pName.textContent = data.partner.name;
                        }
                    }
                }).catch(() => {});
        }, 5000);
    }

    // Live tracking map
    const mapEl = document.getElementById('tracking-map');
    if (mapEl && typeof L !== 'undefined') {
        const trackOrderId = mapEl.dataset.orderId;
        const map = L.map('tracking-map').setView([12.9716, 77.5946], 14);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(map);
        
        const deliveryIcon = L.divIcon({
            html: '<div style="background:#FF5A36;color:#fff;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 2px 8px rgba(0,0,0,.3)">🛵</div>',
            iconSize: [36, 36], className: ''
        });
        let marker = null;

        function updateLocation() {
            fetch(`/delivery/api/location/${trackOrderId}`)
                .then(r => r.json())
                .then(data => {
                    if (data.latitude && data.longitude) {
                        const pos = [data.latitude, data.longitude];
                        if (!marker) {
                            marker = L.marker(pos, { icon: deliveryIcon }).addTo(map);
                            map.setView(pos, 15);
                        } else {
                            marker.setLatLng(pos);
                        }
                        const nameEl = document.getElementById('map-partner-name');
                        if (nameEl) nameEl.textContent = data.name || '';
                    }
                }).catch(() => {});
        }
        updateLocation();
        setInterval(updateLocation, 4000);
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
        });
    });
});
