"""Small process-local TTL cache for FastAPI dashboard data."""

from __future__ import annotations

import datetime as dt
import functools
import pickle
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from typing import TypeVar

F = TypeVar("F", bound=Callable)
_cache_clearers: list[Callable[[], None]] = []
_refresh_lock = threading.Lock()
_last_refresh = dt.datetime.now().strftime("%H:%M:%S")


def register_cache_clearer(clearer: Callable[[], None]) -> None:
    """Register a cache clear callback, such as the SQLAlchemy engine pool."""
    _cache_clearers.append(clearer)


def ttl_cache(ttl_seconds: int) -> Callable[[F], F]:
    """Cache function results by arguments and return copies of cached values."""

    def decorate(function: F) -> F:
        entries: dict[bytes, tuple[float, object]] = {}
        lock = threading.RLock()

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            key = pickle.dumps((args, kwargs), protocol=pickle.HIGHEST_PROTOCOL)
            now = time.monotonic()
            with lock:
                cached = entries.get(key)
                if cached is not None and cached[0] > now:
                    return deepcopy(cached[1])
                entries.pop(key, None)

            result = function(*args, **kwargs)
            with lock:
                entries[key] = (time.monotonic() + ttl_seconds, deepcopy(result))
            return result

        def clear() -> None:
            with lock:
                entries.clear()

        wrapped.cache_clear = clear
        _cache_clearers.append(clear)
        return wrapped

    return decorate


def clear_all_caches() -> None:
    """Clear dashboard data caches and cached database engines."""
    for clear in tuple(_cache_clearers):
        clear()


def get_last_refresh_key() -> str:
    """Return the process-wide timestamp shown in the dashboard sidebar."""
    return _last_refresh


def bump_last_refresh() -> None:
    """Update the timestamp after a manual refresh."""
    global _last_refresh
    with _refresh_lock:
        _last_refresh = dt.datetime.now().strftime("%H:%M:%S")
