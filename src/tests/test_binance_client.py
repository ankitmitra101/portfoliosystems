
import pandas as pd
import matplotlib.pyplot as plt
import os

# Path to your CSV (update if needed)
csv_path = "logs/btc_ticks.csv"

# --- 1️Load data ---
if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
    print(" CSV file not found or empty.")
else:
    df = pd.read_csv(csv_path)

    # Handle potential bad rows (e.g., incomplete writes)
    df = df.dropna(subset=["timestamp", "price"])

    print(f" Loaded {len(df)} rows.")
    print(df.head())

    # --- 2️ Visualize ---
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])  # drop bad timestamps if any
        df = df.sort_values("timestamp")

        plt.figure(figsize=(10, 5))
        plt.plot(df["timestamp"], df["price"], label="Price (USDT)", linewidth=1.2)
        plt.title("BTC/USDT Tick Prices")
        plt.xlabel("Time")
        plt.ylabel("Price (USDT)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

# --- 3️ Optional: clear CSV ---
clear = input("Clear CSV after viewing? (y/n): ").strip().lower()
if clear == "y":
    with open(csv_path, "w") as f:
        f.write("timestamp,price,volume\n")
    print("🧹 CSV cleared.")
else:
    print(" CSV retained.")
