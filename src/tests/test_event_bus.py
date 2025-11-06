import asyncio
from src.core.event_bus import EventBus

bus = EventBus()

async def async_listener(data):
    print("[async listener]", data)

def sync_listener(data):
    print("[sync listener]", data)

bus.subscribe("MARKET_SNAPSHOT", async_listener)
bus.subscribe("MARKET_SNAPSHOT", sync_listener)

async def main():
    await bus.publish("MARKET_SNAPSHOT", {"price": 67800, "volume": 0.2})

if __name__ == "__main__":
    asyncio.run(main())
