# src/core/base_data_client.py
from abc import ABC, abstractmethod
from typing import List, Callable, Dict, Any
from src.core.schemas import MarketSnapshot
import logging

class BaseDataClient(ABC):
    """
    Abstract interface for data clients (Binance, Zerodha, IBKR).
    Concrete subclasses must implement connect/subscribe/stop.
    """

    def __init__(self, name: str, symbols: List[str], timeframes: List[str]):
        self.name = name
        self.symbols = symbols
        self.logger = logging.getLogger(self.name)
        self.timeframes = timeframes
        self._callback: Callable[[MarketSnapshot], None] = None
        self.running = False

    def register_callback(self, cb: Callable[[MarketSnapshot], None]):
        """Register function to call with MarketSnapshot"""
        self._callback = cb

    def _emit(self, payload: Dict[str, Any]):
        """Wrap a payload and call callback (MarketSnapshot built by handler usually)."""
        if self._callback:
            self._callback(payload)

    @abstractmethod
    def connect(self):
        """Establish connection / prepare client (sync or async)."""
        raise NotImplementedError

    @abstractmethod
    def subscribe(self):
        """Start streaming (or producing) data."""
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """Stop streaming / cleanup."""
        raise NotImplementedError
    def is_connected(self) -> bool:
        return self.running
    def close(self):
        """Alias for stop(), for external orchestrators."""
        if self.running:
            self.stop()
            self.logger.info(f"{self.name} stopped gracefully.")