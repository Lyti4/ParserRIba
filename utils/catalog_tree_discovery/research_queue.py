"""Serial queue helpers for adaptive catalog research."""

from __future__ import annotations

import heapq


class ResearchQueue:
    """Single-threaded queue with per-URL repeat limits."""

    def __init__(self, *, max_repeat_urls: int) -> None:
        self.max_repeat_urls = max(1, int(max_repeat_urls))
        self._queue: list[tuple[int, int, str]] = []
        self._counts: dict[str, int] = {}
        self._skipped: list[str] = []
        self.enqueued_count = 0
        self._sequence = 0

    def push(self, url: str, *, priority: int = 50) -> bool:
        """Enqueue one URL when its repeat budget is not exhausted."""
        count = self._counts.get(url, 0)
        if count >= self.max_repeat_urls:
            self.skip(url, "repeat_limit")
            return False
        self._counts[url] = count + 1
        self._sequence += 1
        heapq.heappush(self._queue, (int(priority), self._sequence, url))
        self.enqueued_count += 1
        return True

    def pop(self) -> str | None:
        """Return the next queued URL or None when empty."""
        if not self._queue:
            return None
        return heapq.heappop(self._queue)[2]

    def skip(self, url: str, reason: str) -> None:
        """Remember one skipped URL reason for internal diagnostics."""
        self._skipped.append(f"{reason}:{url}")

    def diagnostic_notes(self) -> list[str]:
        """Return compact frontier notes for profile snapshots."""
        notes = [f"frontier_enqueued:{self.enqueued_count}", f"frontier_pending:{len(self._queue)}"]
        reason_counts: dict[str, int] = {}
        for item in self._skipped:
            reason = item.split(":", 1)[0]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        notes.extend(f"frontier_skipped_{reason}:{count}" for reason, count in sorted(reason_counts.items()))
        return notes
