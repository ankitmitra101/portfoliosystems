# src/backtest/historical_replayer.py
import pandas as pd
from src.core.schemas import SimpleSnapshot


class HistoricalReplayer:
    """
    Replay historical candles directly into your event bus.
    Each row becomes a MARKET_SNAPSHOT event.
    Expected CSV columns: timestamp, close, (optional) volume
    """

    def __init__(self, event_bus, csv_path: str, symbol: str):
        self.bus = event_bus
        self.symbol = symbol.upper()

        df = pd.read_csv(csv_path)
        # Normalize and sort timestamps in UTC
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Minimal column validation
        if "close" not in df.columns:
            raise ValueError("CSV must contain a 'close' column.")
        if "timestamp" not in df.columns:
            raise ValueError("CSV must contain a 'timestamp' column.")

        self.df = df

    async def run(self):
        for row in self.df.itertuples(index=False):
            ts = row.timestamp.to_pydatetime()
            close = float(row.close)
            volume = float(getattr(row, "volume", 0.0))

            snap = SimpleSnapshot(
                timestamp=ts,
                symbol=self.symbol,
                bid=close,
                ask=close,
                last=close,
                volume=volume,
                meta={"source": "backtest"},
            )

            await self.bus.publish("MARKET_SNAPSHOT", snap)
