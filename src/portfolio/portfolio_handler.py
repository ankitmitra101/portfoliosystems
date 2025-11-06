# src/portfolio/portfolio_handler.py
import asyncio
from datetime import datetime
from collections import defaultdict

from src.core.schemas import Order, Fill
from src.utils.log_writer import LogWriter

MIN_TRADE_UNITS = 1e-6          # absolute floor (do nothing below this)
DELTA_THRESHOLD = 0.0004        # <- noise filter: ignore tiny target changes
DEFAULT_MAX_UNITS = 0.01


class PortfolioHandler:
    """
    TARGET score → target position → delta order → fill updates.
    Tracks:
      • Real portfolio PnL
      • Per-alpha PnL attribution (accurate fill-based accounting)
    """

    def __init__(self, event_bus, initial_cash=100000.0, max_units=None):
        self.bus = event_bus
        self.log = LogWriter()

        self.cash = float(initial_cash)
        self.positions = defaultdict(float)            # symbol -> net qty
        self.last_prices = defaultdict(float)          # symbol -> last trade/mark price

        # Ensure max_units always works per symbol (and never KeyErrors)
        if isinstance(max_units, dict):
            self.max_units = defaultdict(lambda: DEFAULT_MAX_UNITS, max_units)
        else:
            self.max_units = defaultdict(lambda: DEFAULT_MAX_UNITS)

        # α attribution: alpha -> symbol -> exposure qty*score
        self.alpha_virtual_pos = defaultdict(lambda: defaultdict(float))

        # Subscriptions
        self.bus.subscribe("SIGNAL", self.on_signal)
        self.bus.subscribe("FILL", self.on_fill)

        # Don’t schedule here — schedule from engine after loop starts
        self._state_task = None

    async def start(self, live_mode=True):
        """
        Start periodic equity reporting.
        In BACKTEST → we do NOT run the infinite reporting loop.
        """
        if not live_mode:
            return  # no periodic prints/marks during backtest

        if self._state_task is None:
            self._state_task = asyncio.create_task(self._report_state())

    # ----------------------------------------------------------------------
    async def on_signal(self, signal):
        """Convert score → target position → delta → ORDER"""
        try:
            if signal.get("direction") != "TARGET":
                return

            symbol = signal["symbol"].upper()
            price = float(signal["price"])
            score = float(signal.get("score", 0.0))
            meta = signal.get("meta") or {}

            # Ensure scores dict always exists for attribution
            if not isinstance(meta.get("scores"), dict) or not meta["scores"]:
                meta = {**meta, "scores": {"GENERIC": score}}

            self.last_prices[symbol] = price

            # Score → bounded target exposure
            target = max(-1.0, min(1.0, score)) * self.max_units[symbol]
            current = self.positions[symbol]
            delta = target - current

            # Ignore micro noise
            if abs(delta) < max(DELTA_THRESHOLD, MIN_TRADE_UNITS):
                return

            direction = "BUY" if delta > 0 else "SELL"
            qty = abs(delta)

            order = Order(
                symbol=symbol,
                quantity=qty,
                direction=direction,
                price=price,
                order_id=f"ORD-{datetime.utcnow().timestamp():.6f}",
                meta=meta,
            )

            # (silenced) verbose prints removed for speed
            await self.bus.publish("ORDER", order)

        except Exception as e:
            # Minimal error surfacing
            print("[PORTFOLIO][ERROR] on_signal:", e)
            raise

    # ----------------------------------------------------------------------
    async def on_fill(self, fill: Fill):
        """Apply fill → update cash, position, attribution, PnL."""
        try:
            symbol = fill.symbol.upper()
            price = float(fill.fill_price)
            qty_signed = float(fill.quantity) if fill.direction.upper() == "BUY" else -float(fill.quantity)

            # Position adjust
            self.positions[symbol] += qty_signed
            self.last_prices[symbol] = price

            # Cash update (spot-style)
            trade_value = price * abs(fill.quantity)
            commission = float(getattr(fill, "commission", 0.0))
            if qty_signed > 0:
                self.cash -= (trade_value + commission)
            else:
                self.cash += (trade_value - commission)

            # Alpha attribution (safe if missing)
            scores = (fill.meta or {}).get("scores", {"GENERIC": 1.0})
            for alpha_name, s in scores.items():
                try:
                    self.alpha_virtual_pos[alpha_name][symbol] += qty_signed * float(s)
                except Exception:
                    pass

            # Mark-to-market
            unreal = sum(q * self.last_prices[s] for s, q in self.positions.items())
            total_equity = self.cash + unreal

            # CSV logs (kept for reports/replication)
            self.log._write_row(
                "portfolio_pnl.csv",
                {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "cash": self.cash,
                    "unrealized": unreal,
                    "total_equity": total_equity,
                    "positions": dict(self.positions),
                },
                ["timestamp_utc", "cash", "unrealized", "total_equity", "positions"]
            )

            alpha_pnl = {
                a: sum(q * self.last_prices.get(sym, 0.0)
                       for sym, q in self.alpha_virtual_pos[a].items())
                for a in self.alpha_virtual_pos
            }
            self.log._write_row(
                "alpha_pnl.csv",
                {"timestamp_utc": datetime.utcnow().isoformat(), **{f"pnl_{a}": alpha_pnl[a] for a in alpha_pnl}},
                ["timestamp_utc"] + [f"pnl_{a}" for a in alpha_pnl]
            )

            # lightweight bus marks (useful for replication tools; no printing)
            try:
                await self.bus.publish("PORTFOLIO_MARK", {
                    "ts": datetime.utcnow().isoformat(),
                    "equity": float(total_equity),
                    "cash": float(self.cash),
                    "unrealized": float(unreal),
                })
                for a, pnl_val in alpha_pnl.items():
                    await self.bus.publish("ALPHA_PNL_TICK", {
                        "alpha": a,
                        "ts": datetime.utcnow().isoformat(),
                        "pnl": float(pnl_val),
                    })
            except Exception:
                # non-fatal if no listeners
                pass

        except Exception as e:
            print("[PORTFOLIO][ERROR] on_fill:", e)
            raise

    # ----------------------------------------------------------------------
    async def _report_state(self):
        """
        Live-only periodic prints. Backtest disables this in start().
        Kept minimal to avoid overhead even in live.
        """
        await asyncio.sleep(5)
        while True:
            try:
                unreal = sum(q * self.last_prices[s] for s, q in self.positions.items())
                total_equity = self.cash + unreal
                # (silenced) print for speed:
                # print(f"[Portfolio] 💼 Equity=${total_equity:.2f} | Cash=${self.cash:.2f}")
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(30)
