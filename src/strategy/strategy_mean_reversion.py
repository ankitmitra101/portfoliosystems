"""
Mean Reversion Strategy (Score-Based)

- Computes Z-score relative to rolling mean
- Outputs score ∈ [-1, +1]
- Includes smoothing + deadband to prevent noisy reversals
"""

import numpy as np
from collections import deque


class MeanReversionStrategy:
    def __init__(self, window=20, entry_z=2.0, max_history=300, smooth_alpha=0.25):
        self.window = window
        self.entry_z = entry_z
        self.smooth_alpha = smooth_alpha     # smoothing factor

        self.prices = deque(maxlen=max_history)
        self.prev_score = 0.0                # store previous output

    def score(self, candle: dict) -> float:
        close = float(candle["close"])
        self.prices.append(close)

        # Not enough data yet
        if len(self.prices) < self.window:
            return 0.0

        prices_np = np.array(self.prices, dtype=float)
        recent = prices_np[-self.window:]

        mean = recent.mean()
        std = recent.std() + 1e-9

        # Z-score of how far price deviates from mean
        z = (close - mean) / std

        # Raw reversion signal (price high → short, low → long)
        raw_alpha = -z  # negative z = buy, positive z = sell

        # Normalize into stable range
        raw_score = float(np.tanh(raw_alpha / self.entry_z))

        # ✅ Smooth score to avoid flip-flop
        score = self.smooth_alpha * raw_score + (1 - self.smooth_alpha) * self.prev_score
        self.prev_score = score

        # ✅ Deadband: ignore tiny signals
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
            "meta": {"scores": {"MEANREV": s}}
        })
