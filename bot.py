"""
Groww Algo Trading Bot - Main Entry Point
==========================================
A live trading bot that connects to Groww's API and executes
trades based on technical analysis strategies.

Usage:
    python bot.py                    # Run with default settings
    python bot.py --strategy RSI     # Run with specific strategy
    python bot.py --paper            # Force paper trading mode
    python bot.py --live             # Force live trading (⚠️ real money!)

⚠️ DISCLAIMER: Algorithmic trading carries significant risk.
   Use at your own risk. Start with PAPER TRADING first!
"""

import sys
import os
import time
import signal
import logging
import argparse

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from datetime import datetime, timedelta
from colorama import init, Fore, Style
from tabulate import tabulate

from config import (
    WATCHLIST, STRATEGY, CHECK_INTERVAL_SECONDS,
    PAPER_TRADING, CANDLE_INTERVAL,
    MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE,
    LOG_FILE, LOG_LEVEL, EXCHANGE, MARKET_NAME,
    NSE_HOLIDAYS_2026,
)
from groww_api import GrowwAPI, GrowwAPIError
from strategies import get_strategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from risk_manager import RiskManager

# Initialize colorama for Windows
init(autoreset=True)

# ═══════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════

def setup_logging():
    """Configure logging to both file and console."""
    logger = logging.getLogger("GrowwBot")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


# ═══════════════════════════════════════════════
# DISPLAY HELPERS
# ═══════════════════════════════════════════════

def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   {Fore.GREEN}█▀▀ █▀█ █▀█ █ █ █ █   {Fore.YELLOW}▄▀█ █   █▀▀ █▀█   {Fore.RED}█▀▄ █▀█ ▀█▀{Fore.CYAN}     ║
║   {Fore.GREEN}█▄█ █▀▄ █▄█ ▀▄▀▄▀▀   {Fore.YELLOW}█▀█ █▄▄ █▄█ █▄█   {Fore.RED}█▄▀ █▄█  █{Fore.CYAN}      ║
║                                                              ║
║   {Fore.WHITE}Automated Trading System for Indian Markets{Fore.CYAN}               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_status(mode, strategy_name, watchlist, risk_summary):
    """Print current bot status."""
    mode_color = Fore.YELLOW if mode == "PAPER" else Fore.RED
    print(f"\n{Fore.CYAN}{'─' * 60}")
    print(f"  Mode:      {mode_color}{mode} TRADING{Style.RESET_ALL}")
    print(f"  Strategy:  {Fore.GREEN}{strategy_name}{Style.RESET_ALL}")
    print(f"  Watchlist: {Fore.WHITE}{', '.join(watchlist)}{Style.RESET_ALL}")
    print(f"  Interval:  {Fore.WHITE}Every {CHECK_INTERVAL_SECONDS}s{Style.RESET_ALL}")
    print(f"  Time:      {Fore.WHITE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")

    # Risk summary table
    summary_data = [
        ["Open Positions", risk_summary["open_positions"], f"/ {risk_summary['max_positions']}"],
        ["Capital Used", risk_summary["capital_used"], f"/ {risk_summary['capital_available']} free"],
        ["Daily P&L", risk_summary["daily_pnl"], ""],
        ["Total P&L", risk_summary["total_pnl"], ""],
        ["Total Trades", risk_summary["total_trades"], ""],
    ]
    print(tabulate(summary_data, headers=["Metric", "Value", ""], tablefmt="simple"))
    print()


def print_signal(symbol, signal, strategy_info, price):
    """Print a trading signal."""
    if signal == SIGNAL_BUY:
        color = Fore.GREEN
        icon = "🟢"
    elif signal == SIGNAL_SELL:
        color = Fore.RED
        icon = "🔴"
    else:
        color = Fore.YELLOW
        icon = "⚪"

    print(
        f"  {icon} {color}{signal:4s}{Style.RESET_ALL} | "
        f"{Fore.WHITE}{symbol:12s}{Style.RESET_ALL} | "
        f"₹{price:>10.2f} | "
        f"{strategy_info}"
    )


# ═══════════════════════════════════════════════
# MARKET HOURS CHECK
# ═══════════════════════════════════════════════

