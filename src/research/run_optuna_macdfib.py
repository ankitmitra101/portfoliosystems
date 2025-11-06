# src/research/run_optuna_macdfib.py
import asyncio
import optuna
import numpy as np
from pathlib import Path
from src.backtest.backtest_runner import BacktestRunner
from src.strategy.strategy_macd_fibonacci import MACDFibonacciStrategy

CSV = "src/data/streamer/BTC-USD_1m.csv"
SYMBOL = "BTCUSDT"

def objective(trial):
    # Suggest parameters (search space)
    fast = trial.suggest_int("fast", 8, 20)
    slow = trial.suggest_int("slow", 21, 60)
    signal = trial.suggest_int("signal", 4, 20)
    fib_threshold = trial.suggest_float("fib_threshold", 0.1, 1.5)

    strat = MACDFibonacciStrategy(
        fast=fast,
        slow=slow,
        signal=signal,
        fib_threshold=fib_threshold
    )

    async def run():
        eq = await BacktestRunner(CSV, SYMBOL).run_individual([strat])
        returns = np.log(eq).diff().dropna()
        sharpe = returns.mean() / returns.std() if returns.std() != 0 else 0
        return sharpe

    return asyncio.run(run())


if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30)  # You can increase to 50-100 later

    print("\n🎯 Best MACD-Fibonacci Parameters:")
    print(study.best_params)
    print(f"Sharpe: {study.best_value:.4f}")

    Path("reports").mkdir(exist_ok=True)
    with open("reports/macdfib_best_params.txt", "w") as f:
        f.write(str(study.best_params))
