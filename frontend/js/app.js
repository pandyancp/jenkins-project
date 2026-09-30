/**
 * AlgoTrader Pro — Main Application Engine
 * ========================================
 * Reactive Scanner, Chart Engine, Backtester, Paper Broker, and Risk Controls.
 */

// State
let ws = null;
let chart = null;
let currentSymbol = 'RELIANCE';
let currentTimeframe = '5m';
let scanResults = [];
let currentFilter = 'ALL';
let pendingTradeOrder = null;

// Initialize on DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        lucide.createIcons();
    }

    // Initialize Chart
    chart = new TradingChart('tradingview-chart');

    // Live IST Clock
    updateClock();
    setInterval(updateClock, 1000);

    // Setup navigation & event listeners
    setupTabNavigation();
    setupEventHandlers();

    // Load initial data
    loadScannerResults();
    loadStockDetails(currentSymbol);
    loadPaperOrders();

    // Connect WebSocket
    connectWebSocket();
});

function updateClock() {
    const now = new Date();
    const istTime = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const timeDisplay = document.getElementById('time-display');
    if (timeDisplay) timeDisplay.textContent = `${istTime} IST`;
}

/**
 * Tab Navigation Switcher
 */
function setupTabNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            const activeTabContent = document.getElementById(`tab-${targetTab}`);
            if (activeTabContent) {
                activeTabContent.classList.add('active');
            }

            if (targetTab === 'charts' && chart) {
                setTimeout(() => {
                    if (chart.chart && chart.container) {
                        chart.chart.applyOptions({ width: chart.container.clientWidth });
                    }
                }, 100);
            }
        });
    });
}

/**
 * WebSocket Connection
 */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws`;

    ws = new WebSocket(wsUrl);
    const wsStatusDot = document.querySelector('#ws-status .status-dot');
    const wsStatusText = document.querySelector('#ws-status .status-text');

    ws.onopen = () => {
        if (wsStatusDot) wsStatusDot.className = "status-dot connected";
        if (wsStatusText) wsStatusText.textContent = "Live 1s";
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'MARKET_TICK' || data.type === 'SNAPSHOT') {
                if (data.indices) updateIndices(data.indices);
            }
        } catch (e) {}
    };

    ws.onclose = () => {
        if (wsStatusDot) wsStatusDot.className = "status-dot disconnected";
        if (wsStatusText) wsStatusText.textContent = "Offline";
        setTimeout(connectWebSocket, 3000);
    };
}

function updateIndices(indices) {
    for (const [key, idx] of Object.entries(indices)) {
        let elId = '';
        if (key === 'NIFTY 50') elId = 'idx-nifty50';
        else if (key === 'BANK NIFTY') elId = 'idx-banknifty';
        else if (key === 'SENSEX') elId = 'idx-sensex';

        const el = document.getElementById(elId);
        if (el) {
            const valEl = el.querySelector('.idx-val');
            const chgEl = el.querySelector('.idx-chg');
            valEl.textContent = `₹${idx.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
            const isPos = idx.change >= 0;
            chgEl.className = `idx-chg ${isPos ? 'positive' : 'negative'}`;
            chgEl.textContent = `${isPos ? '+' : ''}${idx.change_percent.toFixed(2)}%`;
        }
    }
}

/**
 * 1. SCANNER ENGINE
 */
