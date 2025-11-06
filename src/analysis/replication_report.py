# src/analysis/replication_report.py
import os
import csv
import json
from collections import defaultdict

def read_fills(file_path):
    """
    Reads fills.csv and aggregates per-alpha trade data.
    Returns:
        alpha_data = {
            'alpha_name': {
                'trades': int,
                'pnl': float
            }
        }
    """
    alpha_data = defaultdict(lambda: {"trades": 0, "pnl": 0.0})
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing fills.csv: {file_path}")

    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alpha = row.get("alpha", "unknown")
            side = row.get("side") or row.get("direction", "").upper()
            qty = float(row.get("qty") or row.get("quantity", 0))
            price = float(row.get("price") or row.get("fill_price", 0))
            commission = float(row.get("commission", 0))

            # Simplified PnL: BUY → -cost, SELL → +proceeds
            pnl = (-price * qty - commission) if side == "BUY" else (price * qty - commission)
            alpha_data[alpha]["pnl"] += pnl
            alpha_data[alpha]["trades"] += 1

    return alpha_data


def compute_total_pnl(alpha_data):
    """Aggregate total portfolio PnL from all alphas."""
    return sum(a["pnl"] for a in alpha_data.values())


def compare_fills(sandbox_fills, replay_fills):
    """
    Compare sandbox and replay P&L and trades.
    Returns a results dictionary ready to be written to JSON.
    """
    results = {
        "portfolio_pnl": {},
        "alphas": {}
    }

    # Portfolio-level comparison
    sandbox_total = compute_total_pnl(sandbox_fills)
    replay_total = compute_total_pnl(replay_fills)
    pnl_match = abs(sandbox_total - replay_total) < 1e-6

    results["portfolio_pnl"] = {
        "sandbox_pnl": round(sandbox_total, 4),
        "backtest_pnl": round(replay_total, 4),
        "pnl_match": "PASS" if pnl_match else "FAIL"
    }

    # Per-alpha comparison
    all_alphas = set(sandbox_fills.keys()) | set(replay_fills.keys())
    for alpha in all_alphas:
        s_data = sandbox_fills.get(alpha, {"trades": 0, "pnl": 0.0})
        r_data = replay_fills.get(alpha, {"trades": 0, "pnl": 0.0})
        match = abs(s_data["pnl"] - r_data["pnl"]) < 1e-6 and s_data["trades"] == r_data["trades"]
        results["alphas"][alpha] = {
            "sandbox_trades": s_data["trades"],
            "replay_trades": r_data["trades"],
            "sandbox_pnl": round(s_data["pnl"], 4),
            "replay_pnl": round(r_data["pnl"], 4),
            "match": "PASS" if match else "FAIL",
            "analysis": "" if match else f"Mismatch in trades or pnl ({s_data['pnl']:.2f} vs {r_data['pnl']:.2f})"
        }

    return results


def generate_replication_report(sandbox_dir="logs/sandbox", replay_dir="logs/replay", output_path="results.json"):
    """
    Main entry point — generate replication test report.
    """
    sandbox_fills = read_fills(os.path.join(sandbox_dir, "fills.csv"))
    replay_fills = read_fills(os.path.join(replay_dir, "fills.csv"))
    results = compare_fills(sandbox_fills, replay_fills)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[REPORT] ✅ Replication report saved to {output_path}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    # Example: Compare fills from /logs/sandbox and /logs/replay
    generate_replication_report(
        sandbox_dir="logs/sandbox",
        replay_dir="logs/replay",
        output_path="results.json"
    )
