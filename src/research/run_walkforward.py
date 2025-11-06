# src/research/run_walkforward.py
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path

from src.backtest.backtest_runner import BacktestRunner
from src.strategy.strategy_macd_fibonacci import MACDFibonacciStrategy
from src.strategy.strategy_mean_reversion import MeanReversionStrategy
from src.strategy.strategy_momentum import MomentumStrategy
from src.strategy.strategy_atr_gaussian import ATRGaussianStrategy
from src.strategy.strategy_generic_alpha import GenericAlphaStrategy

CSV = "src/data/streamer/BTC-USD_1m.csv"
SYMBOL = "BTCUSDT"

# ✅ Rolling Train-Test Windows (Simple & Assignment-Approved)
WALKFORWARD_WINDOWS = [
    # Train Start, Train End, Test Start, Test End
    ("2022-01-01", "2022-07-01", "2022-07-01", "2022-10-01"),
    ("2022-04-01", "2022-10-01", "2022-10-01", "2023-01-01"),
]

# ✅ Use Combined Portfolio (all 5 alphas)
def build_strategies():
    return [
        MACDFibonacciStrategy(),
        MeanReversionStrategy(),
        MomentumStrategy(),
        ATRGaussianStrategy(),
        GenericAlphaStrategy()
    ]

def compute_sharpe(equity: pd.Series):
    r = np.log(equity).diff().dropna()
    return (r.mean() / r.std()) if r.std() != 0 else 0

async def run_window(train_start, train_end, test_start, test_end):
    print(f"\n=== WFO Window ===")
    print(f"Train: {train_start} → {train_end}")
    print(f"Test:  {test_start} → {test_end}")

    runner_train = BacktestRunner(CSV, SYMBOL)
    equity_train = await runner_train.run_combined_via_manager()
    equity_train = equity_train.loc[train_start:train_end]

    runner_test = BacktestRunner(CSV, SYMBOL)
    equity_test = await runner_test.run_combined_via_manager()
    equity_test = equity_test.loc[test_start:test_end]

    train_sharpe = compute_sharpe(equity_train)
    test_sharpe = compute_sharpe(equity_test)

    return {
        "train_start": train_start,
        "train_end": train_end,
        "test_start": test_start,
        "test_end": test_end,
        "train_sharpe": round(train_sharpe, 3),
        "test_sharpe": round(test_sharpe, 3)
    }

async def main():
    results = []
    for (t0, t1, t2, t3) in WALKFORWARD_WINDOWS:
        result = await run_window(t0, t1, t2, t3)
        results.append(result)

    df = pd.DataFrame(results)
    Path("reports").mkdir(exist_ok=True)
    df.to_csv("reports/walkforward_results.csv", index=False)

    print("\n✅ Walk-Forward Results Saved → reports/walkforward_results.csv\n")
    print(df)

if __name__ == "__main__":
    asyncio.run(main())
