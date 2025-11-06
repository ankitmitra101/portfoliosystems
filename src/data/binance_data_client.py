# src/data/binance_data_client.py
import asyncio
import json
import random
import websockets
from datetime import datetime
from typing import List
import os
import csv

from src.core.base_data_client import BaseDataClient


class BinanceDataClient(BaseDataClient):
    """
    Binance Data Client supporting:
    - Mock/Testnet and Live modes
    - Tick or Candlestick streams
    - EventBus publishing (RAW_MARKET) for full pipeline integration
    """

    def __init__(self, symbols: List[str], timeframes: List[str], use_testnet=True, stream_type="tick", api_key=None, api_secret=None):
        super().__init__(name="binance", symbols=symbols, timeframes=timeframes)
        self._task = None
        self.bus = None
        self.use_testnet = use_testnet
        self.stream_type = stream_type  # "tick" or "candlestick"
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False

        if use_testnet:
            self.base_ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.base_ws_url = "wss://stream.binance.com:9443/ws"

    # -------------------------------
    # EventBus Binding
    # -------------------------------
    def bind_event_bus(self, bus):
        """Attach an EventBus instance for publishing downstream RAW_MARKET events."""
        self.bus = bus

    # -------------------------------
    # Core Connection Logic
    # -------------------------------
    async def connect(self):
        if self.use_testnet:
            print("[Binance] Connecting to Binance Testnet (mock)...")
        else:
            print("[Binance] Connecting to Binance Live API...")
        await asyncio.sleep(1)
        print("[Binance] ✅ Connection established.")

    async def subscribe(self):
        """Start streaming data."""
        if self.use_testnet:
            await self._mock_stream()
        else:
            await self._live_stream()

    # -------------------------------
    # Mock Stream (for local testing)
    # -------------------------------
    async def _mock_stream(self):
        print(f"[Binance] Subscribing to {self.symbols} ({self.stream_type}, mock mode)")
        self.running = True

        async def mock_stream():
            while self.running:
                timestamp = datetime.utcnow().isoformat() + "Z"
                for sym in self.symbols:
                    price = round(random.uniform(50000, 70000), 2)
                    volume = round(random.uniform(0.01, 0.1), 4)

                    tick_data = {
                        "source": "BINANCE",
                        "symbol": sym.upper(),
                        "price": price,
                        "volume": volume,
                        "timestamp": timestamp
                    }

                    # ✅ Publish raw tick event
                    if self.bus:
                        await self.bus.publish("RAW_MARKET", tick_data)

                await asyncio.sleep(1)

        self._task = asyncio.create_task(mock_stream())

    # -------------------------------
    # Live Stream (real-time WebSocket)
    # -------------------------------
    async def _live_stream(self):
        print(f"[Binance] Subscribing to {self.symbols} ({self.stream_type}, live mode)")
        self.running = True

        streams = []
        for sym in self.symbols:
            sym = sym.lower()
            if self.stream_type == "tick":
                streams.append(f"{sym}@trade")
            else:
                for tf in self.timeframes:
                    streams.append(f"{sym}@kline_{tf}")

        stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        print(f"[Binance] Connecting WebSocket to: {stream_url}")

        async def live_stream():
            while self.running:
                try:
                    async with websockets.connect(stream_url, ping_interval=20, ping_timeout=20) as ws:
                        print("[Binance] ✅ Live WebSocket connection established.")
                        while self.running:
                            msg = await ws.recv()
                            data = json.loads(msg)
                            payload_data = data.get("data", {})

                            if not payload_data:
                                continue

                            symbol = payload_data.get("s", "").upper()
                            timestamp = datetime.utcfromtimestamp(payload_data.get("E", 0) / 1000.0).isoformat() + "Z"

                            if self.stream_type == "tick":
                                # Trade stream
                                price = float(payload_data.get("p", 0))
                                vol = float(payload_data.get("q", 0))

                                tick_data = {
                                    "source": "BINANCE",
                                    "symbol": symbol,
                                    "price": price,
                                    "volume": vol,
                                    "timestamp": timestamp
                                }

                                # ✅ Publish raw tick event
                                if self.bus:
                                    await self.bus.publish("RAW_MARKET", tick_data)

                            else:
                                # Candle (kline) stream
                                k = payload_data.get("k", {})
                                if not k:
                                    continue

                                is_closed = k.get("x", False)
                                if is_closed:
                                    candle_data = {
                                        "source": "BINANCE",
                                        "symbol": symbol,
                                        "price": float(k["c"]),
                                        "volume": float(k["v"]),
                                        "timestamp": timestamp
                                    }

                                    # ✅ Treat closed candle as a tick event for aggregator
                                    if self.bus:
                                        await self.bus.publish("RAW_MARKET", candle_data)

                except Exception as e:
                    print(f"[Binance] ⚠️ WebSocket error: {e} — reconnecting in 3s")
                    await asyncio.sleep(3)

        self._task = asyncio.create_task(live_stream())

    # -------------------------------
    # Graceful Stop
    # -------------------------------
    async def stop(self):
        print("[Binance] Stopping stream...")
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[Binance] Stream stopped.")
