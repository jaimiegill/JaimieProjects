// 1. GLOBAL SCOPE
let tvWidget = null;
let cryptoAssets = [];
let currentFilter = 'main';
const watchlistRows = {};
const sparkHistories = {};
const MAIN_ASSETS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'LTC'];

function initChart(symbol = "KRAKEN:XBTUSD") {
    const container = document.getElementById("tv_main_chart");
    if (!container) return;
    container.innerHTML = "";

    tvWidget = new TradingView.widget({
        // Use "autosize" so it fills your center div perfectly
        "autosize": true,
        "symbol": symbol,
        "interval": "15",
        "theme": "dark",
        "container_id": "tv_main_chart",
        "style": "1",
        "hide_side_toolbar": false, // Shows the drawing tools (left bar)
        "allow_symbol_change": true, // Enables searching in the top bar

        // 1. ENABLE THESE for the top bar
        "enabled_features": [
            "header_widget",         // This is the main top bar
            "header_indicators",     // Indicators button
            "header_settings",       // Settings gear
            "header_chart_type",     // Candle/Line/Area switch
            "header_resolutions",    // Timeframe switch (1m, 5m, 1h)
            "header_screenshot"      // Camera icon
        ],

        // 2. CLEAN UP the list below
        "disabled_features": [
            "border_around_the_chart", // Still keeps the layout flush
            "header_symbol_search"     // Keep this only if you want to use YOUR search bar
        ],

        "overrides": {
            "paneProperties.background": "#000000",
            "paneProperties.backgroundType": "solid",
            "paneProperties.separatorColor": "#000000",
            "scalesProperties.lineColor": "rgba(42, 46, 57, 1)", // Set to visible so you can see prices
            "symbolWatermarkProperties.transparency": 100
        }
    });
}

// ... Keep all your other functions (fetchMarketData, renderWatchlist, etc.) exactly as they were ...

// 3. STARTUP LOGIC (Place this at the very bottom of the file)
window.addEventListener('DOMContentLoaded', () => {
    fetchMarketData(); // This calls sortAndRender which calls renderWatchlist
    initChart();       // Loads default chart
});

// 1. FILTERED DATA FETCH
let searchableAssets = []; // Global list of all available coins

async function fetchMarketData() {
    try {
        const [pRes, tRes] = await Promise.all([
            fetch('https://api.kraken.com/0/public/AssetPairs'),
            fetch('https://api.kraken.com/0/public/Ticker')
        ]);
        const pairs = (await pRes.json()).result;
        const tickers = (await tRes.json()).result;

        const liveTemp = [];
        searchableAssets = []; // Clear old search data

        for (const key in pairs) {
            const p = pairs[key];
            const base = p.base.replace('XXBT', 'BTC').replace('XBT', 'BTC').replace('XETH', 'ETH').replace('ZUSD', 'USD');

            // 1. If it's a MAIN_ASSET, add it to the live list
            if (MAIN_ASSETS.includes(base) && (p.quote === 'ZUSD' || p.quote === 'USD') && tickers[key]) {
                const t = tickers[key];
                liveTemp.push({
                    symbol: base,
                    tvSymbol: `KRAKEN:${p.altname}`,
                    wsSymbol: p.wsname,
                    price: parseFloat(t.c[0]),
                    change: ((t.c[0] - t.o) / t.o) * 100
                });
            }
            // 2. Otherwise, just save the basic info for searching (No heavy processing)
            else if (p.quote === 'ZUSD' || p.quote === 'USD') {
                searchableAssets.push({
                    symbol: base,
                    tvSymbol: `KRAKEN:${p.altname}`,
                    name: p.altname
                });
            }
        }

        cryptoAssets = liveTemp; // Only these get live updates
        sortAndRender();
        initWebSocket();
    } catch (e) { console.error(e); }
}

// 4. SORTING & UI LOGIC
function setFilter(type) {
    currentFilter = type;
    document.querySelectorAll('.tab-btn').forEach(btn =>
        btn.classList.toggle('active', btn.innerText.toLowerCase() === type)
    );
    sortAndRender();
}

