"""Rate limiting simples em memória (janela deslizante por chave)."""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_events: int, window_seconds: float):
        self.max = max_events
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.max:
            return False
        dq.append(now)
        return True
