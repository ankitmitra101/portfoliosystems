# PortfolioSystem
# PortfolioSystem

A modular backtesting and live-trading system integrating multiple data sources (Binance, Zerodha, IBKR).

## 📂 Project Structure
- **config/** → API keys, symbol lists, and settings  
- **data/** → market data storage (CSV, JSON)  
- **logs/** → runtime logs  
- **src/core/** → main trading logic and data client interfaces  
- **src/utils/** → config loader and logger  
- **run_backtest.py** → run backtests on historical data  
- **run_live.py** → live trading entry point  

## ⚙️ Supported Exchanges
- Binance (Crypto)
- Zerodha (Indian Equities)
- Interactive Brokers (Global Equities & FX)

## 🚀 Vision
Designed for **scalability** — currently handles 7 symbols across 3 exchanges,  
but built so new exchanges and symbols can be added with a few config lines.

## 🧱 Future Extensions
- Add more brokers via `BaseDataClient` subclassing  
- Integrate real-time streaming  
- Add portfolio optimization, risk metrics, and execution simulation  

---

💡 *Author: Ankit Mitra*  
*Version 1.0 — Scalable Portfolio System Prototype*





