function sortAndRender() {
    if (currentFilter === 'main') {
        cryptoAssets.sort((a, b) => {
            const ia = MAIN_ASSETS.indexOf(a.symbol), ib = MAIN_ASSETS.indexOf(b.symbol);
            if (ia !== -1 && ib !== -1) return ia - ib;
            return ia !== -1 ? -1 : (ib !== -1 ? 1 : a.symbol.localeCompare(b.symbol));
        });
    } else if (currentFilter === 'trending') {
        cryptoAssets.sort((a, b) => b.trendScore - a.trendScore);
    } else {
        cryptoAssets.sort((a, b) => b.volume - a.volume);
    }
    renderWatchlist();
}

// 5. RENDER WATCHLIST (SINGLE VERSION)
// 1. RENDER WATCHLIST (Fixed IDs for WebSocket targeting)
function renderWatchlist() {
    const container = document.getElementById('watchlist-content');
    container.innerHTML = '';

    cryptoAssets.forEach((asset, index) => {
        const row = document.createElement('div');
        row.className = 'crypto-row';
        row.id = `row-${asset.symbol}`;

        // ADDED: id="price-${asset.symbol}" so the WebSocket can find it
        row.innerHTML = `
            <div style="display: flex; align-items: center; width: 95px;">
                <img src="" class="coin-logo" onerror="resolveLogo(this, '${asset.symbol}')">
                <div class="coin-info"><strong>${asset.symbol}</strong></div>
            </div>
            <canvas class="spark-canvas" id="canvas-${asset.symbol}"></canvas>
            <div class="trending-info">
                <span class="change-pill ${asset.change >= 0 ? 'pill-up' : 'pill-down'}">
                    ${asset.change >= 0 ? '▲' : '▼'}${Math.abs(asset.change).toFixed(2)}%
                </span>
            </div>
            <div id="price-${asset.symbol}" class="price-container">
                $${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        `;

        const img = row.querySelector('.coin-logo');
        resolveLogo(img, asset.symbol);

        row.onclick = () => {
            document.querySelectorAll('.crypto-row').forEach(r => r.classList.remove('active-row'));
            row.classList.add('active-row');
            initChart(asset.tvSymbol);
        };

        container.appendChild(row);
        watchlistRows[asset.symbol] = row;
        
        // Stagger sparklines to prevent Wi-Fi choking
        setTimeout(() => initSpark(asset.symbol), index * 150);
    });
}

