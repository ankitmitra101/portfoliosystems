class Event:
    """Base class for all events."""
    pass


class MarketEvent(Event):
    """Handles the event of receiving new market data."""
    def __init__(self):
        self.type = 'MARKET'


class SignalEvent(Event):
    """Handles the event of sending a trading signal from a strategy."""
    def __init__(self, symbol, datetime, signal_type, strength):
        self.type = 'SIGNAL'
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type  # 'BUY' or 'SELL'
        self.strength = strength


class OrderEvent(Event):
    """Handles the event of sending an order to the broker."""
    def __init__(self, symbol, order_type, quantity, direction):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type  # 'MKT' or 'LMT'
        self.quantity = quantity
        self.direction = direction    # 'BUY' or 'SELL'

    def __str__(self):
        return f"Order: Symbol={self.symbol}, Type={self.order_type}, Qty={self.quantity}, Dir={self.direction}"


class FillEvent(Event):
    """Handles the event of an order being filled by the broker."""
    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost, commission=None):
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        self.commission = commission if commission is not None else self.calculate_commission()

    def calculate_commission(self):
        # Basic example: fixed 1 USD per trade
        return 1.0
