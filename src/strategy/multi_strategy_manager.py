# src/strategy/multi_strategy_manager.py
import asyncio
from datetime import datetime
from collections import defaultdict

from src.utils.log_writer import LogWriter
from src.strategy.strategy_mean_reversion import MeanReversionStrategy
from src.strategy.strategy_momentum import MomentumStrategy
from src.strategy.strategy_atr_gaussian import ATRGaussianStrategy
from src.strategy.strategy_macd_fibonacci import MACDFibonacciStrategy
from src.strategy.strategy_generic_alpha import GenericAlphaStrategy

THRESHOLD = 0.05   # Minimum conviction to trade


class MultiStrategyManager:
    """
    Threshold-Trading Version
    - Combine alpha scores → final score
    - If |score| < THRESHOLD → HOLD (no target shift)

    Backtest toggle:
      enable=True  → subscribe & publish combined TARGET (LIVE/COMBINED BACKTEST)
      enable=False → do nothing (INDIVIDUAL-BY-ALPHA BACKTEST)
    """

    def __init__(self, bus, alpha_weights=None, enable=True):
        self.bus = bus
        self.log = LogWriter()
        self.enabled = bool(enable)

        self.alphas = {
            "meanreversion": MeanReversionStrategy(),
            "momentum": MomentumStrategy(),
            "atrgaussian": ATRGaussianStrategy(),
            "macdfibonacci": MACDFibonacciStrategy(),
            "genericalpha": GenericAlphaStrategy(),
        }

        self.alpha_weights = (
            {name: 1.0 / len(self.alphas) for name in self.alphas}
            if alpha_weights is None else alpha_weights
        )

        self.virt_pos = defaultdict(lambda: defaultdict(float))
        self.last_price = defaultdict(float)
        self.last_published_score = defaultdict(float)

        if self.enabled:
            self.bus.subscribe("MARKET_SNAPSHOT", self.on_market_snapshot)
            print("[DEBUG] MultiStrategyManager subscribed to MARKET_SNAPSHOT")

    # ---------- Attribution ----------
    def _update_attribution(self, symbol: str, price: float, per_alpha_units: dict):
        self.last_price[symbol] = price
        for alpha, du in per_alpha_units.items():
            self.virt_pos[alpha][symbol] += du

        virt_pnl = {
            alpha: sum(qty * self.last_price.get(sym, 0.0) for sym, qty in self.virt_pos[alpha].items())
            for alpha in self.alphas
        }

        self.log._write_row(
            "alpha_attribution.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "symbol": symbol,
                **{f"pnl_{a}": virt_pnl[a] for a in self.alphas},
                **{f"pos_{a}_{symbol}": self.virt_pos[a][symbol] for a in self.alphas},
            },
            ["timestamp_utc", "symbol"]
            + [f"pnl_{a}" for a in self.alphas]
            + [f"pos_{a}_{symbol}" for a in self.alphas]
        )

    # ---------- Helper: accept both dict snapshots and object snapshots ----------
    @staticmethod
    def _extract_candle(snapshot):
        """
        Returns (symbol, price, candle_dict, timestamp)
        Supports:
          • dict snapshot with snapshot['payload']
          • object with attributes: symbol, last, volume, timestamp
        """
        try:
            # object style
            symbol = snapshot.symbol.upper()
            price = float(getattr(snapshot, "last", getattr(snapshot, "price", 0.0)))
            ts = getattr(snapshot, "timestamp", datetime.utcnow())
            candle = {
                "symbol": symbol,
                "close": price,
                "open": price,
                "high": price,
                "low":  price,
                "volume": float(getattr(snapshot, "volume", 0.0)),
                "timestamp": ts,
            }
            if price > 0:
                return symbol, price, candle, ts
        except Exception:
            pass

        # dict style (legacy)
        symbol = snapshot["symbol"].upper()
        payload = snapshot["payload"]
        price = float(payload.get("close") or payload.get("price"))
        candle = {
            "symbol": symbol,
            "close": price,
            "open": payload.get("open", price),
            "high": payload.get("high", price),
            "low":  payload.get("low",  price),
            "volume": payload.get("volume", 0.0),
            "timestamp": snapshot["timestamp"],
        }
        return symbol, price, candle, snapshot["timestamp"]

    # ---------- Main Handler ----------
    async def on_market_snapshot(self, snapshot):
        if not self.enabled:
            return  # backtest (individual) → manager idle

        try:
            symbol, price, candle, _ts = self._extract_candle(snapshot)
        except Exception:
            return

        # ---- Per-alpha scores ----
        scores = {}
        for name, alpha in self.alphas.items():
            try:
                scores[name] = float(alpha.score(candle))
            except Exception:
                scores[name] = 0.0

        # ---- Combine ----
        combined = sum(self.alpha_weights[name] * scores[name] for name in self.alphas)

        # ---- Threshold & clip ----
        if abs(combined) < THRESHOLD:
            combined = 0.0
        combined = max(-1.0, min(1.0, combined))

        # ---- Log ----
        self.log._write_row(
            "alpha_scores.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "price": price,
                **{f"score_{k}": v for k, v in scores.items()},
                "combined_after_threshold": combined,
            },
            ["timestamp_utc", "symbol", "price"]
            + [f"score_{k}" for k in self.alphas]
            + ["combined_after_threshold"]
        )

        # ---- Attribution (no drift) ----
        self._update_attribution(symbol, price, {a: 0.0 for a in self.alphas})

        # ---- Prevent signal spam ----
        if abs(combined - self.last_published_score[symbol]) < 0.05:
            return
        self.last_published_score[symbol] = combined

        # ---- Publish final TARGET signal ----
        await self.bus.publish("SIGNAL", {
            "symbol": symbol,
            "direction": "TARGET",
            "score": combined,
            "price": price,
            "meta": {
                "alpha": "multi",
                "weights": self.alpha_weights,
                "scores": scores,
            }
        })
