# src/execution/order_execution_handler.py

import asyncio
import random
from datetime import datetime
from src.core.schemas import Order, Fill
from src.utils.log_writer import LogWriter


class OrderExecutionHandler:
    """
    Handles:
      - SEND: Portfolio → Execution
      - FILL: Execution → Portfolio

    IMPORTANT:
      Meta (alpha scores) MUST NOT be serialized to broker/logs,
      but MUST be restored when generating Fill → Portfolio update.
    """

    def __init__(self, mode="paper", event_bus=None, slippage_bps=3, commission_bps=1):
        self.mode = mode.lower()
        self.bus = event_bus
        self.slippage_bps = slippage_bps
        self.commission_bps = commission_bps
        self.log_writer = LogWriter()

        # Internal store for meta attribution
        self._order_meta = {}   # order_id -> meta

        if self.bus:
            self.bus.subscribe("ORDER", self.on_order)
            print(f"[DEBUG] ExecutionHandler active in MODE = {self.mode.upper()}")

    # --------------------------------------------------------
    async def on_order(self, order: Order):
       

        # ✅ Store meta internally (scores etc must NOT go to logs/websocket)
        self._order_meta[order.order_id] = order.meta or {}

        # ✅ Log order *without* meta to avoid datetime JSON error
        self.log_writer.log_order(
            order_id=order.order_id,
            alpha=(order.meta.get("alpha") if order.meta else "multi"),
            side=order.direction,
            qty=order.quantity,
            price=order.price,
            status="NEW",
            exchange=(order.meta.get("exchange") if order.meta else "BINANCE"),
            raw_json={   # sanitized payload only
                "symbol": order.symbol,
                "qty": order.quantity,
                "side": order.direction,
                "price": order.price,
                "order_id": order.order_id,
            },
        )

        if self.mode in ("paper", "backtest"):
            await self._simulate_fill(order)
        else:
            await self._execute_real(order)

    # --------------------------------------------------------
    async def _simulate_fill(self, order: Order):
        await asyncio.sleep(random.uniform(0.05, 0.15))  # simulated latency

        slippage = (self.slippage_bps / 10000.0) * order.price
        fill_price = order.price + slippage if order.direction == "BUY" else order.price - slippage
        commission = (self.commission_bps / 10000.0) * (fill_price * order.quantity)

        # ✅ Restore attribution meta
        meta = self._order_meta.pop(order.order_id, {})

        fill = Fill(
            symbol=order.symbol,
            quantity=order.quantity,
            direction=order.direction,
            fill_price=fill_price,
            timestamp=datetime.utcnow(),
            commission=commission,
            order_id=order.order_id,
            meta=meta,   # ← CRITICAL for Portfolio attribution
        )

        # ✅ Log sanitized fill (no raw meta, no datetime in JSON)
        self.log_writer.log_fill(
            fill_id=f"FILL-{int(datetime.utcnow().timestamp()*1000)}",
            order_id=order.order_id,
            alpha=meta.get("alpha", "multi"),
            symbol=order.symbol,
            qty=order.quantity,
            price=fill_price,
            commission=commission,
            exchange=meta.get("exchange", "BINANCE"),
            raw_json={
                "symbol": order.symbol,
                "qty": order.quantity,
                "side": order.direction,
                "price": fill_price,
                "timestamp": fill.timestamp.isoformat(),
            },
        )

       
        if self.bus:
            await self.bus.publish("FILL", fill)

    # --------------------------------------------------------
    async def _execute_real(self, order: Order):
        print(f"[Execution] 🚀 LIVE ORDER SENT → {order}")
        await self._simulate_fill(order)
