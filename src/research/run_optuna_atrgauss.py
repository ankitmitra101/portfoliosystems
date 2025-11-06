# src/research/run_optuna_atrgauss.py
import asyncio
import optuna
import numpy as np
from pathlib import Path
from src.backtest.backtest_runner import BacktestRunner
from src.strategy.strategy_atr_gaussian import ATRGaussianStrategy

CSV = "src/data/streamer/BTC-USD_1m.csv"
SYMBOL = "BTCUSDT"

def objective(trial):
    atr_length = trial.suggest_int("atr_length", 10, 40)
    band_width = trial.suggest_float("band_width", 1.0, 4.0)

    strat = ATRGaussianStrategy(
        atr_length=atr_length,
        band_width=band_width
    )

    async def run():
        eq = await BacktestRunner(CSV, SYMBOL).run_individual([strat])
        returns = np.log(eq).diff().dropna()
        sharpe = returns.mean() / returns.std() if returns.std() != 0 else 0
        return sharpe

    return asyncio.run(run())


if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30)

    print("\n🎯 Best ATR Gaussian Parameters:")
    print(study.best_params)
    print(f"Sharpe: {study.best_value:.4f}")

    Path("reports").mkdir(exist_ok=True)
    with open("reports/atrgauss_best_params.txt", "w") as f:
        f.write(str(study.best_params))
