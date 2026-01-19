from __future__ import annotations

import threading
import time

from app.core.config import settings

# 2024-01-01T00:00:00Z in milliseconds. Keeps generated IDs smaller.
_EPOCH_MS = 1704067200000


class Snowflake:
    """
    64-bit Snowflake ID generator:
      41 bits: timestamp (ms) since _EPOCH_MS
      10 bits: node id (0..1023)
      12 bits: sequence within the same millisecond (0..4095)
    """

    def __init__(self, *, node_id: int) -> None:
        if not (0 <= node_id <= 1023):
            raise ValueError("SNOWFLAKE_NODE_ID must be in [0, 1023]")
        self._node_id = node_id
        self._lock = threading.Lock()
        self._last_ts = -1
        self._seq = 0

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def next_id(self) -> int:
        with self._lock:
            ts = self._now_ms()
            if ts < self._last_ts:
                # Clock moved backwards. Wait until it catches up.
                ts = self._wait_until(self._last_ts)

            if ts == self._last_ts:
                self._seq = (self._seq + 1) & 0xFFF
                if self._seq == 0:
                    ts = self._wait_until(self._last_ts + 1)
            else:
                self._seq = 0

            self._last_ts = ts
            return ((ts - _EPOCH_MS) << 22) | (self._node_id << 12) | self._seq

    @classmethod
    def _wait_until(cls, target_ms: int) -> int:
        ts = cls._now_ms()
        while ts < target_ms:
            time.sleep(0.001)
            ts = cls._now_ms()
        return ts


_GENERATOR: Snowflake | None = None


def _get_generator() -> Snowflake:
    global _GENERATOR
    if _GENERATOR is None:
        _GENERATOR = Snowflake(node_id=settings.SNOWFLAKE_NODE_ID)
    return _GENERATOR


def generate_id() -> int:
    return _get_generator().next_id()