async function loadScannerResults() {
    try {
        const res = await fetch('/api/v1/scanner/run?max_price=2500');
        if (!res.ok) return;
        const data = await res.json();
        scanResults = data.results;

        // Update Top Summary Cards
        document.getElementById('card-scanned').textContent = `${data.scanned_count} Stocks`;
        document.getElementById('card-buy-setups').textContent = `${data.buy_setups_count} Setups`;
        document.getElementById('card-watch-stocks').textContent = `${data.watch_count} Stocks`;
        document.getElementById('scanner-buy-badge').textContent = data.buy_setups_count;

        // Update Status Pill
        const statusPill = document.getElementById('market-status-pill');
        const statusText = document.getElementById('market-status-text');
        const statusPulse = document.getElementById('market-pulse');

        if (data.is_market_open) {
            statusPill.className = "market-pill";
            statusPulse.className = "pulse-indicator";
            statusText.textContent = "NSE LIVE MARKET";
        } else {
            statusPill.className = "market-pill closed";
            statusPulse.className = "pulse-indicator closed";
            statusText.textContent = "NSE MARKET CLOSED";
        }

        // Render Dropdown for Detail View
        const symbolSelect = document.getElementById('selected-symbol-select');
        if (symbolSelect) {
            symbolSelect.innerHTML = scanResults.map(s => 
                `<option value="${s.symbol}" ${s.symbol === currentSymbol ? 'selected' : ''}>${s.symbol} — ₹${s.price.toFixed(2)} (${s.signal})</option>`
            ).join('');
        }

        renderScannerTable();
    } catch (e) {
        console.error("Error loading scanner results:", e);
    }
}

