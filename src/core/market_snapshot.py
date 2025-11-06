from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class MarketSnapshot:
    """
    A synchronized snapshot across multiple symbols/timeframes.
    Example: {'timestamp':..., 'binance': {...}, 'zerodha': {...}}
    """
    timestamp: datetime
    payload: Dict[str, Any]   # adapter/source -> symbol_tf -> data (Bar/Tick dicts)
    meta: Optional[Dict[str, Any]] = None
