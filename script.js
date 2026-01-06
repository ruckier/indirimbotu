document.addEventListener('DOMContentLoaded', async () => {
    const grid = document.getElementById('products-grid');
    const lastUpdateEl = document.getElementById('last-update');

    // Stats Elements
    const totalCountEl = document.getElementById('total-count');
    const minPriceEl = document.getElementById('min-price');
    const checkTimeEl = document.getElementById('check-time');

    try {
        // Cache busting için ?t=... ekliyoruz
        const response = await fetch('prices.json?t=' + new Date().getTime());
        if (!response.ok) throw new Error("Veri okunamadı");

        const data = await response.json();

        // Data boşsa
        if (Object.keys(data).length === 0) {
            grid.innerHTML = '<div class="loading">Henüz veri yok. Botun çalışmasını bekleyin.</div>';
            return;
        }

        // Objeden Array'e çevir ve işle
        const products = Object.entries(data).map(([url, info]) => ({
            url,
            ...info
        }));

        // İstatistikleri Hesapla
        const totalPrice = products.reduce((sum, p) => sum + p.price, 0);
        const minPrice = Math.min(...products.map(p => p.price));
        const lastCheck = Math.max(...products.map(p => p.updated_at));

        totalCountEl.innerText = products.length;
        minPriceEl.innerText = `${minPrice.toLocaleString('tr-TR')} TL`;
        checkTimeEl.innerText = new Date(lastCheck * 1000).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
        lastUpdateEl.innerHTML = `<i class="fa-solid fa-check"></i> Son Kontrol: ${new Date(lastCheck * 1000).toLocaleString('tr-TR')}`;

        // Render Function
        const renderProducts = (items) => {
            grid.innerHTML = '';
            items.forEach(product => {
                const date = new Date(product.updated_at * 1000);
                const timeStr = date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });

                const card = document.createElement('div');
                card.className = 'product-card';

                card.innerHTML = `
                    <div class="update-badge"><i class="fa-regular fa-clock"></i> ${timeStr}</div>
                    <div class="product-name">${product.name}</div>
                    <div class="product-footer">
                        <div class="price-tag">
                            ${product.price.toLocaleString('tr-TR')} <span class="price-currency">TL</span>
                        </div>
                        <a href="${product.url}" target="_blank" class="visit-btn">
                            Git <i class="fa-solid fa-arrow-right"></i>
                        </a>
                    </div>
                `;
                grid.appendChild(card);
            });
        };

        // Initial Render
        renderProducts(products);

        // Sorting Logic
        document.getElementById('sort-select').addEventListener('change', (e) => {
            const sortType = e.target.value;
            let sortedProducts = [...products];

            if (sortType === 'price-asc') {
                sortedProducts.sort((a, b) => a.price - b.price);
            } else if (sortType === 'price-desc') {
                sortedProducts.sort((a, b) => b.price - a.price);
            } else if (sortType === 'newest') {
                sortedProducts.sort((a, b) => b.updated_at - a.updated_at);
            }

            renderProducts(sortedProducts);
        });

    } catch (error) {
        console.error(error);
        grid.innerHTML = `<div class="loading" style="color: #ff0055;">
            <i class="fa-solid fa-triangle-exclamation"></i><br>
            Veri yüklenirken hata oluştu.<br>
            <small>${error.message}</small>
        </div>`;
    }
});
