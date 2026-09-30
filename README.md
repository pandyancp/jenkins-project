# 🇮🇳 AlgoTrader Pro — Indian Stock Market Scanner & Algo Trading Platform

A production-ready, beginner-friendly **Indian Stock Market (NSE) Algo Trading & Scanner Application** built with Python 3.12, FastAPI, and Vanilla JS.

---

## 🌟 Key Capabilities

* **Automated Stock Scanner**: Scans NSE equities and filters by Liquidity, Fundamental Quality (ROE, ROCE, Debt/Equity, P/E), and Technical Momentum.
* **Technical Strategy Engine**: 5-minute rule-based strategy combining **EMA 9/21 Crossover + RSI 14 Momentum + VWAP + Volume Confirmation**.
* **Actionable Signals**: Generates `BUY SETUP`, `WATCH`, `NO TRADE`, and `EXIT` signals with dynamic scores (0 to 100).
* **Automated Position Sizing & Risk Management**:
  $$\text{Position Size} = \frac{\text{Capital} \times \text{Risk \%}}{\text{Entry Price} - \text{Stop Loss Price}}$$
  Includes daily drawdown limits, max position limits, and an emergency **Kill Switch**.
* **Historical Backtesting Engine**: Event-driven backtester with realistic transaction costs (Brokerage, STT, Exchange Turnover, GST, Stamp Duty) and execution slippage.
* **Paper Trading Broker**: Complete simulated execution engine backed by **SQLite / PostgreSQL**, tracking open positions, stop losses, targets, and P&L.
* **Modular Broker API Ready**: Abstract `BrokerInterface` architecture ready for Zerodha Kite, Angel One, Upstox, Groww, or Dhan.
* **Docker Ready**: One-command deployment via `docker compose up -d`.

---

## 📁 Application Architecture

```text
algo-trading/
├── backend/
│   ├── main.py                  # FastAPI Application Entry Point & Routes
│   ├── config.py                # Centralized Pydantic Settings (.env)
│   ├── logger.py                # Structured Rotating Logging
│   ├── database/
│   │   ├── connection.py        # SQLAlchemy Database Session Factory
│   │   └── models.py            # SQLite / PostgreSQL DB Models
│   ├── models/
│   │   └── schemas.py           # Pydantic Request & Response Contracts
│   ├── services/
│   │   ├── data_service.py      # Stock Universe, Fundamentals & Candle Feeds
│   │   └── broker.py            # Modular Broker Interface & MockPaperBroker
│   ├── indicators/
│   │   └── technical.py         # Pure Pandas/NumPy EMA, RSI, VWAP, ATR
│   ├── strategies/
│   │   └── ema_rsi.py           # 5-min EMA 9/21 + RSI + VWAP Strategy
│   ├── risk/
│   │   └── manager.py           # Position Sizing & Drawdown Protection
│   ├── scanner/
│   │   └── stock_scanner.py     # Multi-factor Stock Scanner Pipeline
│   └── backtest/
│       └── engine.py            # Event-Driven Backtesting Simulation Engine
├── frontend/
│   ├── index.html               # Dark Terminal Single Page Application
│   ├── css/
│   │   └── dashboard.css        # Responsive Theme Styles
│   └── js/
│       ├── app.js               # Reactive UI, Scanner & Backtest Controllers
│       └── charts.js            # TradingView Lightweight Candlestick Charts
├── data/                        # Local SQLite Databases
├── logs/                        # System & Trade Execution Logs
├── tests/                       # Automated Pytest Test Suite
├── .env.example                 # Config Template
├── requirements.txt             # Python Dependencies
├── Dockerfile                   # Production Container Image
├── docker-compose.yml           # Multi-container Deployment
└── README.md                    # Project Documentation
```

---

## 🚀 Quick Start (Local Setup)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run Automated Tests
```bash
python -m pytest tests/test_all_phases.py -v
```

### 4. Start the Application
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

Interactive API Docs (Swagger UI):
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🐳 Running with Docker

To build and run the application in an isolated Docker container:

```bash
docker compose up -d --build
```

To view live logs:
```bash
docker compose logs -f
```

---

## 📊 Technical Strategy Logic

### 🟢 BUY SETUP Rules:
1. **EMA 9 > EMA 21** (Bullish short-term trend)
2. **RSI (14) > 50.0 and RSI <= 68.0** (Strong upward momentum without being overbought)
3. **Current Price >= VWAP** (Trading at or above institutional fair value)
4. **Current Volume >= 0.8x 20-period Average Volume** (Volume confirmation)

### 🔴 EXIT Rules:
1. **Target Hit** (Default: +3.0%)
2. **Stop Loss Hit** (Default: -1.5%)
3. **Bearish Reversal**: EMA 9 < EMA 21 AND RSI < 40.0

---

## 🛡️ Risk Management Rules

* **Capital**: ₹50,000.00 (Configurable)
* **Risk Per Trade**: 1.0% (Max ₹500.00 risk per trade)
* **Position Size Formula**:
  $$\text{Shares} = \text{min}\left(\left\lfloor\frac{\text{Max Risk}}{\text{Entry} - \text{Stop Loss}}\right\rfloor, \left\lfloor\frac{\text{Capital}}{\text{Entry}}\right\rfloor\right)$$
* **Max Daily Loss**: 2.0% (-₹1,000.00) — If daily loss exceeds this, the circuit breaker automatically halts new trades for the day.
* **Emergency Kill Switch**: Available on the dashboard to immediately stop all automated trade executions.

---

## 🔌 Connecting a Real Broker Later

The platform is designed with modularity in mind. To integrate a live broker:
1. Implement the `BrokerInterface` in [backend/services/broker.py](file:///d:/Algo/backend/services/broker.py).
2. Fill your broker API keys in `.env`.
3. Switch `TRADING_MODE=live` when you are ready.
