import asyncio
from src.data.ibkr_data_client import IBKRDataClient
from src.core.event_bus import EventBus

async def main():
    bus = EventBus()
    client = IBKRDataClient(symbols=["AAPL", "MSFT"])
    client.bind_event_bus(bus)

    await client.connect()
    await client.subscribe()

    try:
        while True:
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Stopping stream...")
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
