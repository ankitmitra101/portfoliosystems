# src/backtest/backtest_runner.py
import asyncio
import pandas as pd

from src.core.event_bus import EventBus
from src.portfolio.portfolio_handler import PortfolioHandler
from src.execution.order_execution_handler import OrderExecutionHandler
from src.backtest.historical_replayer import HistoricalReplayer
from src.strategy.multi_strategy_manager import MultiStrategyManager


# backtest_runner.py (top-level, before class)
def _resolve_strategy_callback(strat):
    """
    Return an ASYNC handler for MARKET_SNAPSHOT.
    Tries common method names; if only `score(candle)` exists, wrap it.
    """
    # Preferred standard
    if hasattr(strat, "on_market_snapshot"):
        fn = getattr(strat, "on_market_snapshot")
        if asyncio.iscoroutinefunction(fn):
            return fn
        async def _wrapped(snapshot):
            return fn(snapshot)
        return _wrapped

    # Legacy/common names
    for name in ("on_snapshot", "on_bar", "on_tick", "on_candle", "on_kline"):
        if hasattr(strat, name):
            fn = getattr(strat, name)
            if asyncio.iscoroutinefunction(fn):
                return fn
            async def _w(snapshot, _fn=fn):
                return _fn(snapshot)
            return _w

    # Fallback: strategies that expose `score(candle)` only
    if hasattr(strat, "score") and callable(getattr(strat, "score")):
        async def _adapter(snapshot):
            s = float(strat.score({
                "close": getattr(snapshot, "last", None) or getattr(snapshot, "bid", None) or getattr(snapshot, "ask", None),
                "high":  getattr(snapshot, "last", None) or getattr(snapshot, "bid", None) or getattr(snapshot, "ask", None),
                "low":   getattr(snapshot, "last", None) or getattr(snapshot, "bid", None) or getattr(snapshot, "ask", None),
            }))
            # publish a TARGET-style SIGNAL the portfolio understands
            await strat.bus.publish("SIGNAL", {
                "symbol": snapshot.symbol,
                "price":  snapshot.last,
                "direction": "TARGET",
                "score": s,
                "meta": {"scores": {type(strat).__name__: s}}
            })
        return _adapter

    raise AttributeError(f"{type(strat).__name__} has no usable handler (expected on_market_snapshot/on_snapshot/… or score(candle)).")


class BacktestRunner:
    """
    Can run:
      • Individual alpha strategies → each publishes its own TARGET
      • Combined alpha portfolio via MultiStrategyManager → single blended TARGET
    """

    def __init__(self, csv_path: str, symbol: str, initial_cash: float = 100000.0):
        self.csv_path = csv_path
        self.symbol = symbol.upper()
        self.initial_cash = initial_cash

    async def run_individual(self, strategies: list) -> pd.Series:
        """
        Run one or multiple individual alphas (each emits TARGET signals).
        """
        bus = EventBus()
        portfolio = PortfolioHandler(event_bus=bus, initial_cash=self.initial_cash)
        _exec = OrderExecutionHandler(mode="backtest", event_bus=bus)

        # Connect strategy signal flow (support various handler names)
        for strat in strategies:
            strat.bus = bus
            handler = _resolve_strategy_callback(strat)
            bus.subscribe("MARKET_SNAPSHOT", handler)

        # Track equity curve
        equity = []

        async def _mark(snapshot):
            unreal = 0.0
            for s, q in portfolio.positions.items():
                px = portfolio.last_prices.get(s, 0.0)
                unreal += q * px
            equity.append((snapshot.timestamp, portfolio.cash + unreal))

        bus.subscribe("MARKET_SNAPSHOT", _mark)

        await portfolio.start(live_mode=False)
        await HistoricalReplayer(bus, self.csv_path, self.symbol).run()

        if not equity:
            return pd.Series(dtype=float, name="equity")
        times, values = zip(*equity)
        return pd.Series(values, index=pd.to_datetime(times, utc=True), name="equity")

    async def run_combined_via_manager(self, alpha_weights=None) -> pd.Series:
        """
        Use MultiStrategyManager to blend signals into one TARGET.
        (This matches your LIVE trading pipeline behavior)
        """
        bus = EventBus()
        portfolio = PortfolioHandler(event_bus=bus, initial_cash=self.initial_cash)
        _exec = OrderExecutionHandler(mode="backtest", event_bus=bus)

        # Combined alpha logic
        MultiStrategyManager(bus, alpha_weights=alpha_weights, enable=True)

        equity = []

        async def _mark(snapshot):
            unreal = 0.0
            for s, q in portfolio.positions.items():
                px = portfolio.last_prices.get(s, 0.0)
                unreal += q * px
            equity.append((snapshot.timestamp, portfolio.cash + unreal))

        bus.subscribe("MARKET_SNAPSHOT", _mark)

        await portfolio.start(live_mode=False)
        await HistoricalReplayer(bus, self.csv_path, self.symbol).run()

        if not equity:
            return pd.Series(dtype=float, name="equity")
        times, values = zip(*equity)
        return pd.Series(values, index=pd.to_datetime(times, utc=True), name="equity")
