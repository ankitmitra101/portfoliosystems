# src/tests/test_order_execution.py
import asyncio
from datetime import datetime

from src.core.event_bus import EventBus
from src.core.schemas import Order
from src.execution.order_execution_handler import OrderExecutionHandler


async def main():
    # Create the event bus
    bus = EventBus()

    # Create the execution handler (simulate fills)
    execution_handler = OrderExecutionHandler(mode="backtest", event_bus=bus)

    # Example order event
    order = Order(
        symbol="BTCUSDT",
        quantity=0.01,
        direction="BUY",
        price=68000,
        order_id=f"ORD-{int(datetime.utcnow().timestamp())}",
        meta={"alpha": "alpha_1", "exchange": "BINANCE"},
    )

    # Publish order → triggers simulated fill and logging
    await bus.publish("ORDER", order)

    print("\n✅ Order sent & simulated fill logged.\nCheck logs/orders.csv and logs/fills.csv\n")


if __name__ == "__main__":
    asyncio.run(main())
