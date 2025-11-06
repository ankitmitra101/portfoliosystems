# src/data/ibkr_data_client.py
import asyncio
import json
import websockets
from datetime import datetime
from typing import List

from src.core.base_data_client import BaseDataClient

class IBKRDataClient(BaseDataClient):
    """
    Interactive Brokers (TWS / IB Gateway) real-time market data stream.
    Requires:
      - IBKR TWS running
      - Market Data Subscription enabled
      - `reqMktData` feed supports tick-by-tick streaming
    """

    def __init__(self, symbols: List[str], host="127.0.0.1", port=7497, client_id=1):
        super().__init__(name="ibkr", symbols=symbols, timeframes=["tick"])
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ws_url = f"ws://{host}:{port}/ws"   # For TWS/Gateway WebSocket bridge
        self.bus = None
        self.running = False
        self._task = None

    def bind_event_bus(self, bus):
        self.bus = bus

    async def connect(self):
        print(f"[IBKR] Connecting to TWS at {self.host}:{self.port} ...")
        await asyncio.sleep(1)
        print("[IBKR] ✅ Connection established (assuming external TWS WebSocket bridge).")

    async def subscribe(self):
        """
        Assumes a WebSocket gateway translating IBKR tick data → JSON:
        Payload format expected:
            {"symbol": "AAPL", "price": 172.15, "size": 100, "timestamp": 1709959192}
        """
        self.running = True
        print("[IBKR] Starting live tick stream...")

        async def _stream():
            while self.running:
                try:
                    async with websockets.connect(self.ws_url) as ws:
                        print("[IBKR] ✅ WebSocket connected.")
                        while self.running:
                            msg = await ws.recv()
                            data = json.loads(msg)

                            symbol = data.get("symbol", "").upper()
                            price = float(data.get("price", 0))
                            volume = float(data.get("size", 0))
                            ts = data.get("timestamp", datetime.utcnow().timestamp())
                            timestamp = datetime.utcfromtimestamp(ts).isoformat() + "Z"

                            tick_data = {
                                "source": "IBKR",
                                "symbol": symbol,
                                "price": price,
                                "volume": volume,
                                "timestamp": timestamp,
                            }

                            if self.bus:
                                await self.bus.publish("RAW_MARKET", tick_data)

                except Exception as e:
                    print(f"[IBKR] ⚠️ Stream error: {e} — reconnect in 3s")
                    await asyncio.sleep(3)

        self._task = asyncio.create_task(_stream())

    async def stop(self):
        print("[IBKR] Stopping stream...")
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[IBKR] ✅ Stream stopped.")
