"""Serial queue helpers for adaptive catalog research."""

from __future__ import annotations

from collections import deque


class ResearchQueue:
    """Single-threaded queue with per-URL repeat limits."""

    def __init__(self, *, max_repeat_urls: int) -> None:
        self.max_repeat_urls = max(1, int(max_repeat_urls))
        self._queue: deque[str] = deque()
        self._counts: dict[str, int] = {}

    def push(self, url: str) -> bool:
        """Enqueue one URL when its repeat budget is not exhausted."""
        count = self._counts.get(url, 0)
        if count >= self.max_repeat_urls:
            return False
        self._counts[url] = count + 1
        self._queue.append(url)
        return True

    def pop(self) -> str | None:
        """Return the next queued URL or None when empty."""
        if not self._queue:
            return None
        return self._queue.popleft()
