import websocket, json

def on_message(ws, message):
    print("Message:", message)

def on_open(ws):
    ws.send(json.dumps({
        "method": "SUBSCRIBE",
        "params": ["btcusdt@trade"],
        "id": 1
    }))

ws = websocket.WebSocketApp(
    "wss://stream.binance.com:9443/ws",
    on_message=on_message,
    on_open=on_open
)
ws.run_forever()
