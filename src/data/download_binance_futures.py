import ccxt
import pandas as pd
import time
from datetime import datetime
from pathlib import Path


def download(symbol, out_path, start="2022-01-01T00:00:00Z", end="2023-01-01T00:00:00Z"):

    # ✅ Use Binance USDT-M Futures API (reliable even when Binance main is blocked)
    ex = ccxt.binanceusdm({
        "enableRateLimit": True,
        "timeout": 20000,
    })

    # Retry load_markets due to possible DNS/SSL slow response
    for attempt in range(5):
        try:
            ex.load_markets()
            break
        except Exception as e:
            print(f"[WARN] load_markets failed (attempt {attempt+1}/5): {e}")
            time.sleep(2)
    else:
        raise RuntimeError("❌ Could not load markets. Network/VPN/Firewall issue persists.")

    timeframe = "1m"
    since = ex.parse8601(start)
    end_ts = ex.parse8601(end)

    all_candles = []

    print(f"\n[Fetching] {symbol} {timeframe} from {start} → {end}\n")

    while since < end_ts:
        try:
            candles = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1500)
        except Exception as e:
            print(f"[WARN] retry fetch_ohlcv due to: {e}")
            time.sleep(2)
            continue

        if not candles:
            break

        all_candles.extend(candles)
        since = candles[-1][0] + 60_000
        print("→ Up to:", datetime.utcfromtimestamp(since / 1000))
        time.sleep(0.25)

    df = pd.DataFrame(all_candles, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df[["timestamp", "close", "volume"]]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\n✅ Saved: {out_path}\n")


if __name__ == "__main__":
    Path("src/data/streamer").mkdir(parents=True, exist_ok=True)

    download("BTCUSDT", "src/data/streamer/BTC-USD_1m.csv",
         start="2022-01-01T00:00:00Z", end="2023-01-01T00:00:00Z")

    download("ETHUSDT", "src/data/streamer/ETH-USD_1m.csv",
         start="2022-01-01T00:00:00Z", end="2023-01-01T00:00:00Z")
