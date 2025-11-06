"""
ATR + Gaussian Filter Strategy (Score-based)

- Maintains rolling OHLC history
- Computes Gaussian-smoothed close & ATR
- Score = (close - smooth) / ATR → normalized & smoothed
"""

import numpy as np
from scipy.ndimage import gaussian_filter1d
from collections import deque


class ATRGaussianStrategy:
    def __init__(self, gauss_sigma=2.0, atr_window=14, max_history=200):
        self.gauss_sigma = gauss_sigma
        self.atr_window = atr_window

        self.high = deque(maxlen=max_history)
        self.low = deque(maxlen=max_history)
        self.close = deque(maxlen=max_history)

        # For signal smoothing
        self.prev_score = 0.0

    def _atr_now(self):
        if len(self.close) < self.atr_window + 1:
            return None

        highs = np.array(self.high, dtype=float)
        lows = np.array(self.low, dtype=float)
        closes = np.array(self.close, dtype=float)
        prev_close = np.roll(closes, 1)
        prev_close[0] = closes[0]

        tr = np.maximum.reduce([
            highs - lows,
            np.abs(highs - prev_close),
            np.abs(lows - prev_close),
        ])

        return float(tr[-self.atr_window:].mean())

    def score(self, candle: dict) -> float:
        """
        Output: score in [-1, 1]
        Higher score → BUY bias
        Lower score → SELL bias
        """
        h = float(candle.get("high", candle["close"]))
        l = float(candle.get("low", candle["close"]))
        c = float(candle["close"])

        self.high.append(h)
        self.low.append(l)
        self.close.append(c)

        if len(self.close) < self.atr_window + 5:
            return 0.0

        closes = np.array(self.close, dtype=float)

        smooth = gaussian_filter1d(closes, sigma=self.gauss_sigma)[-1]
        atr = self._atr_now() or 1e-9

        # Raw unbounded volatility-normalized deviation
        raw = (c - smooth) / atr

        # Clip to [-1, 1]
        raw_score = np.clip(raw / 2.0, -1.0, 1.0)

        # -----------------------
        # ✅ Smoothing (to avoid flipping positions constantly)
        # -----------------------
        alpha = 0.2  # 0.1–0.3 works best
        score = alpha * raw_score + (1 - alpha) * self.prev_score
        self.prev_score = score

        # -----------------------
        # ✅ Deadband / Neutral Zone
        # -----------------------
        if abs(score) < 0.2:
            score = 0.0

        return float(score)

    async def on_snapshot(self, snap):
        """
        MARKET_SNAPSHOT → compute score → emit SIGNAL (score → target position)
        """
        s = self.score({
            "close": snap.last,
            "high": snap.last,
            "low": snap.last
        })

        await self.bus.publish("SIGNAL", {
            "symbol": snap.symbol,
            "price": snap.last,
            "direction": "TARGET",
            "score": s,
            "meta": {"scores": {"ATRGauss": s}}
        })
