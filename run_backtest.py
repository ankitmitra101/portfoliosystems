import asyncio
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from src.core.event_bus import EventBus
from src.utils.candlestick_aggregator import CandlestickAggregator
from src.strategy.multi_strategy_manager import MultiStrategyManager
from src.portfolio.portfolio_handler import PortfolioHandler
from src.execution.order_execution_handler import OrderExecutionHandler

DATA_DIR = "src/data/streamer"
os.makedirs(DATA_DIR, exist_ok=True)


def _load_cached(symbol: str, tf: str) -> pd.DataFrame | None:
    path = f"{DATA_DIR}/{symbol}_{tf}.csv"
    if not os.path.exists(path):
        return None
    print(f"[DATA] Loading cached → {path}")
    df = pd.read_csv(path)

    # Remove any stray index columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    # Ensure expected columns exist
    expected = {"t_ms", "Close", "Volume"}
    if not expected.issubset(set(df.columns)):
        print(f"[DATA] ⚠️ Cached file missing columns {expected - set(df.columns)} → refetching.")
        return None

    # Coerce types and drop bad rows
    df["t_ms"] = pd.to_numeric(df["t_ms"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    df = df.dropna(subset=["t_ms", "Close", "Volume"]).reset_index(drop=True)
    df["t_ms"] = df["t_ms"].astype("int64")
    return df


def _fetch_and_cache(symbol: str, tf: str) -> pd.DataFrame:
    print(f"[DATA] Fetching {symbol} ({tf}) from yfinance...")
    df = yf.download(symbol, interval=tf, period="7d")  # 1m granularity allows ~7-8 days
    if df is None or len(df) == 0:
        raise RuntimeError(f"yfinance returned no data for {symbol} @ {tf}")

    # Make sure time is a column (yfinance gives Datetime index for intraday)
    df = df.reset_index().copy()

    # The time column for intraday is usually 'Datetime'; fall back defensively
    time_col = None
    for cand in ("Datetime", "Date", "Time", df.columns[0]):
        if cand in df.columns:
            time_col = cand
            break
    if time_col is None:
        raise RuntimeError("Could not identify timestamp column in yfinance dataframe.")

    # Convert timestamp → epoch ms (works with tz-aware datetimes too)
    # .view('int64') works if dtype is datetime64[ns]; for safety, use astype('int64') try/except
    if pd.api.types.is_datetime64_any_dtype(df[time_col]):
        t_ns = df[time_col].view("int64")
    else:
        # force convert to datetime first
        t_ns = pd.to_datetime(df[time_col], utc=True, errors="coerce").view("int64")

    out = pd.DataFrame({
        "t_ms": (t_ns // 1_000_000).astype("int64"),
        "Close": pd.to_numeric(df["Close"], errors="coerce"),
        "Volume": pd.to_numeric(df["Volume"], errors="coerce"),
    }).dropna(subset=["t_ms", "Close", "Volume"]).reset_index(drop=True)

    path = f"{DATA_DIR}/{symbol}_{tf}.csv"
    out.to_csv(path, index=False)
    print(f"[DATA] ✅ Cached → {path}")
    return out


def get_data(symbol: str, tf: str = "1m") -> pd.DataFrame:
    cached = _load_cached(symbol, tf)
    if cached is not None:
        return cached
    return _fetch_and_cache(symbol, tf)


async def replay_as_ticks(bus: EventBus, df: pd.DataFrame, symbol: str):
    symbol = symbol.upper()

    # Use itertuples to guarantee scalars (no Series weirdness)
    for t_ms, close, vol in df[["t_ms", "Close", "Volume"]].itertuples(index=False, name=None):
        # Guard against non-numeric rows
        try:
            t_ms = int(t_ms)
            price = float(close)
            volume = float(vol)
        except Exception:
            continue

        ts = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)

        tick = {
            "timestamp": ts.isoformat().replace("+00:00", "Z"),
            "source": "YF_BACKTEST",
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "bid": None,
            "ask": None,
            "meta": {"replay": True},
        }

        await bus.publish("RAW_MARKET", tick)
        await asyncio.sleep(0)


async def main():
    # Event bus
    bus = EventBus()

    # Same pipeline as live
    aggregator = CandlestickAggregator(bus, timeframes=("1m", "5m", "1h"))
    bus.subscribe("RAW_MARKET", aggregator.on_tick)

    strategy_manager = MultiStrategyManager(bus)
    portfolio = PortfolioHandler(event_bus=bus, initial_cash=100000)
    execution = OrderExecutionHandler(mode="paper", event_bus=bus)

    await portfolio.start()

    print("\n[BACKTEST] 🔁 Replaying historical data from yfinance...\n")

    # Symbols in yfinance format; your strategies handle symbol routing
    markets = ["BTC-USD", "ETH-USD"]

    for sym in markets:
        df = get_data(sym, "1m")
        print(f"[BACKTEST] Replaying {len(df)} bars for {sym}")
        await replay_as_ticks(bus, df, sym)

    print("\n[BACKTEST] ✅ DONE.\nCheck:")
    print("  • logs/portfolio_pnl.csv")
    print("  • logs/alpha_pnl.csv\n")


if __name__ == "__main__":
    asyncio.run(main())