function renderScannerTable() {
    const tbody = document.getElementById('scanner-tbody');
    if (!tbody) return;

    let filtered = scanResults;
    if (currentFilter === 'BUY SETUP') {
        filtered = scanResults.filter(s => s.signal === 'BUY SETUP');
    } else if (currentFilter === 'WATCH') {
        filtered = scanResults.filter(s => s.signal === 'WATCH');
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" class="text-center muted" style="padding: 24px;">No stocks matching filter: ${currentFilter}</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(s => {
        const isPos = s.change_pct >= 0;
        const sign = isPos ? '+' : '';
        const chgClass = isPos ? 'val-green' : 'val-red';

        let badgeClass = 'badge-signal-notrade';
        if (s.signal === 'BUY SETUP') badgeClass = 'badge-signal-buy';
        else if (s.signal === 'WATCH') badgeClass = 'badge-signal-watch';
        else if (s.signal === 'EXIT') badgeClass = 'badge-signal-exit';

        return `
            <tr onclick="selectStockForChart('${s.symbol}')">
                <td>
                    <div class="sym-code">${s.symbol}</div>
                    <div class="sym-sub">${s.name}</div>
                </td>
                <td><span class="badge">${s.sector}</span></td>
                <td class="text-right"><strong>₹${s.price.toFixed(2)}</strong></td>
                <td class="text-right ${chgClass}">${sign}${s.change_pct.toFixed(2)}%</td>
                <td class="text-right">₹${s.ema9.toFixed(1)} / ₹${s.ema21.toFixed(1)}</td>
                <td class="text-right">${s.rsi.toFixed(1)}</td>
                <td class="text-right">₹${s.vwap.toFixed(1)}</td>
                <td class="text-center">
                    <strong style="color: var(--color-blue);">${s.tech_score}</strong> / <span class="muted">${s.fund_score}</span>
                </td>
                <td class="text-center">
                    <span class="badge-signal ${badgeClass}">${s.signal}</span>
                </td>
                <td class="text-right">
                    ₹${s.entry_price.toFixed(1)} / <span class="val-red">₹${s.stop_loss.toFixed(1)}</span> / <span class="val-green">₹${s.target.toFixed(1)}</span>
                </td>
                <td class="text-right"><strong>${s.position_size} shares</strong></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); openPaperTradeModal('${s.symbol}', ${s.price}, ${s.stop_loss}, ${s.target}, ${s.position_size})">
                        Paper Trade
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * 2. STOCK DETAILS & CHART LOADER
 */
window.selectStockForChart = function(symbol) {
    currentSymbol = symbol;
    const navCharts = document.querySelector('.nav-item[data-tab="charts"]');
    if (navCharts) navCharts.click();
    loadStockDetails(symbol);
};

async function loadStockDetails(symbol) {
    try {
        const res = await fetch(`/api/v1/stock/${symbol}/candles?timeframe=${currentTimeframe}&count=150`);
        if (!res.ok) return;
        const data = await res.json();

        // Update Chart
        if (chart && data.candles) {
            chart.setCandleData(data.candles);
        }

        const last = data.candles[data.candles.length - 1];
        if (last) {
            document.getElementById('chart-ltp').textContent = `₹${last.close.toFixed(2)}`;
            const prev = data.candles[data.candles.length - 2] || last;
            const chg = ((last.close - prev.close) / prev.close) * 100;
            const chgEl = document.getElementById('chart-change');
            chgEl.className = `chart-change ${chg >= 0 ? 'positive' : 'negative'}`;
            chgEl.textContent = `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`;
        }

        // Update Fundamental Scorecards
        if (data.fundamentals) {
            const f = data.fundamentals;
            document.getElementById('f-pe').textContent = f.pe_ratio || '-';
            document.getElementById('f-pb').textContent = f.pb_ratio || '-';
            document.getElementById('f-roe').textContent = `${f.roe_pct}%`;
            document.getElementById('f-roce').textContent = `${f.roce_pct}%`;
            document.getElementById('f-de').textContent = f.debt_to_equity;
            document.getElementById('f-mcap').textContent = `₹${(f.market_cap_cr || 0).toLocaleString('en-IN')}`;
        }
    } catch (e) {
        console.error("Error loading stock details:", e);
    }
}

/**
 * 3. BACKTESTING ENGINE CONTROLS
 */
async function executeBacktest() {
    const btn = document.getElementById('btn-run-backtest');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader"></i> Simulating...';

    const reqData = {
        symbol: document.getElementById('bt-symbol').value,
        timeframe: "5m",
        days: parseInt(document.getElementById('bt-days').value),
        initial_capital: parseFloat(document.getElementById('bt-capital').value),
        risk_pct: parseFloat(document.getElementById('bt-risk').value),
        stop_loss_pct: parseFloat(document.getElementById('bt-sl').value),
        target_pct: parseFloat(document.getElementById('bt-target').value),
        brokerage_per_order: 20.0,
        slippage_pct: 0.05
    };

    try {
        const res = await fetch('/api/v1/backtest/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqData)
        });
        if (!res.ok) return;
        const bt = await res.json();

        document.getElementById('bt-results-container').style.display = 'block';
        const pnlEl = document.getElementById('bt-net-pnl');
        pnlEl.textContent = `${bt.net_pnl >= 0 ? '+' : ''}₹${bt.net_pnl.toFixed(2)}`;
        pnlEl.className = `stat-value ${bt.net_pnl >= 0 ? 'val-green' : 'val-red'}`;
        document.getElementById('bt-pnl-pct').textContent = `${bt.net_pnl_pct.toFixed(2)}% Net Return`;

        document.getElementById('bt-winrate').textContent = `${bt.win_rate_pct}%`;
        document.getElementById('bt-trade-counts').textContent = `${bt.winning_trades} Wins / ${bt.losing_trades} Losses (Total: ${bt.total_trades})`;
        document.getElementById('bt-profit-factor').textContent = bt.profit_factor;
        document.getElementById('bt-drawdown').textContent = `-${bt.max_drawdown_pct}%`;
        document.getElementById('bt-charges-paid').textContent = `Taxes & Brokerage: ₹${bt.total_charges_paid.toFixed(2)}`;

        // Render trades table
        const tbody = document.getElementById('bt-trades-tbody');
        tbody.innerHTML = bt.trades.map(t => `
            <tr>
                <td>${t.entry_time.slice(0, 16).replace('T', ' ')}</td>
                <td>${t.exit_time.slice(0, 16).replace('T', ' ')}</td>
                <td><strong>${t.symbol}</strong></td>
                <td class="text-right">${t.quantity}</td>
                <td class="text-right">₹${t.entry_price.toFixed(2)}</td>
                <td class="text-right">₹${t.exit_price.toFixed(2)}</td>
                <td class="text-right ${t.net_pnl >= 0 ? 'val-green' : 'val-red'}">
                    ${t.net_pnl >= 0 ? '+' : ''}₹${t.net_pnl.toFixed(2)} (${t.pnl_pct}%)
                </td>
                <td class="text-center"><span class="badge">${t.exit_reason}</span></td>
            </tr>
        `).join('');

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Backtest error:", e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="zap"></i> Run Backtest Simulation';
        if (window.lucide) lucide.createIcons();
    }
}

/**
 * 4. PAPER TRADING & ORDERS
 */
async function loadPaperOrders() {
    try {
        const res = await fetch('/api/v1/orders');
        if (!res.ok) return;
        const data = await res.json();

        // Update capital card
        if (data.funds) {
            document.getElementById('card-capital').textContent = `₹${data.funds.total_capital.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        }

        // Render open positions
        const openTbody = document.getElementById('open-positions-tbody');
        if (openTbody) {
            if (data.open_positions.length === 0) {
                openTbody.innerHTML = `<tr><td colspan="10" class="text-center muted">No active positions open.</td></tr>`;
            } else {
                openTbody.innerHTML = data.open_positions.map(p => `
                    <tr>
                        <td><code>${p.order_id}</code></td>
                        <td><strong>${p.symbol}</strong></td>
                        <td><span class="badge badge-green">${p.side}</span></td>
                        <td class="text-right">${p.quantity}</td>
                        <td class="text-right">₹${p.entry_price.toFixed(2)}</td>
                        <td class="text-right">₹${p.current_price.toFixed(2)}</td>
                        <td class="text-right val-red">₹${p.stop_loss.toFixed(2)}</td>
                        <td class="text-right val-green">₹${p.target.toFixed(2)}</td>
                        <td class="text-right ${p.pnl >= 0 ? 'val-green' : 'val-red'}">
                            ${p.pnl >= 0 ? '+' : ''}₹${p.pnl.toFixed(2)}
                        </td>
                        <td class="text-center">
                            <button class="btn btn-sm btn-outline val-red" onclick="exitPaperPosition('${p.symbol}')">
                                Exit Position
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }

        // Render audit history
        const histTbody = document.getElementById('order-history-tbody');
        if (histTbody) {
            if (data.order_history.length === 0) {
                histTbody.innerHTML = `<tr><td colspan="9" class="text-center muted">No orders executed yet.</td></tr>`;
            } else {
                histTbody.innerHTML = data.order_history.map(o => `
                    <tr>
                        <td>${o.created_at.slice(0, 19).replace('T', ' ')}</td>
                        <td><code>${o.order_id}</code></td>
                        <td><strong>${o.symbol}</strong></td>
                        <td><span class="badge ${o.side === 'BUY' ? 'badge-green' : 'badge-purple'}">${o.side}</span></td>
                        <td class="text-right">${o.quantity}</td>
                        <td class="text-right">₹${o.entry_price.toFixed(2)}</td>
                        <td class="text-right">${o.exit_price ? '₹' + o.exit_price.toFixed(2) : '-'}</td>
                        <td class="text-right ${o.pnl >= 0 ? 'val-green' : 'val-red'}">
                            ${o.pnl ? (o.pnl >= 0 ? '+' : '') + '₹' + o.pnl.toFixed(2) : '₹0.00'}
                        </td>
                        <td class="text-center"><span class="badge">${o.status}</span></td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error("Error loading paper orders:", e);
    }
}

window.openPaperTradeModal = function(symbol, price, sl, target, qty) {
    pendingTradeOrder = { symbol, price, stop_loss: sl, target, quantity: qty };
    const modal = document.getElementById('paper-trade-modal');
    const summary = document.getElementById('trade-modal-summary');

    summary.innerHTML = `
        <div style="background: var(--bg-secondary); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between;"><strong>Symbol:</strong> <span>${symbol} (NSE)</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Current Price:</strong> <span>₹${price.toFixed(2)}</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Calculated Quantity:</strong> <span>${qty} shares</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Stop Loss (1.5%):</strong> <span class="val-red">₹${sl.toFixed(2)}</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Target (3.0%):</strong> <span class="val-green">₹${target.toFixed(2)}</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Total Capital Required:</strong> <span>₹${(price * qty).toFixed(2)}</span></div>
            <div style="display: flex; justify-content: space-between;"><strong>Max Risk:</strong> <span>₹${((price - sl) * qty).toFixed(2)} (1.0% limit)</span></div>
        </div>
    `;

    modal.classList.add('active');
};

window.exitPaperPosition = async function(symbol) {
    try {
        const res = await fetch(`/api/v1/orders/${symbol}/exit`, { method: 'POST' });
        if (res.ok) {
            loadPaperOrders();
        }
    } catch (e) {
        console.error("Error exiting position:", e);
    }
};

/**
 * 5. UI EVENT HANDLERS
 */
function setupEventHandlers() {
    // Rescan button
    const rescanBtn = document.getElementById('btn-run-scan');
    if (rescanBtn) {
        rescanBtn.addEventListener('click', () => {
            loadScannerResults();
        });
    }

    // Filter pills (ALL / BUY SETUP / WATCH)
    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentFilter = pill.getAttribute('data-filter');
            renderScannerTable();
        });
    });

    // Symbol dropdown in Chart view
    const symSelect = document.getElementById('selected-symbol-select');
    if (symSelect) {
        symSelect.addEventListener('change', (e) => {
            currentSymbol = e.target.value;
            loadStockDetails(currentSymbol);
        });
    }

    // Backtest Run Button
    const btBtn = document.getElementById('btn-run-backtest');
    if (btBtn) {
        btBtn.addEventListener('click', executeBacktest);
    }

    // Refresh orders button
    const refOrdersBtn = document.getElementById('btn-refresh-orders');
    if (refOrdersBtn) {
        refOrdersBtn.addEventListener('click', loadPaperOrders);
    }

    // Confirm Paper Trade
    const confirmTradeBtn = document.getElementById('btn-confirm-trade');
    if (confirmTradeBtn) {
        confirmTradeBtn.addEventListener('click', async () => {
            if (!pendingTradeOrder) return;
            try {
                const res = await fetch('/api/v1/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pendingTradeOrder)
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('paper-trade-modal').classList.remove('active');
                    loadPaperOrders();
                    // Switch to portfolio tab to show open position
                    const navPort = document.querySelector('.nav-item[data-tab="portfolio"]');
                    if (navPort) navPort.click();
                } else {
                    alert(data.detail || "Trade failed");
                }
            } catch (e) {
                console.error("Order error:", e);
            }
        });
    }

    // Close Trade Modal
    const closeTradeBtn = document.getElementById('modal-trade-close');
    if (closeTradeBtn) {
        closeTradeBtn.addEventListener('click', () => {
            document.getElementById('paper-trade-modal').classList.remove('active');
        });
    }

    // Kill Switch Button
    const killBtn = document.getElementById('btn-kill-switch');
    let killActive = false;
    if (killBtn) {
        killBtn.addEventListener('click', async () => {
            killActive = !killActive;
            try {
                const res = await fetch(`/api/v1/risk/kill-switch?active=${killActive}`, { method: 'POST' });
                if (res.ok) {
                    killBtn.classList.toggle('active', killActive);
                    killBtn.innerHTML = killActive ? 
                        '<i data-lucide="check"></i> Deactivate Kill Switch' : 
                        '<i data-lucide="power"></i> Activate Kill Switch';
                    
                    const sideStatus = document.getElementById('sidebar-kill-status');
                    if (sideStatus) {
                        sideStatus.className = killActive ? 'health-tag val-red' : 'health-tag success';
                        sideStatus.textContent = killActive ? 'HALTED' : 'SAFE';
                    }
                    if (window.lucide) lucide.createIcons();
                }
            } catch (e) {}
        });
    }

    // Practice Mode Button
    const practiceBtn = document.getElementById('btn-toggle-practice');
    const practiceText = document.getElementById('practice-btn-text');
    let practiceActive = false;
    if (practiceBtn) {
        practiceBtn.addEventListener('click', async () => {
            practiceActive = !practiceActive;
            practiceBtn.classList.toggle('active', practiceActive);
            practiceText.textContent = practiceActive ? "Practice Ticks: ON" : "Practice Ticks: OFF";
        });
    }
}
