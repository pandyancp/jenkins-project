"""
Automated Stock Scanner Engine
==============================
Scans NSE-listed stocks against Fundamental, Liquidity, Technical, and Risk rules.
Produces actionable signals (BUY SETUP, WATCH, NO TRADE, EXIT) with exact Risk & Sizing.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.services.data_service import MarketDataService, NSE_UNIVERSE
from backend.strategies.ema_rsi import EmaRsiStrategy
from backend.risk.manager import RiskManager
from backend.models.schemas import StockFilterParams, StrategyConfig, RiskParams, ScanItemResponse, ScannerSummaryResponse
from backend.database.connection import SessionLocal
from backend.database.models import ScanResultModel


class StockScanner:
    def __init__(self, data_service: MarketDataService = None):
        self.data_service = data_service or MarketDataService()
        self.strategy = EmaRsiStrategy()
        self.risk_manager = RiskManager()

    def calculate_fundamental_score(self, fund: Dict[str, Any], filters: StockFilterParams) -> float:
        """
        Calculates Fundamental Quality Score (0 to 100).
        Evaluates ROE, ROCE, Debt/Equity, Valuation (P/E), and Market Cap.
        """
        score = 0.0

        # 1. Profitability (ROE & ROCE) - Max 40 pts
        roe = fund.get("roe_pct", 0.0)
        roce = fund.get("roce_pct", 0.0)
        if roe >= 20.0: score += 20.0
        elif roe >= 12.0: score += 12.0
        elif roe >= 8.0: score += 6.0

        if roce >= 20.0: score += 20.0
        elif roce >= 12.0: score += 12.0
        elif roce >= 8.0: score += 6.0

        # 2. Balance Sheet Strength (Debt/Equity) - Max 30 pts
        de = fund.get("debt_to_equity", 1.0)
        if de <= 0.2: score += 30.0
        elif de <= 0.7: score += 20.0
        elif de <= 1.2: score += 10.0

        # 3. Market Capitalization & Stability - Max 20 pts
        mcap = fund.get("market_cap_cr", 0.0)
        if mcap >= 100000.0: score += 20.0
        elif mcap >= 25000.0: score += 15.0
        elif mcap >= 5000.0: score += 10.0

        # 4. Valuation (P/E) - Max 10 pts
        pe = fund.get("pe_ratio", 25.0)
        if 5.0 <= pe <= 30.0: score += 10.0
        elif pe < 50.0: score += 5.0

        return round(score, 1)

    def scan_all(self, filters: StockFilterParams = None, strat_config: StrategyConfig = None, risk_params: RiskParams = None) -> ScannerSummaryResponse:
        """
        Runs the full scanning pipeline across the entire stock universe.
        """
        filters = filters or StockFilterParams()
        if strat_config:
            self.strategy = EmaRsiStrategy(strat_config)
        if risk_params:
            self.risk_manager = RiskManager(risk_params)

        results: List[ScanItemResponse] = []
        buy_count = 0
        watch_count = 0
        no_trade_count = 0

        universe = self.data_service.get_stock_universe()
        db = SessionLocal()

        try:
            for symbol, fund_data in universe.items():
                base_price = fund_data.get("base_price", 0.0)

                # ── Liquidity & Price Filters ──
                if base_price > filters.max_price or base_price <= 0:
                    continue

                avg_vol = fund_data.get("avg_daily_volume", 0)
                if avg_vol < filters.min_volume:
                    continue

                # ── Fundamental Score ──
                fund_score = self.calculate_fundamental_score(fund_data, filters)

                # ── Technical Strategy Evaluation ──
                df = self.data_service.get_historical_candles_df(symbol, "5m", 120)
                tech_eval = self.strategy.evaluate_latest(df)

                signal = tech_eval["signal"]
                tech_score = tech_eval["tech_score"]
                current_price = tech_eval["price"]

                # Total combined score (60% Tech + 40% Fund)
                total_score = round((tech_score * 0.6) + (fund_score * 0.4), 1)

                # ── Risk & Position Sizing ──
                pos_info = self.risk_manager.calculate_position_size(current_price)

                # Track counts
                if signal == "BUY SETUP":
                    buy_count += 1
                elif signal == "WATCH":
                    watch_count += 1
                else:
                    no_trade_count += 1

                # Calculate day change %
                prev_close = float(df.iloc[-2]['close']) if len(df) >= 2 else current_price
                change_pct = round(((current_price - prev_close) / prev_close) * 100.0, 2)

                item = ScanItemResponse(
                    symbol=symbol,
                    name=fund_data.get("name", symbol),
                    sector=fund_data.get("sector", "General"),
                    price=current_price,
                    change_pct=change_pct,
                    ema9=tech_eval["ema9"],
                    ema21=tech_eval["ema21"],
                    rsi=tech_eval["rsi"],
                    vwap=tech_eval["vwap"],
                    volume=tech_eval["volume"],
                    avg_volume=avg_vol,
                    tech_score=tech_score,
                    fund_score=fund_score,
                    total_score=total_score,
                    signal=signal,
                    entry_price=pos_info["entry_price"],
                    stop_loss=pos_info["stop_loss"],
                    target=pos_info["target"],
                    position_size=pos_info["quantity"],
                    risk_amount=pos_info["actual_risk"]
                )
                results.append(item)

                # Persist to database
                db_scan = ScanResultModel(
                    symbol=symbol,
                    price=current_price,
                    change_pct=change_pct,
                    ema9=tech_eval["ema9"],
                    ema21=tech_eval["ema21"],
                    rsi=tech_eval["rsi"],
                    vwap=tech_eval["vwap"],
                    volume=tech_eval["volume"],
                    avg_volume=avg_vol,
                    tech_score=tech_score,
                    fund_score=fund_score,
                    total_score=total_score,
                    signal=signal,
                    entry_price=pos_info["entry_price"],
                    stop_loss=pos_info["stop_loss"],
                    target=pos_info["target"],
                    position_size=pos_info["quantity"]
                )
                db.add(db_scan)

            db.commit()
        except Exception as e:
            db.rollback()
        finally:
            db.close()

        # Sort: BUY SETUPS first, then by total score descending
        signal_priority = {"BUY SETUP": 1, "WATCH": 2, "EXIT": 3, "NO TRADE": 4}
        results.sort(key=lambda x: (signal_priority.get(x.signal, 5), -x.total_score))

        # Check market open status
        now = datetime.now()
        is_open = (now.weekday() < 5) and (now.replace(hour=9, minute=15) <= now <= now.replace(hour=15, minute=30))

        return ScannerSummaryResponse(
            market_status="OPEN" if is_open else "CLOSED",
            is_market_open=is_open,
            scanned_count=len(results),
            buy_setups_count=buy_count,
            watch_count=watch_count,
            no_trade_count=no_trade_count,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            results=results
        )
