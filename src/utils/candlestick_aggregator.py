# src/utils/candle_aggregator.py
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.utils.log_writer import LogWriter


class CandlestickAggregator:
    """
    Universal tick-to-candle aggregator.
    Works for Binance, IBKR, Zerodha, FX feeds — any tick stream.

    Expected RAW_MARKET tick format:
    {
        "source": "BINANCE" | "IBKR" | "ZERODHA",
        "symbol": "BTCUSDT" | "RELIANCE" | "AAPL",
        "price": float,
        "volume": float,
        "timestamp": "2025-11-06T12:01:05.123Z"
    }
    """

    def __init__(self, bus, timeframes=("1m", "5m", "1h")):
        self.bus = bus
        self.timeframes = self._parse_timeframes(timeframes)
        self.buffers = defaultdict(lambda: defaultdict(list))
        self.log_writer = LogWriter()

        # Subscribe to all tick events
        self.bus.subscribe("RAW_MARKET", self.on_tick)
        print("[Aggregator] Subscribed to RAW_MARKET events")

    # ------------------------------------------------------------------
    # Helper Functions
    # ------------------------------------------------------------------
    def _parse_timeframes(self, tfs):
        mapping = {}
        for tf in tfs:
            if tf.endswith("m"):
                mapping[tf] = int(tf[:-1]) * 60
            elif tf.endswith("h"):
                mapping[tf] = int(tf[:-1]) * 3600
            else:
                raise ValueError(f"Unsupported timeframe: {tf}")
        return mapping

    def _get_bucket_start(self, ts, secs):
        ts = ts.replace(second=0, microsecond=0)
        delta = (ts.minute * 60 + ts.second) % secs
        return ts - timedelta(seconds=delta)

    # ------------------------------------------------------------------
    # Core Tick Handler (Async)
    # ------------------------------------------------------------------
    async def on_tick(self, tick):
        """
        Handle incoming RAW_MARKET ticks and publish completed candles.
        """
        try:
            ts = datetime.fromisoformat(tick["timestamp"].replace("Z", "+00:00"))
            symbol = tick["symbol"].upper()
            price = float(tick["price"])
            volume = float(tick.get("volume", 0))
        except Exception as e:
            print(f"[Aggregator] ⚠️ Bad tick data: {e}, {tick}")
            return

        finished_candles = self.update_tick(symbol, price, volume, ts)

        # Publish newly completed candles downstream
        for candle in finished_candles:
            msg = {
                "timestamp": candle["start"].replace(tzinfo=timezone.utc).isoformat(),
                "source": tick["source"],
                "symbol": symbol,
                "timeframe": candle["tf"],
                "payload": {
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "is_closed": True,
                },
                "meta": {"origin": tick["source"]},
            }

            # ✅ Publish to strategy layer
            await self.bus.publish("MARKET_SNAPSHOT", msg)

            # ✅ Log to disk for replication
            try:
                self.log_writer.log_candle(
                    source=tick["source"],
                    symbol=symbol,
                    o=candle["open"],
                    h=candle["high"],
                    l=candle["low"],
                    c=candle["close"],
                    v=candle["volume"],
                    exchange=tick["source"],
                    tf=candle["tf"],
                    raw_json=msg,
                )
            except Exception as e:
                print(f"[Aggregator] ⚠️ Logging error: {e}")

            print(f"[Aggregator] 🟢 Emitted MARKET_SNAPSHOT for {symbol} [{candle['tf']}] @ {candle['close']}")

    # ------------------------------------------------------------------
    # Candle Construction
    # ------------------------------------------------------------------
    def update_tick(self, symbol, price, volume, timestamp):
        """Add one tick, return list of completed candles."""
        finished = []

        for tf, secs in self.timeframes.items():
            bucket_start = self._get_bucket_start(timestamp, secs)
            buf = self.buffers[symbol][tf]

            # ✅ New bucket → close the previous one
            if not buf or buf[-1]["start"] != bucket_start:
                if buf:
                    buf[-1]["tf"] = tf
                    finished.append(buf[-1])
                buf.append({
                    "start": bucket_start,
                    "tf": tf,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                })
            else:
                # ✅ Update ongoing candle
                bar = buf[-1]
                bar["high"] = max(bar["high"], price)
                bar["low"] = min(bar["low"], price)
                bar["close"] = price
                bar["volume"] += volume

        return finished