def is_market_open():
    """Check if Indian stock market (NSE/BSE) is currently open."""
    now = datetime.now()

    # Weekend check (Saturday & Sunday)
    if now.weekday() >= 5:
        return False

    # NSE Holiday check
    today_str = now.strftime("%Y-%m-%d")
    if today_str in NSE_HOLIDAYS_2026:
        return False

    market_open = now.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0
    )
    market_close = now.replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0
    )

    return market_open <= now <= market_close


def get_next_market_open():
    """Get the next time NSE market opens."""
    now = datetime.now()
    next_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)

    if now >= next_open:
        next_open += timedelta(days=1)

    # Skip weekends and holidays
    while next_open.weekday() >= 5 or next_open.strftime("%Y-%m-%d") in NSE_HOLIDAYS_2026:
        next_open += timedelta(days=1)

    return next_open


# ═══════════════════════════════════════════════
# MAIN TRADING BOT
# ═══════════════════════════════════════════════

class TradingBot:
    """Main trading bot that orchestrates everything."""

    def __init__(self, strategy_name=None, paper_mode=None):
        self.logger = logging.getLogger("GrowwBot")
        self.api = GrowwAPI()
        self.risk = RiskManager()
        self.running = False

        # Strategy per symbol
        strategy_name = strategy_name or STRATEGY
        self.strategies = {}
        for symbol in WATCHLIST:
            self.strategies[symbol] = get_strategy(strategy_name)

        self.strategy_name = strategy_name
        self.paper_mode = paper_mode if paper_mode is not None else PAPER_TRADING

        # Override paper mode in config
        if paper_mode is not None:
            import config
            config.PAPER_TRADING = paper_mode

    def start(self):
        """Start the trading bot."""
        print_banner()

        mode = "PAPER" if self.paper_mode else "LIVE"
        if not self.paper_mode:
            print(f"\n{Fore.RED}⚠️  WARNING: LIVE TRADING MODE - REAL MONEY AT RISK!{Style.RESET_ALL}")
            print(f"{Fore.RED}   Press Ctrl+C within 5 seconds to cancel...{Style.RESET_ALL}")
            time.sleep(5)

        self.logger.info(f"🚀 Bot starting in {mode} mode with {self.strategy_name} strategy")

        # Login to Groww
        try:
            self.api.login()
        except Exception as e:
            if self.paper_mode:
                self.logger.warning(f"⚠️ Login failed (paper mode - continuing): {e}")
            else:
                self.logger.error(f"❌ Login failed: {e}")
                return

        self.running = True
        self._run_loop()

    def stop(self):
        """Stop the trading bot gracefully."""
        self.running = False
        self.logger.info("🛑 Bot stopping...")

        # Close all positions
        for symbol in list(self.risk.positions.keys()):
            self.logger.info(f"📤 Closing position: {symbol}")
            quote = self.api.get_quote(symbol)
            if quote:
                self.api.place_order(symbol, "SELL", self.risk.positions[symbol].quantity)
                self.risk.close_position(symbol, quote["ltp"], "BOT_SHUTDOWN")

        # Print final summary
        print(f"\n{Fore.CYAN}{'═' * 60}")
        print(f"  FINAL SUMMARY")
        print(f"{'═' * 60}{Style.RESET_ALL}")
        summary = self.risk.get_summary()
        for key, val in summary.items():
            print(f"  {key}: {val}")

        if self.risk.closed_positions:
            print(f"\n{Fore.CYAN}  TRADE HISTORY:{Style.RESET_ALL}")
            trade_data = [p.to_dict() for p in self.risk.closed_positions]
            print(tabulate(trade_data, headers="keys", tablefmt="grid"))

        self.logger.info("👋 Bot stopped.")

    def _run_loop(self):
        """Main trading loop."""
        while self.running:
            try:
                # Check market hours
                if not is_market_open() and not self.paper_mode:
                    self.logger.info("💤 Market is closed. Waiting...")
                    time.sleep(60)
                    continue

                # Print status
                print_status(
                    "PAPER" if self.paper_mode else "LIVE",
                    self.strategy_name,
                    WATCHLIST,
                    self.risk.get_summary()
                )

                print(f"  {Fore.CYAN}{'─' * 55}{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Signal  | Symbol       | Price      | Info{Style.RESET_ALL}")
                print(f"  {Fore.CYAN}{'─' * 55}{Style.RESET_ALL}")

                # Process each symbol in watchlist
                quotes = {}
                for symbol in WATCHLIST:
                    self._process_symbol(symbol, quotes)

                # Check stop-losses for open positions
                exits = self.risk.check_stop_losses(quotes)
                for symbol, reason in exits:
                    self._exit_position(symbol, quotes.get(symbol, 0), reason)

                # Wait before next check
                self.logger.debug(f"⏳ Waiting {CHECK_INTERVAL_SECONDS}s...")
                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)
                time.sleep(CHECK_INTERVAL_SECONDS)

    def _process_symbol(self, symbol, quotes):
        """Process a single symbol: get quote, run strategy, execute trades."""
        # Get current price
        quote = self.api.get_quote(symbol)

        if not quote:
            print_signal(symbol, SIGNAL_HOLD, "No data", 0)
            return

        price = quote["ltp"]
        quotes[symbol] = price

        # Feed price to strategy
        strategy = self.strategies[symbol]
        strategy.add_price(price)

        # Get signal
        signal = strategy.get_signal()
        info = strategy.get_info()
        info_str = " | ".join(f"{k}={v}" for k, v in info.items() if k != "strategy")
        print_signal(symbol, signal, info_str, price)

        # Execute trade based on signal
        if signal == SIGNAL_BUY:
            self._enter_position(symbol, price)
        elif signal == SIGNAL_SELL:
            if symbol in self.risk.positions:
                self._exit_position(symbol, price, "STRATEGY_SELL")

    def _enter_position(self, symbol, price):
        """Enter a new position if risk rules allow."""
        allowed, reason = self.risk.can_trade(symbol)
        if not allowed:
            self.logger.info(f"⛔ Trade blocked for {symbol}: {reason}")
            return

        quantity = self.risk.calculate_quantity(price)
        if quantity <= 0:
            self.logger.info(f"⛔ Insufficient capital for {symbol} @ ₹{price:.2f}")
            return

        try:
            result = self.api.place_order(symbol, "BUY", quantity)
            if result:
                self.risk.open_position(
                    symbol, "BUY", quantity, price, result["order_id"]
                )
        except GrowwAPIError as e:
            self.logger.error(f"❌ Failed to place buy order for {symbol}: {e}")

    def _exit_position(self, symbol, price, reason="SIGNAL"):
        """Exit an existing position."""
        if symbol not in self.risk.positions:
            return

        position = self.risk.positions[symbol]

        try:
            result = self.api.place_order(symbol, "SELL", position.quantity)
            if result:
                self.risk.close_position(symbol, price, reason)
        except GrowwAPIError as e:
            self.logger.error(f"❌ Failed to place sell order for {symbol}: {e}")


# ═══════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════

def main():
    """Parse arguments and start the bot."""
    parser = argparse.ArgumentParser(
        description="Groww Algo Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bot.py                     # Run with default config
  python bot.py --strategy RSI      # Use RSI strategy
  python bot.py --strategy MACD     # Use MACD strategy
  python bot.py --paper             # Force paper trading
  python bot.py --live              # Force live trading (⚠️ careful!)

Strategies: SMA_CROSSOVER, RSI, MACD, BOLLINGER
        """
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=["SMA_CROSSOVER", "RSI", "MACD", "BOLLINGER"],
        default=None,
        help="Trading strategy to use"
    )
    parser.add_argument(
        "--paper", action="store_true",
        help="Force paper trading mode"
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Force live trading mode (real money!)"
    )

    args = parser.parse_args()

    # Determine mode
    paper_mode = None
    if args.paper:
        paper_mode = True
    elif args.live:
        paper_mode = False

    # Setup logging
    logger = setup_logging()

    # Handle Ctrl+C gracefully
    bot = TradingBot(
        strategy_name=args.strategy,
        paper_mode=paper_mode
    )

    def signal_handler(sig, frame):
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start the bot
    bot.start()


if __name__ == "__main__":
    main()
