# test_multi_clients.py
import asyncio
from datetime import datetime
from data.binance_data_client import BinanceDataClient
from data.zerodha_data_client import ZerodhaDataClient
from data.ibkr_data_client import IBKRDataClient
from collections import defaultdict

# symbol sets (2,3,2)
binance_syms = ["BTCUSDT", "ETHUSDT"]
zerodha_syms = ["RELIANCE", "INFY", "TCS"]
ibkr_syms = ["AAPL", "USDINR"]
tfs = ["1m"]

combined = defaultdict(dict)  # combined[source][symbol_tf] = data

def central_printer(snapshot):
    # snapshot is a MarketSnapshot object with .payload
    ts = snapshot.timestamp.isoformat()
    src = list(snapshot.payload.keys())[0]  # "binance" or "zerodha" or "ibkr"
    data = snapshot.payload[src]
    # write into combined
    combined[src].update(data)
    # build quick readout: pick closes for each symbol if present
    b_close = combined["binance"].get("BTCUSDT_1m", {}).get("close")
    e_close = combined["binance"].get("ETHUSDT_1m", {}).get("close")
    r_close = combined["zerodha"].get("RELIANCE_1m", {}).get("close")
    i_close = combined["zerodha"].get("INFY_1m", {}).get("close")
    t_close = combined["zerodha"].get("TCS_1m", {}).get("close")
    a_close = combined["ibkr"].get("AAPL_1m", {}).get("close")
    u_close = combined["ibkr"].get("USDINR_1m", {}).get("close")
    print(f"{ts} | BTC={b_close} ETH={e_close} REL={r_close} INFY={i_close} TCS={t_close} AAPL={a_close} USDINR={u_close}")

async def main():
    # create clients
    b = BinanceDataClient(symbols=binance_syms, timeframes=tfs)
    z = ZerodhaDataClient(symbols=zerodha_syms, timeframes=tfs)
    i = IBKRDataClient(symbols=ibkr_syms, timeframes=tfs)

    # register the central callback for all
    b.register_callback(central_printer)
    z.register_callback(central_printer)
    i.register_callback(central_printer)

    # connect all
    await asyncio.gather(b.connect(), z.connect(), i.connect())

    # subscribe (start streaming)
    await asyncio.gather(b.subscribe(), z.subscribe(), i.subscribe())

    # run for 8 seconds
    await asyncio.sleep(8)

    # stop all
    await asyncio.gather(b.stop(), z.stop(), i.stop())

if __name__ == "__main__":
    asyncio.run(main())
