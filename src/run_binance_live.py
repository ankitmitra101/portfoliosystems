# src/run_binance_live.py
import asyncio
from src.data.binance_data_client import BinanceDataClient
from src.core.event_bus import EventBus

async def main():
    bus = EventBus()
    client = BinanceDataClient(
        symbols=["btcusdt"],
        timeframes=["1m"],
        use_testnet=False,
        stream_type="tick"
    )
    client.bind_event_bus(bus)

    await client.connect()
    await client.subscribe()   # start stream task (non-blocking inside)

    # keep program alive to continuously receive messages
    try:
        while True:
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Stopping stream...")
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