// 2. WEBSOCKET (Added Auto-Reconnect for bad Wi-Fi)
function initWebSocket() {
    const ws = new WebSocket('wss://ws.kraken.com/v2');

    ws.onopen = () => {
        console.log("WebSocket Connected");
        const symbols = cryptoAssets.map(a => a.wsSymbol);
        ws.send(JSON.stringify({
            method: "subscribe",
            params: { channel: "ticker", symbol: symbols }
        }));
    };

    ws.onmessage = (e) => {
        const res = JSON.parse(e.data);
        if (res.channel === "ticker" && res.data) {
            res.data.forEach(t => {
                const sym = t.symbol.split('/')[0].replace('XBT', 'BTC');
                const el = document.getElementById(`price-${sym}`);
                const row = document.getElementById(`row-${sym}`);

                if (el && row) {
                    const newPrice = t.last;
                    const oldPrice = parseFloat(el.innerText.replace(/[$,]/g, ''));

                    if (newPrice !== oldPrice) {
                        el.innerText = `$${newPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
                        
                        // Use CSS classes for the flash effect
                        const flashClass = newPrice >= oldPrice ? 'flash-up' : 'flash-down';
                        row.classList.remove('flash-up', 'flash-down');
                        void row.offsetWidth; // Trigger reflow
                        row.classList.add(flashClass);
                    }
                }
            });
        }
    };

    ws.onclose = () => {
        console.warn("WebSocket closed. Attempting reconnect...");
        setTimeout(initWebSocket, 3000); // Auto-reconnect after 3 seconds
    };

    ws.onerror = (err) => {
        console.error("WS Error:", err);
        ws.close();
    };
}

// 6. SPARK & WEBSOCKET (Remains mostly the same)
async function initSpark(symbol) {
    if (sparkHistories[symbol]) { drawSpark(symbol); return; }
    const kSym = (symbol === 'BTC' ? 'XBT' : symbol) + 'USD';
    try {
        const res = await fetch(`https://api.kraken.com/0/public/OHLC?pair=${kSym}&interval=60`);
        const data = await res.json();
        const key = Object.keys(data.result)[0];
        sparkHistories[symbol] = data.result[key].map(c => parseFloat(c[4])).slice(-24);
        drawSpark(symbol);
    } catch (e) { }
}

function drawSpark(symbol) {
    const canvas = document.getElementById(`canvas-${symbol}`);
    if (!canvas || !sparkHistories[symbol]) return;
    const ctx = canvas.getContext('2d'), data = sparkHistories[symbol];
    const dpr = window.devicePixelRatio || 1;
    canvas.width = 65 * dpr; canvas.height = 20 * dpr; ctx.scale(dpr, dpr);
    const min = Math.min(...data), max = Math.max(...data), range = (max - min) || 1;
    ctx.clearRect(0, 0, 65, 20); ctx.beginPath();
    const isUp = data[data.length - 1] >= data[0];
    ctx.strokeStyle = isUp ? '#00ffcc' : '#ff3366';
    ctx.lineWidth = 2; ctx.lineJoin = 'round';
    data.forEach((p, i) => {
        const x = (i / (data.length - 1)) * 65;
        const y = 20 - ((p - min) / range * 16) - 2;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
}

// Search Logic
document.getElementById('search-input').addEventListener('input', (e) => {
    const val = e.target.value.toLowerCase();
    Object.keys(watchlistRows).forEach(sym => {
        watchlistRows[sym].style.display = sym.toLowerCase().includes(val) ? 'flex' : 'none';
    });
});

// 1. Define the order of URLs to try
const LOGO_SOURCES = [
    (sym) => `https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/${sym}.png`,
    (sym) => `https://s3-symbol-logo.tradingview.com/crypto/${sym.toUpperCase()}.svg`,
    (sym) => `https://cryptologos.cc/logos/${sym}-logo.svg?v=024`,
    (sym) => `https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@1a72d37/128/color/${sym}.png`
];

function tryNextLogo(imgElement, symbol, sourceIndex) {
    if (sourceIndex < LOGO_SOURCES.length) {
        // Try the next source in the list
        imgElement.src = LOGO_SOURCES[sourceIndex](symbol);
        // Increment index for the next potential failure
        imgElement.setAttribute('data-src-index', sourceIndex + 1);
    } else {
        // FINAL FALLBACK: Create a colored circle with the first letter
        const parent = imgElement.parentElement;
        const fallbackCircle = document.createElement('div');
        fallbackCircle.className = 'coin-logo';
        fallbackCircle.style.display = 'flex';
        fallbackCircle.style.alignItems = 'center';
        fallbackCircle.style.justifyContent = 'center';
        fallbackCircle.style.background = '#363a45';
        fallbackCircle.style.fontSize = '10px';
        fallbackCircle.style.fontWeight = 'bold';
        fallbackCircle.innerText = symbol.substring(0, 1).toUpperCase();

        parent.replaceChild(fallbackCircle, imgElement);
    }
}

function renderWatchlist() {
    const container = document.getElementById('watchlist-content');
    container.innerHTML = '';

    cryptoAssets.forEach(asset => {
        const row = document.createElement('div');
        row.className = 'crypto-row';
        row.id = `row-${asset.symbol}`;

        row.innerHTML = `
            <div style="display: flex; align-items: center; width: 95px;">
                <img src="" 
                     class="coin-logo" 
                     onload="this.style.opacity='1'"
                     onerror="resolveLogo(this, '${asset.symbol}')"
                     style="opacity: 0; transition: opacity 0.3s;">
                <div class="coin-info"><strong>${asset.symbol}</strong></div>
            </div>
            <canvas class="spark-canvas" id="canvas-${asset.symbol}"></canvas>
            <div class="trending-info">
                <span class="change-pill ${asset.change >= 0 ? 'pill-up' : 'pill-down'}">
                    ${asset.change >= 0 ? '▲' : '▼'}${Math.abs(asset.change).toFixed(2)}%
                </span>
            </div>
            <div id="price-${asset.symbol}" class="price-container">
                $${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        `;

        // Initialize the first attempt
        const img = row.querySelector('.coin-logo');
        resolveLogo(img, asset.symbol);

        row.onclick = () => {
            document.querySelectorAll('.crypto-row').forEach(r => r.classList.remove('active-row'));
            row.classList.add('active-row');
            if (tvWidget) tvWidget.setSymbol(asset.tvSymbol, "15");
        };
        // Inside your renderWatchlist function:
        row.onclick = () => {
            // UI Feedback
            document.querySelectorAll('.crypto-row').forEach(r => r.classList.remove('active-row'));
            row.classList.add('active-row');

            // Re-initialize the entire chart
            console.log("Re-initializing chart for:", asset.tvSymbol);
            initChart(asset.tvSymbol);
        };

        container.appendChild(row);
        watchlistRows[asset.symbol] = row;
        initSpark(asset.symbol);

    });
}
// 1. Map Kraken Symbols to CryptoLogos Slugs
const LOGO_MAP = {
    'BTC': 'bitcoin', 'XBT': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'XRP': 'xrp', 'ADA': 'cardano', 'DOGE': 'dogecoin', 'AVAX': 'avalanche',
    'DOT': 'polkadot', 'LINK': 'chainlink', 'LTC': 'litecoin', 'MATIC': 'polygon',
    'ALGO': 'algorand', 'BCH': 'bitcoin-cash', 'XLM': 'stellar', 'ATOM': 'cosmos',
    'UNI': 'uniswap', 'ICP': 'internet-computer', 'ETC': 'ethereum-classic',
    'FIL': 'filecoin', 'NEAR': 'near-protocol', 'APE': 'apecoin'
};

// 2. The Waterfall Function
function resolveLogo(img, symbol) {
    const s = symbol.toUpperCase();
    const slug = LOGO_MAP[s] || s.toLowerCase();
    const index = parseInt(img.getAttribute('data-step') || '0');

    // List of URL patterns to try in order
    const patterns = [
        // Step 0: CryptoLogos SVG (Primary)
        `https://cryptologos.cc/logos/${slug}-${s.toLowerCase()}-logo.svg?v=024`,
        // Step 1: CryptoLogos PNG (Backup)
        `https://cryptologos.cc/logos/${slug}-${s.toLowerCase()}-logo.png?v=024`,
        // Step 2: TradingView CDN (Reliable fallback)
        `https://s3-symbol-logo.tradingview.com/crypto/${s === 'XBT' ? 'BTC' : s}.svg`,
        // Step 3: Generic Icon
        `https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/${s === 'XBT' ? 'btc' : s.toLowerCase()}.png`
    ];

    if (index < patterns.length) {
        img.setAttribute('data-step', index + 1);
        img.src = patterns[index];
    } else {
        // Ultimate Fallback: Hide the broken image
        img.style.display = 'none';
    }
}
let searchTimeout;
document.getElementById('search-input').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const query = e.target.value.toUpperCase();

    searchTimeout = setTimeout(() => {
        if (!query) {
            renderWatchlist(); // Go back to normal live list
            return;
        }

        // Search the hidden list
        const results = searchableAssets.filter(a =>
            a.symbol.includes(query) || a.name.includes(query)
        );

        renderSearchResults(results);
    }, 300);
});

function renderSearchResults(results) {
    const container = document.getElementById('watchlist-content');
    container.innerHTML = ''; // Clear the live list

    // Only show the first 20 results (for speed)
    results.slice(0, 20).forEach(asset => {
        const row = document.createElement('div');
        row.className = 'crypto-row search-result';
        row.innerHTML = `
            <div style="display: flex; align-items: center;">
                <div class="coin-info"><strong>${asset.symbol}</strong></div>
            </div>
            <div class="search-hint">Click to view chart</div>
        `;
        row.onclick = () => initChart(asset.tvSymbol);
        container.appendChild(row);
    });
}


// Start
initChart();
fetchMarketData();