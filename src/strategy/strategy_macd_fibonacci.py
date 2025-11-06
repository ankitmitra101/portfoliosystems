"""
MACD + Fibonacci Momentum Strategy (Score-Based)

- Streaming-safe (no pandas)
- Outputs score in [-1, +1]
- Smooth, stable, low-churn signal
"""

import numpy as np


class MACDFibonacciStrategy:
    def __init__(self, fast=12, slow=26, signal=9, sensitivity=4.0, smooth_alpha=0.25):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.sensitivity = sensitivity      # scale hist response
        self.smooth_alpha = smooth_alpha    # score smoothing factor

        self.ema_fast = None
        self.ema_slow = None
        self.ema_signal = None
        self.prev_score = 0.0

    def score(self, candle: dict) -> float:
        close = float(candle["close"])

        # --------------------------------------
        # Initialize EMAs on first update
        # --------------------------------------
        if self.ema_fast is None:
            self.ema_fast = close
            self.ema_slow = close
            self.ema_signal = 0.0
            return 0.0

        # EMA coefficients
        k_fast = 2 / (self.fast + 1)
        k_slow = 2 / (self.slow + 1)
        k_signal = 2 / (self.signal + 1)

        # Update EMAs
        self.ema_fast += k_fast * (close - self.ema_fast)
        self.ema_slow += k_slow * (close - self.ema_slow)

        macd = self.ema_fast - self.ema_slow
        self.ema_signal += k_signal * (macd - self.ema_signal)

        hist = macd - self.ema_signal

        # Base signal (tanh normalization)
        raw_score = float(np.tanh(hist * self.sensitivity))

        # --------------------------------------
        # ✅ Smooth the score to prevent flip-flop
        # --------------------------------------
        score = self.smooth_alpha * raw_score + (1 - self.smooth_alpha) * self.prev_score
        self.prev_score = score

        # --------------------------------------
        # ✅ Deadband → reduce noise near zero
        # --------------------------------------
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
            "meta": {"scores": {"MACDFIB": s}}
        })
