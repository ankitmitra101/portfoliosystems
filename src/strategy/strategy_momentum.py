"""
Momentum Crossover Strategy (Score-Based)

Uses short-term vs long-term exponential moving averages (EMAs).
Outputs a stable momentum score ∈ [-1, +1].

- Smooth
- Trend-following
- Low churn
"""

import numpy as np
from collections import deque


class MomentumStrategy:
    def __init__(self, short_window=5, long_window=12, smooth_alpha=0.25):
        self.short_window = short_window
        self.long_window = long_window
        self.smooth_alpha = smooth_alpha    # smoothing for score

        self.ema_short = None
        self.ema_long = None
        self.prev_score = 0.0

    def score(self, candle: dict) -> float:
        close = float(candle["close"])

        # Initialize EMAs
        if self.ema_short is None:
            self.ema_short = close
            self.ema_long = close
            return 0.0

        k_short = 2 / (self.short_window + 1)
        k_long  = 2 / (self.long_window + 1)

        # Update EMAs
        self.ema_short += k_short * (close - self.ema_short)
        self.ema_long  += k_long  * (close - self.ema_long)

        spread = self.ema_short - self.ema_long

        # Normalize momentum into [-1, +1]
        raw_score = float(np.tanh(spread * 4.0))

        # ✅ Smooth to avoid thrashing
        score = self.smooth_alpha * raw_score + (1 - self.smooth_alpha) * self.prev_score
        self.prev_score = score

        # ✅ Ignore tiny noise
        if abs(score) < 0.10:
            score = 0.0

        return float(score)

    async def on_snapshot(self, snap):
        s = self.score({"close": snap.last})

        await self.bus.publish("SIGNAL", {
            "symbol": snap.symbol,
            "price": snap.last,
            "direction": "TARGET",
            "score": s,
            "meta": {"scores": {"MOMENTUM": s}}
        })
