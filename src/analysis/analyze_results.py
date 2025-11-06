# src/analysis/analyze_results.py

import pandas as pd
import quantstats as qs


def load_portfolio_returns():
    df = pd.read_csv("portfolio_pnl.csv", parse_dates=["timestamp"], index_col="timestamp")

    # Convert equity → daily (or per-bar) returns
    returns = df["equity"].pct_change().dropna()

    return returns


def generate_portfolio_report():
    print("\n[REPORT] Generating QuantStats Portfolio Report...")

    returns = load_portfolio_returns()

    qs.reports.html(
        returns,
        benchmark="BTC-USD",   # can change later
        output="portfolio_report.html"
    )

    print("✅ Saved → portfolio_report.html")


def alpha_correlation():
    print("\n[REPORT] Computing Alpha Correlations...")

    df = pd.read_csv("alpha_pnl.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # pivot to: timestamp index, alphas as columns
    pivot = df.pivot(index="timestamp", columns="alpha", values="pnl").fillna(0)

    corr = pivot.corr()
    corr.to_csv("alpha_correlation.csv")

    print("✅ Saved → alpha_correlation.csv")
    print("\n=== ALPHA CORRELATION MATRIX ===\n")
    print(corr)


if __name__ == "__main__":
    generate_portfolio_report()
    alpha_correlation()
