# src/engine.py
import asyncio
import json
import os
import time
import csv
from datetime import datetime

from src.core.event_bus import EventBus
from src.portfolio.portfolio_handler import PortfolioHandler
from src.execution.order_execution_handler import OrderExecutionHandler
from src.strategy.multi_strategy_manager import MultiStrategyManager
from src.utils.log_writer import LogWriter


class TradingEngine:
    """
    Unified Trading Engine supporting:
      - Backtest Mode: feed offline CSV candles/ticks
      - Replay Mode: replay logs/events.csv from live sandbox run
    """

    def __init__(self, mode="backtest", data_dir="logs"):
        self.mode = mode
        self.data_dir = data_dir
        self.bus = EventBus()
        self.log_writer = LogWriter()

        # Core components
        self.portfolio = PortfolioHandler(self.bus)
        self.execution = OrderExecutionHandler(mode="backtest", event_bus=self.bus)
        self.strategy_manager = MultiStrategyManager(self.bus)

        print(f"[ENGINE] Initialized in {mode.upper()} mode")

    # --------------------------------------------------------------------------
    # BACKTEST MODE
    # --------------------------------------------------------------------------
    async def run_backtest(self, data_source="logs/binance_btcusdt_candles.csv"):
        print("[ENGINE] Starting backtest...")
        if not os.path.exists(data_source):
            raise FileNotFoundError(f"Backtest data not found: {data_source}")

        with open(data_source, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                snapshot = {
                    "timestamp": row["timestamp_utc"],
                    "payload": {
                        "binance": {
                            "btcusdt": {
                                "close": float(row["close"]),
                                "open": float(row["open"]),
                                "high": float(row["high"]),
                                "low": float(row["low"]),
                                "volume": float(row["volume"]),
                            }
                        }
                    },
                    "meta": {"source": "backtest_csv"}
                }
                # Publish MARKET_SNAPSHOT event
                await self.bus.publish("MARKET_SNAPSHOT", type("Snapshot", (), snapshot))
                await asyncio.sleep(0.01)

        print("[ENGINE] Backtest complete ✅")

    # --------------------------------------------------------------------------
    # REPLAY MODE
    # --------------------------------------------------------------------------
    async def run_replay(self):
        """
        Replays the recorded sandbox events from logs/events.csv.
        Each event type is published to the bus in timestamp order.
        """
        path = os.path.join(self.data_dir, "events.csv")
        if not os.path.exists(path):
            raise FileNotFoundError("No events.csv found to replay.")

        print("[ENGINE] Starting REPLAY mode — reproducing sandbox trades...")
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row["topic"]
                payload = json.loads(row["payload"])

                await self.bus.publish(topic, payload)
                await asyncio.sleep(0.01)

        print("[ENGINE] Replay complete ✅")

    # --------------------------------------------------------------------------
    # ENTRY POINT
    # --------------------------------------------------------------------------
    def run(self):
        print(f"[ENGINE] 🚀 Running in {self.mode} mode...")
        if self.mode == "replay":
            asyncio.run(self.run_replay())
        else:
            asyncio.run(self.run_backtest())

        print("[ENGINE] Finished execution.")

    def stop(self):
        print("[ENGINE] Stopped.")
