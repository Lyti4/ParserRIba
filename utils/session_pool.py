"""Local parser session pool with proxy affinity and health scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from utils.proxy import mask_proxy_url


@dataclass
class ParserSession:
    """State for one browser/proxy/profile session."""

    store: str
    proxy_url: str = ""
    session_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    uses: int = 0
    successes: int = 0
    failures: int = 0
    quarantined_until: datetime | None = None
    last_reason: str = ""

    @property
    def success_rate(self) -> float:
        """Return success rate for completed attempts."""
        total = self.successes + self.failures
        if total == 0:
            return 1.0
        return self.successes / total

    def is_available(self, now: datetime | None = None) -> bool:
        """Return True when the session is not quarantined."""
        current = now or datetime.now()
        return self.quarantined_until is None or self.quarantined_until <= current

    def mark_used(self) -> None:
        """Record one session use."""
        self.uses += 1
        self.last_used_at = datetime.now()

    def record_success(self) -> None:
        """Record a successful attempt."""
        self.successes += 1
        self.last_reason = "ok"
        self.quarantined_until = None

    def record_failure(self, reason: str, cooldown_ms: int = 0) -> None:
        """Record a failed attempt and optionally quarantine the session."""
        self.failures += 1
        self.last_reason = reason
        if cooldown_ms > 0:
            self.quarantined_until = datetime.now() + timedelta(milliseconds=cooldown_ms)

    def summary(self) -> dict[str, Any]:
        """Return a report-safe session summary."""
        data = asdict(self)
        data["proxy_url"] = mask_proxy_url(self.proxy_url) if self.proxy_url else ""
        data["created_at"] = self.created_at.isoformat(timespec="seconds")
        data["last_used_at"] = self.last_used_at.isoformat(timespec="seconds")
        data["quarantined_until"] = (
            self.quarantined_until.isoformat(timespec="seconds") if self.quarantined_until else ""
        )
        data["success_rate"] = self.success_rate
        return data


class SessionPool:
    """Small in-memory session pool used by parser orchestration."""

    def __init__(self, store: str, proxy_urls: list[str] | None = None, max_uses: int = 50) -> None:
        self.store = store
        self.proxy_urls = proxy_urls or []
        self.max_uses = max_uses
        self._sessions: list[ParserSession] = []
        self._next_proxy_index = 0

    def acquire(self) -> ParserSession:
        """Return an available session or create a new one."""
        for session in self._sessions:
            if session.uses < self.max_uses and session.is_available():
                session.mark_used()
                return session

        proxy_url = self._next_proxy()
        session = ParserSession(store=self.store, proxy_url=proxy_url)
        session.mark_used()
        self._sessions.append(session)
        return session

    def record_success(self, session_id: str) -> None:
        """Record success for a known session."""
        session = self._find(session_id)
        if session:
            session.record_success()

    def record_failure(self, session_id: str, reason: str, cooldown_ms: int = 0) -> None:
        """Record failure for a known session."""
        session = self._find(session_id)
        if session:
            session.record_failure(reason, cooldown_ms)

    def summary(self) -> dict[str, Any]:
        """Return a report-safe pool summary."""
        return {
            "store": self.store,
            "total_sessions": len(self._sessions),
            "available_sessions": sum(1 for session in self._sessions if session.is_available()),
            "sessions": [session.summary() for session in self._sessions],
        }

    def _next_proxy(self) -> str:
        if not self.proxy_urls:
            return ""
        proxy_url = self.proxy_urls[self._next_proxy_index % len(self.proxy_urls)]
        self._next_proxy_index += 1
        return proxy_url

    def _find(self, session_id: str) -> ParserSession | None:
        for session in self._sessions:
            if session.session_id == session_id:
                return session
        return None
