import csv
import os
from datetime import datetime
import json

class LogWriter:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    # ----------------------------------------------------------------------
    # Core CSV writer
    # ----------------------------------------------------------------------
    def _write_row(self, filename, row, header):
        file_path = os.path.join(self.log_dir, filename)
        file_exists = os.path.exists(file_path)
        with open(file_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    # ----------------------------------------------------------------------
    # Existing Logging Functions
    # ----------------------------------------------------------------------
    def log_tick(self, source, symbol, price, volume, exchange, raw_json):
        self._write_row(
            f"{source}_{symbol}_ticks.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "price": price,
                "volume": volume,
                "exchange": exchange,
                "raw_json": json.dumps(raw_json),
            },
            ["timestamp_utc", "price", "volume", "exchange", "raw_json"]
        )

    def log_candle(self, source, symbol, o, h, l, c, v, exchange, tf, raw_json):
        self._write_row(
            f"{source}_{symbol}_candles.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "open": o, "high": h, "low": l, "close": c,
                "volume": v, "exchange": exchange, "tf": tf,
                "raw_json": json.dumps(raw_json)
            },
            ["timestamp_utc", "open", "high", "low", "close", "volume",
             "exchange", "tf", "raw_json"]
        )

    def log_order(self, order_id, alpha, side, qty, price, status, exchange, raw_json):
        self._write_row(
            "orders.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "order_id": order_id, "alpha": alpha, "side": side,
                "qty": qty, "price": price, "status": status,
                "exchange": exchange, "raw_json": json.dumps(raw_json)
            },
            ["timestamp_utc", "order_id", "alpha", "side", "qty",
             "price", "status", "exchange", "raw_json"]
        )

    def log_fill(self, fill_id, order_id, alpha, symbol, qty, price, commission, exchange, raw_json):
        self._write_row(
            "fills.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "fill_id": fill_id, "order_id": order_id, "alpha": alpha,
                "symbol": symbol, "qty": qty, "price": price,
                "commission": commission, "exchange": exchange,
                "raw_json": json.dumps(raw_json)
            },
            ["timestamp_utc", "fill_id", "order_id", "alpha", "symbol",
             "qty", "price", "commission", "exchange", "raw_json"]
        )

    # ----------------------------------------------------------------------
    # 🆕 New Additions
    # ----------------------------------------------------------------------
    def log_signal(self, symbol, strategy, direction, price, meta):
        """
        Logs strategy-generated trading signals to signals.csv
        """
        self._write_row(
            "signals.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "strategy": strategy,
                "direction": direction,
                "price": price,
                "meta": json.dumps(meta or {})
            },
            ["timestamp_utc", "symbol", "strategy", "direction", "price", "meta"]
        )

    def log_event(self, topic, payload):
        """
        Unified system event log for replication/replay testing.
        Logs everything (MARKET_SNAPSHOT, SIGNAL, ORDER, FILL).
        """
        self._write_row(
            "events.csv",
            {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "topic": topic,
                "payload": json.dumps(payload)
            },
            ["timestamp_utc", "topic", "payload"]
        )
