"""
Generic Alpha Strategy (Multi-Factor Blend, Score Version)

Factors:
- Momentum (trend direction)
- Mean reversion (z-score vs mean)
- Volatility compression (anticipating breakout risk)

Outputs a score ∈ [-1, +1].
Higher → BUY bias, Lower → SELL bias.
"""

import numpy as np
from collections import deque


class GenericAlphaStrategy:
    def __init__(self, lookback=20, max_history=300):
        self.lookback = lookback
        self.closes = deque(maxlen=max_history)

        # For smoothing stability
        self.prev_score = 0.0

    def score(self, candle: dict) -> float:
        close = float(candle["close"])
        self.closes.append(close)

        # Not enough history → no conviction
        if len(self.closes) < self.lookback:
            return 0.0

        closes = np.array(self.closes, dtype=float)
        recent = closes[-self.lookback:]

        # -----------------------
        # Factor 1: Momentum
        # -----------------------
        momentum = (recent[-1] - recent[0]) / (abs(recent[0]) + 1e-9)

        # -----------------------
        # Factor 2: Mean Reversion (Z-Score)
        # -----------------------
        mean = recent.mean()
        std = recent.std() + 1e-9
        zscore = (recent[-1] - mean) / std

        # -----------------------
        # Factor 3: Volatility Compression Breakout Signal
        # -----------------------
        vol = np.std(np.diff(recent)) + 1e-9

        # -----------------------
        # Composite Alpha Score (raw)
        # -----------------------
        raw = (0.5 * momentum) - (0.3 * zscore) - (0.2 * vol)

        # Soft normalization
        raw_score = float(np.tanh(raw))

        # -----------------------
        # ✅ Smoothing
        # -----------------------
        alpha = 0.25  # Lower = smoother, Higher = more reactive
        score = alpha * raw_score + (1 - alpha) * self.prev_score
        self.prev_score = score

        # -----------------------
        # ✅ Deadband / Neutral Zone
        # -----------------------
        if abs(score) < 0.15:
            score = 0.0

        return float(score)

    async def on_snapshot(self, snap):
        s = self.score({"close": snap.last})

        await self.bus.publish("SIGNAL", {
            "symbol": snap.symbol,
            "price": snap.last,
            "direction": "TARGET",
            "score": s,
            "meta": {"scores": {"GENERIC": s}}
        })
