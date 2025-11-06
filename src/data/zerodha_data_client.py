# src/data/zerodha_data_client.py
import asyncio
from datetime import datetime
from kiteconnect import KiteTicker
from typing import List

from src.core.base_data_client import BaseDataClient

class ZerodhaDataClient(BaseDataClient):
    """
    Zerodha WebSocket Ticker (requires access token).
    Streams tick data → RAW_MARKET events.
    """

    def __init__(self, symbols: List[str], api_key: str, access_token: str):
        super().__init__(name="zerodha", symbols=symbols, timeframes=["tick"])
        self.api_key = api_key
        self.access_token = access_token
        self.bus = None
        self.running = False
        self.ticker = KiteTicker(api_key, access_token)

    def bind_event_bus(self, bus):
        self.bus = bus

    async def connect(self):
        print("[Zerodha] Connecting to Kite WebSocket...")
        await asyncio.sleep(1)
        print("[Zerodha] ✅ Connected.")

    async def subscribe(self):
        print("[Zerodha] Starting tick stream...")
        self.running = True

        def on_tick(ticks, ws=None):
            for t in ticks:
                symbol = str(t["instrument_token"])
                price = float(t["last_price"])
                volume = float(t.get("volume", 0))
                timestamp = datetime.utcnow().isoformat() + "Z"

                tick_data = {
                    "source": "ZERODHA",
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "timestamp": timestamp,
                }

                if self.bus:
                    asyncio.create_task(self.bus.publish("RAW_MARKET", tick_data))

        def on_close(ws, code, reason):
            print("[Zerodha] ⚠️ WebSocket closed:", reason)

        self.ticker.on_tick = on_tick
        self.ticker.on_close = on_close

        self.ticker.subscribe([int(s) for s in self.symbols])
        self.ticker.set_mode(self.ticker.MODE_FULL, self.symbols)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.ticker.connect)

    async def stop(self):
        print("[Zerodha] Stopping stream...")
        self.running = False
        self.ticker.close()
        print("[Zerodha] ✅ Stream stopped.")
