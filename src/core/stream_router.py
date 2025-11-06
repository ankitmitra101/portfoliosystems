# src/core/stream_router.py
import asyncio
import heapq
from datetime import datetime, timedelta
from collections import defaultdict
import time
from src.utils.log_writer import LogWriter

ISOFMT = "%Y-%m-%dT%H:%M:%S.%fZ"

class StreamRouter:
    """
    Receives RAW_MARKET events from any DataClient and routes them to per-symbol queues.
    Also does a tiny buffering/watermark to order events by timestamp.
    """
    def __init__(self, bus, buffer_ms=200):
        self.bus = bus
        self.queues = {}  # symbol -> asyncio.Queue
        self.buffer_ms = buffer_ms
        self.log = LogWriter()
        # subscribe to raw events
        self.bus.subscribe("RAW_MARKET", self.on_raw)
        print("[Router] subscribed to RAW_MARKET")

    async def on_raw(self, raw_event):
        # raw_event must contain timestamp (ISO), symbol, source, payload, timeframe
        # log raw inbound
        try:
            self.log.log_event("RAW_MARKET", raw_event)
        except Exception:
            pass

        symbol = raw_event["symbol"].upper()
        q = self.queues.get(symbol)
        if q is None:
            q = asyncio.Queue(maxsize=10000)
            self.queues[symbol] = q
            # spawn aggregator consumer for this symbol
            asyncio.create_task(self._symbol_consumer(symbol, q))

        # put event into symbol queue
        await q.put(raw_event)

    async def _symbol_consumer(self, symbol, q: asyncio.Queue):
        """
        Pulls events from per-symbol queue, buffers for buffer_ms milliseconds,
        then yields in timestamp order to aggregator.
        """
        buffer = []
        last_flush = time.time()
        while True:
            try:
                item = await q.get()
            except asyncio.CancelledError:
                break

            # push into heap by timestamp
            ts = item.get("timestamp")
            # convert ISO -> epoch
            try:
                epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                epoch = time.time()
            heapq.heappush(buffer, (epoch, item))

            # flush policy: either buffer size or time window
            now = time.time()
            if (now - last_flush) * 1000 >= self.buffer_ms or len(buffer) > 50:
                await self._flush_buffer(symbol, buffer)
                last_flush = now

    async def _flush_buffer(self, symbol, buffer):
        # pop all items in order and publish to aggregator
        while buffer:
            _, event = heapq.heappop(buffer)
            # publish ordered event for aggregator to consume
            await self.bus.publish("ORDERED_MARKET", event)
