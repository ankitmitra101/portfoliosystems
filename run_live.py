# main.py
from src.core.engine import Engine

if __name__ == "__main__":
    engine = Engine()
    engine.run_live()   # or engine.run_backtest()
