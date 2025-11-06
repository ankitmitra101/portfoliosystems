# src/utils/config_loader.py
import json
import yaml
import os

def load_config(path="config/settings.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_symbols_for_source(source: str, config_dir="config"):
    path_map = {
        "binance": os.path.join(config_dir, "binance_symbols.json"),
        "zerodha": os.path.join(config_dir, "zerodha_symbols.json"),
        "ibkr": os.path.join(config_dir, "ibkr_symbols.json"),
    }
    path = path_map.get(source)
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)
