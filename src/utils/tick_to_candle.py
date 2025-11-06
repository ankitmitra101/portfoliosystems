# src/utils/tick_to_candle.py
import pandas as pd
from datetime import datetime
from src.utils.candlestick_aggregator import CandlestickAggregator
from pathlib import Path
import time

tick_path = Path("logs/btc_ticks.csv")
candle_path = Path("logs/btc_candles.csv")
aggregator = CandlestickAggregator(["1m"])

def aggregate_ticks_to_candles():
    if not tick_path.exists():
        print("❌ No tick file found.")
        return

    # Initialize CSV if not present
    if not candle_path.exists():
        with open(candle_path, "w") as f:
            f.write("symbol,start,open,high,low,close,volume\n")

    print("📊 Aggregating ticks into candles...")
    df = pd.read_csv(tick_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    completed = []
    for _, row in df.iterrows():
        bars = aggregator.update(
            "BTCUSDT", float(row["price"]), float(row["volume"]), row["timestamp"]
        )
        completed.extend(bars)

    for bar in completed:
        with open(candle_path, "a") as f:
            f.write(
                f"BTCUSDT,{bar['start']},{bar['open']},{bar['high']},{bar['low']},{bar['close']},{bar['volume']}\n"
            )

    print(f"✅ Aggregated {len(completed)} candles into {candle_path}")

if __name__ == "__main__":
    while True:
        aggregate_ticks_to_candles()
        time.sleep(60)  # update every minute
