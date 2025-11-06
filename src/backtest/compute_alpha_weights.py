# src/backtest/compute_alpha_weights.py
from __future__ import annotations
import numpy as np
import pandas as pd

def _safe_cov(ret_df: pd.DataFrame) -> pd.DataFrame:
    ret_df = ret_df.fillna(0.0)
    return ret_df.cov()

def _clip_and_norm(w: np.ndarray) -> np.ndarray:
    w = np.maximum(w, 0.0)
    s = w.sum()
    return w / s if s > 0 else np.ones_like(w) / len(w)

def equal_weight(names: list[str]) -> dict[str, float]:
    n = len(names)
    w = {k: 1.0 / n for k in names}
    return w

def inverse_vol(ret_df: pd.DataFrame) -> dict[str, float]:
    # annualized vol (assuming 1m bars → scale to daily ~sqrt(1440); but we only need relative vols)
    vol = ret_df.std().replace(0.0, np.nan)
    inv = 1.0 / vol
    inv = inv.replace([np.inf, -np.inf, np.nan], 0.0)
    w = inv / inv.sum() if inv.sum() > 0 else pd.Series(1.0, index=ret_df.columns) / len(ret_df.columns)
    return w.to_dict()

def min_variance(ret_df: pd.DataFrame) -> dict[str, float]:
    # w ∝ Σ^{-1} 1, then clip negatives and renorm
    cov = _safe_cov(ret_df)
    names = cov.columns.tolist()
    ones = np.ones(len(names))
    try:
        inv = np.linalg.pinv(cov.values)  # robust pseudo-inverse
    except Exception:
        inv = np.eye(len(names))
    raw = inv @ ones
    w = _clip_and_norm(raw)
    return dict(zip(names, w))

def max_sharpe(ret_df: pd.DataFrame, rf: float = 0.0) -> dict[str, float]:
    # w ∝ Σ^{-1} (μ - rf), then clip negatives and renorm
    cov = _safe_cov(ret_df)
    mu = ret_df.mean().values
    mu = mu - rf
    names = cov.columns.tolist()
    try:
        inv = np.linalg.pinv(cov.values)
    except Exception:
        inv = np.eye(len(names))
    raw = inv @ mu
    w = _clip_and_norm(raw)
    return dict(zip(names, w))
