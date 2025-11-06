# src/core/data_handler.py
import os
import pandas as pd
import json
from datetime import datetime
from collections import deque
from typing import Dict, Any
from src.core.event import MarketEvent
from src.core.schemas import Bar
from src.utils.candlestick_aggregator import CandlestickAggregator
class MultiDataHandler:
    """
    Loads CSVs for configured sources and symbols and streams synchronized snapshots.
    - Expects CSV layout: timestamp,open,high,low,close,volume  (timestamp parseable by pd)
    - CSV files located at: data/csv/<source>/<SYMBOL>_<TF>.csv
    """

    def __init__(self, symbols_config: Dict[str, Dict[str, list]], events: deque, data_dir="data/csv", log_path="logs/market_log.ndjson"):
        self.symbols_config = symbols_config
        self.events = events
        self.data_dir = data_dir
        self.aggregator = CandlestickAggregator(timeframes=['1m', '1h'])
        self.series = {}  # source -> key -> DataFrame (index=timestamp)
        self._load_all_series()
        # build master timeline
        all_ts = set()
        for src in self.series:
            for key, df in self.series[src].items():
                all_ts.update(df.index)
        self.timestamps = sorted(all_ts)
        self.index = 0
        self.log_path = log_path
        # empty the log file
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        open(self.log_path, "w").close()

    def _series_filepath(self, source: str, symbol: str, tf: str):
        return os.path.join(self.data_dir, source, f"{symbol}_{tf}.csv")

    def _load_single(self, filepath: str):
        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True).set_index("timestamp")
        # ensure numeric columns
        for c in ["open","high","low","close","volume"]:
            if c not in df.columns:
                df[c] = pd.NA
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].apply(pd.to_numeric, errors="coerce")
        return df

    def _load_all_series(self):
        for source, symmap in self.symbols_config.items():
            self.series[source] = {}
            for symbol, tfs in symmap.items():
                for tf in tfs:
                    fp = self._series_filepath(source, symbol, tf)
                    if not os.path.exists(fp):
                        raise FileNotFoundError(f"Missing CSV: {fp}")
                    key = f"{symbol}_{tf}"
                    self.series[source][key] = self._load_single(fp)

    def get_next_snapshot(self) -> Dict[str, Any]:
        """
        Returns a dict: {"timestamp":..., "source": { "SYM_TF": Bar-like dict } }
        Also appends MarketEvent to events and logs snapshot for replay.
        """
        if self.index >= len(self.timestamps):
            return None
        ts = self.timestamps[self.index]
        snapshot = {"timestamp": ts}
        for source, maps in self.series.items():
            snapshot[source] = {}
            for key, df in maps.items():
                pos = df.index.searchsorted(ts, side="right") - 1
                if pos >= 0:
                    row = df.iloc[pos]
                    snapshot[source][key] = {
                        "open": float(row["open"]) if pd.notna(row["open"]) else None,
                        "high": float(row["high"]) if pd.notna(row["high"]) else None,
                        "low": float(row["low"]) if pd.notna(row["low"]) else None,
                        "close": float(row["close"]) if pd.notna(row["close"]) else None,
                        "volume": float(row["volume"]) if pd.notna(row["volume"]) else None,
                        "ts": df.index[pos].isoformat()
                    }
                else:
                    snapshot[source][key] = None
        # log the snapshot (ndjson)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(snapshot, default=str) + "\n")
        # emit event and advance
        self.events.append(MarketEvent())
        self.index += 1
        return snapshot
