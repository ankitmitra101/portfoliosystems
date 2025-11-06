# src/utils/live_plot.py
import pandas as pd
import mplfinance as mpf
from pathlib import Path

class LivePlot:
    def __init__(self, path="logs/btc_candles.csv"):
        self.candle_path = Path(path)

    def show(self):
        """Reads candle CSV and plots the latest 100 candles."""
        if not self.candle_path.exists() or self.candle_path.stat().st_size == 0:
            print("❌ No candle data found.")
            return
        
        df = pd.read_csv(
            self.candle_path,
            header=None,
            names=["start", "open", "high", "low", "close", "volume"]
        )

        # Parse timestamp
        df["start"] = pd.to_datetime(df["start"], errors="coerce")
        df.dropna(subset=["start"], inplace=True)

        # Rename columns for mplfinance
        df.rename(columns={
            "start": "Date", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume"
        }, inplace=True)
        df.set_index("Date", inplace=True)

        # Plot last 100 candles
        mpf.plot(
            df.tail(100),
            type="candle",
            style="charles",
            volume=True,
            title="BTCUSDT - 1m Candles"
        )
