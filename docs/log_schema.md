# Log Schema Specification

All system components (live, backtest, replay) must write data to the same canonical CSV/JSON schemas.

---

## 1. Tick Logs

**File:** `logs/<source>_<symbol>_ticks.csv`

| Field | Type | Description |
|--------|------|-------------|
| `timestamp_utc` | ISO8601 / float | UTC timestamp of tick |
| `price` | float | Trade price |
| `volume` | float | Trade volume |
| `exchange` | str | Exchange/source (e.g. BINANCE, IBKR) |
| `raw_json` | str | Original data payload (stringified JSON) |

---

## 2. Candle (Bar) Logs

**File:** `logs/<source>_<symbol>_candles.csv`

| Field | Type | Description |
|--------|------|-------------|
| `timestamp_utc` | ISO8601 / float | UTC start time of bar |
| `open` | float | Open price |
| `high` | float | High price |
| `low` | float | Low price |
| `close` | float | Close price |
| `volume` | float | Volume traded in bar |
| `exchange` | str | Exchange/source |
| `tf` | str | Timeframe (e.g. 1m, 5m, 1h) |
| `raw_json` | str | Original candle data payload |

---

## 3. Order Logs

**File:** `logs/orders.csv`

| Field | Type | Description |
|--------|------|-------------|
| `timestamp_utc` | ISO8601 | UTC time of order event |
| `order_id` | str | System or broker order ID |
| `alpha` | str | Strategy / signal name |
| `side` | str | "BUY" / "SELL" |
| `qty` | float | Quantity |
| `price` | float | Limit price or market execution price |
| `status` | str | e.g. NEW, FILLED, CANCELED |
| `exchange` | str | Exchange name |
| `raw_json` | str | Original broker/order payload |

---

## 4. Fill Logs

**File:** `logs/fills.csv`

| Field | Type | Description |
|--------|------|-------------|
| `timestamp_utc` | ISO8601 | UTC time of fill |
| `fill_id` | str | Fill ID |
| `order_id` | str | Related order ID |
| `alpha` | str | Strategy / signal name |
| `symbol` | str | Symbol traded |
| `qty` | float | Quantity filled |
| `price` | float | Execution price |
| `commission` | float | Commission / fee paid |
| `exchange` | str | Exchange name |
| `raw_json` | str | Original fill payload |

---

### Notes

- Every adapter must **write in append mode**.
- `raw_json` allows exact replay of raw exchange/broker data.
- All timestamps must be in **UTC**.

