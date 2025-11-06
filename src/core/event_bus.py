# src/core/event_bus.py
import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    """
    A simple event bus supporting both synchronous and asynchronous subscribers.
    Async callbacks are AWAITED (no fire-and-forget), so errors propagate.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe a function or coroutine to a topic."""
        self._subscribers[topic].append(callback)
        name = getattr(callback, "__name__", str(callback))
        self.logger.debug(f"Subscribed {name} to topic '{topic}'")

    async def publish(self, topic: str, data: Any):
        """
        Publish data to a topic.
        All async subscribers are awaited (gathered) so exceptions surface.
        """
        callbacks = self._subscribers.get(topic, [])
        if not callbacks:
            self.logger.debug(f"No subscribers for topic '{topic}'")
            return

        self.logger.debug(f"Publishing to '{topic}' with {len(callbacks)} subscriber(s)")

        tasks = []
        async with self._lock:
            for cb in callbacks:
                try:
                    if inspect.iscoroutinefunction(cb):
                        tasks.append(cb(data))   # return coroutine; do NOT create_task
                    else:
                        cb(data)
                except Exception as e:
                    self.logger.exception(f"Error invoking subscriber for topic '{topic}': {e}")

        if tasks:
            # propagate errors; if you want to keep going per-subscriber, set return_exceptions=True
            await asyncio.gather(*tasks)

    def unsubscribe(self, topic: str, callback: Callable):
        """Remove a callback from a topic."""
        if callback in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(callback)
            name = getattr(callback, "__name__", str(callback))
            self.logger.debug(f"Unsubscribed {name} from topic '{topic}'")

    def clear(self):
        """Remove all subscriptions."""
        self._subscribers.clear()
        self.logger.debug("Cleared all event subscriptions")
