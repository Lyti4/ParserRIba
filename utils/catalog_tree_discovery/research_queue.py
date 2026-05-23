"""Serial queue helpers for adaptive catalog research."""

from __future__ import annotations

import heapq


class ResearchQueue:
    """Single-threaded queue with per-URL repeat limits."""

    def __init__(self, *, max_repeat_urls: int) -> None:
        self.max_repeat_urls = max(1, int(max_repeat_urls))
        self._queue: list[tuple[int, int, str]] = []
        self._counts: dict[str, int] = {}
        self._sequence = 0

    def push(self, url: str, *, priority: int = 50) -> bool:
        """Enqueue one URL when its repeat budget is not exhausted."""
        count = self._counts.get(url, 0)
        if count >= self.max_repeat_urls:
            return False
        self._counts[url] = count + 1
        self._sequence += 1
        heapq.heappush(self._queue, (int(priority), self._sequence, url))
        return True

    def pop(self) -> str | None:
        """Return the next queued URL or None when empty."""
        if not self._queue:
            return None
        return heapq.heappop(self._queue)[2]
