# src/run_engine.py
import asyncio
from src.core.event_bus import EventBus
from src.data.binance_data_client import BinanceDataClient
from src.execution.order_execution_handler import OrderExecutionHandler
from src.portfolio.portfolio_handler import PortfolioHandler
from src.strategy.multi_strategy_manager import MultiStrategyManager
from src.utils.candlestick_aggregator import CandlestickAggregator  # ✅ correct filename

async def main():
    # -----------------------------
    # 1️⃣ Initialize Event Bus
    # -----------------------------
    bus = EventBus()

    # -----------------------------
    # 2️⃣ Initialize Data Client (Binance)
    # -----------------------------
    client = BinanceDataClient(
        symbols=["btcusdt", "ethusdt"],
        timeframes=["1m"],
        use_testnet=False,     # ✅ Live data
        stream_type="tick"
    )
    client.bind_event_bus(bus)

    # -----------------------------
    # 3️⃣ Initialize Candlestick Aggregator
    # -----------------------------
    aggregator = CandlestickAggregator(bus,timeframes=("1m", "5m", "1h"))
    # ✅ Subscribe aggregator to receive raw tick data
    bus.subscribe("RAW_MARKET", aggregator.on_tick)
    print("[Aggregator] Subscribed to RAW_MARKET events")

    # -----------------------------
    # 4️⃣ Initialize Core Components
    # -----------------------------
    strategy_manager = MultiStrategyManager(bus)                     # 5 Alphas
    portfolio = PortfolioHandler(event_bus=bus, initial_cash=100000) # PnL & positions
    execution = OrderExecutionHandler(mode="paper", event_bus=bus)    # ✅ live mode now

    # -----------------------------
    # 5️⃣ Connect Binance Client
    # -----------------------------
    await client.connect()
    await client.subscribe()

    print("\n[ENGINE] 🚀 Multi-Strategy Event-Driven System Initialized")
    print("[ENGINE] Components: BinanceDataClient → Aggregator → MultiStrategyManager → Portfolio → Execution\n")

    try:
        while True:
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("\n[ENGINE] ⚙️  Stopping system...")
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
