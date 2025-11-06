


import asyncio
from src.core.engine import TradingEngine

async def main():
    engine = TradingEngine("config.yaml")
    await engine.data_handler.start()
    engine.run(mode="mock")

if __name__ == "__main__":
    asyncio.run(main())
