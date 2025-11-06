# src/backtest/run_all_backtests.py
import asyncio
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from src.backtest.backtest_runner import BacktestRunner
from src.strategy.strategy_macd_fibonacci import MACDFibonacciStrategy
from src.strategy.strategy_mean_reversion import MeanReversionStrategy
from src.strategy.strategy_momentum import MomentumStrategy
from src.strategy.strategy_atr_gaussian import ATRGaussianStrategy
from src.strategy.strategy_generic_alpha import GenericAlphaStrategy
from src.backtest.compute_alpha_weights import equal_weight, inverse_vol, min_variance, max_sharpe


def to_returns(equity: pd.Series, log: bool = False) -> pd.Series:
    if equity is None or equity.empty:
        return pd.Series(dtype=float, name="returns")
    equity = equity.sort_index()
    if log:
        r = np.log(equity).diff().fillna(0.0)
    else:
        r = equity.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    r.name = "returns"
    return r


async def main():
    # === CONFIG (single-asset for now) ===
    CSV = "src/data/streamer/BTC-USD_1m.csv"   # columns: timestamp, close, [volume]
    SYMBOL = "BTCUSDT"
    OUT = Path("reports")
    OUT.mkdir(exist_ok=True)

    # --- Backtest: Individual alphas ---
    alpha_specs: Dict[str, object] = {
        "MACDFIB": MACDFibonacciStrategy(),
        "MEANREV": MeanReversionStrategy(),
        "MOMENTUM": MomentumStrategy(),
        "ATRGauss": ATRGaussianStrategy(),
        "GENERIC": GenericAlphaStrategy(),
    }

    alpha_returns: Dict[str, pd.Series] = {}
    for name, strat in alpha_specs.items():
        eq = await BacktestRunner(CSV, SYMBOL).run_individual([strat])
        eq.to_csv(OUT / f"{name}_equity.csv")
        alpha_returns[name] = to_returns(eq)

    # Persist per-alpha return table + correlation
    if not alpha_returns:
        print("[WARN] No alpha returns computed.")
        return

    ret_df = pd.concat(alpha_returns.values(), axis=1)
    ret_df.columns = list(alpha_returns.keys())
    ret_df.to_csv(OUT / "alpha_returns.csv")

    corr = ret_df.corr()
    corr.to_csv(OUT / "alpha_returns_correlation.csv")
    print("[Alpha Return Correlations]\n", corr)

    # --- Compute weights (choose a scheme here) ---
    # Option 1: Equal weight
    w_eq = equal_weight(ret_df.columns.tolist())

    # Option 2: Inverse vol (often a good baseline)
    w_iv = inverse_vol(ret_df)

    # Option 3: Minimum-variance
    w_mv = min_variance(ret_df)

    # Option 4: Max-Sharpe (using sample mean; simple baseline)
    w_ms = max_sharpe(ret_df)

    # Save all weight sets
    weights_table = pd.DataFrame([w_eq, w_iv, w_mv, w_ms],
                                 index=["equal_weight", "inverse_vol", "min_variance", "max_sharpe"]).T
    weights_table.to_csv(OUT / "alpha_weights_candidates.csv")
    print("\n[Alpha Weights Candidates]\n", weights_table)

    # ---- Pick one scheme to use now ----
    chosen_weights = w_iv   # <—— change to w_mv or w_ms if you prefer
    print("\n[Chosen Weights]\n", chosen_weights)

    # --- Backtest: Combined portfolio with chosen weights ---
    combined_runner = BacktestRunner(CSV, SYMBOL)
    port_eq = await combined_runner.run_combined_via_manager(alpha_weights=chosen_weights)
    port_eq.to_csv(OUT / "portfolio_equity.csv")

    # Performance report
    try:
        import quantstats as qs  # type: ignore
        qs.reports.html(to_returns(port_eq), output=str(OUT / "portfolio_quantstats.html"))
    except Exception as e:
        print(f"[WARN] QuantStats report not generated: {e}")


if __name__ == "__main__":
    asyncio.run(main())
