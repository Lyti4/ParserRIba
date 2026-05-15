"""Persisted proxy health history without storing proxy credentials."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from utils.proxy import mask_proxy_url


@dataclass(frozen=True)
class ProxyAttemptRecord:
    """Safe proxy attempt data stored in SQLite."""

    store: str
    proxy_url: str
    session_id: str
    run_id: str
    success: bool
    reason: str
    health_status: str
    traffic_risk: str
    response_count: int
    estimated_body_bytes: int
    duration_ms: int
    observed_ip: str
    preflight_ok: bool | None
    status_counts: dict[str, int]
    failure_counts: dict[str, int]


class ProxyHistoryStore:
    """SQLite-backed proxy history used for diagnostics and ranking."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create the history table if it does not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proxy_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    store TEXT NOT NULL,
                    proxy_key TEXT NOT NULL,
                    proxy_mask TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    health_status TEXT NOT NULL,
                    traffic_risk TEXT NOT NULL,
                    response_count INTEGER NOT NULL,
                    estimated_body_bytes INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    observed_ip TEXT NOT NULL,
                    preflight_ok INTEGER,
                    status_counts TEXT NOT NULL,
                    failure_counts TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_proxy_attempts_lookup "
                "ON proxy_attempts(store, proxy_key, created_at)"
            )

    def record_attempt(self, record: ProxyAttemptRecord) -> None:
        """Persist one sanitized proxy attempt."""
        if not record.proxy_url:
            return
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO proxy_attempts (
                    created_at, store, proxy_key, proxy_mask, session_id, run_id,
                    success, reason, health_status, traffic_risk, response_count,
                    estimated_body_bytes, duration_ms, observed_ip, preflight_ok,
                    status_counts, failure_counts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    record.store,
                    proxy_key(record.proxy_url),
                    mask_proxy_url(record.proxy_url),
                    record.session_id,
                    record.run_id,
                    int(record.success),
                    record.reason[:160],
                    record.health_status[:80],
                    record.traffic_risk[:40],
                    record.response_count,
                    record.estimated_body_bytes,
                    record.duration_ms,
                    record.observed_ip[:80],
                    None if record.preflight_ok is None else int(record.preflight_ok),
                    json.dumps(record.status_counts, ensure_ascii=False, sort_keys=True),
                    json.dumps(record.failure_counts, ensure_ascii=False, sort_keys=True),
                ),
            )

    def rank_proxy_urls(self, store: str, proxy_urls: list[str]) -> list[str]:
        """Return proxy URLs ordered by recent local history."""
        if not proxy_urls or not self.db_path.exists():
            return proxy_urls
        stats_by_key = {item["proxy_key"]: item for item in self.proxy_stats(store, proxy_urls)}
        indexed = list(enumerate(proxy_urls))
        indexed.sort(key=lambda item: (-_score_stats(stats_by_key.get(proxy_key(item[1]))), item[0]))
        return [proxy_url for _, proxy_url in indexed]

    def proxy_stats(self, store: str, proxy_urls: list[str]) -> list[dict[str, Any]]:
        """Return report-safe stats for the given proxy list."""
        if not proxy_urls or not self.db_path.exists():
            return []
        keys = [proxy_key(proxy_url) for proxy_url in proxy_urls]
        placeholders = ",".join("?" for _ in keys)
        query = f"""
            SELECT
                proxy_key,
                MAX(proxy_mask) AS proxy_mask,
                COUNT(*) AS attempts,
                SUM(success) AS successes,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failures,
                AVG(response_count) AS avg_responses,
                AVG(estimated_body_bytes) AS avg_body_bytes,
                MAX(created_at) AS last_seen,
                MAX(CASE WHEN success = 1 THEN created_at ELSE '' END) AS last_success,
                SUM(CASE WHEN traffic_risk = 'high' THEN 1 ELSE 0 END) AS high_risk_attempts
            FROM proxy_attempts
            WHERE store = ? AND proxy_key IN ({placeholders})
            GROUP BY proxy_key
        """
        with self._connect() as connection:
            rows = connection.execute(query, [store, *keys]).fetchall()
        return [_row_to_stats(row) for row in rows]

    def summary(self, store: str, proxy_urls: list[str]) -> dict[str, Any]:
        """Return report-safe proxy history summary."""
        stats = self.proxy_stats(store, proxy_urls)
        ranked = self.rank_proxy_urls(store, proxy_urls)
        return {
            "enabled": bool(proxy_urls),
            "db_path": str(self.db_path),
            "known_proxies": len(stats),
            "ranked_proxies": [mask_proxy_url(proxy_url) for proxy_url in ranked[:5]],
            "stats": stats,
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def proxy_key(proxy_url: str) -> str:
    """Return a stable non-secret key for a proxy URL."""
    return hashlib.sha256(proxy_url.strip().encode("utf-8")).hexdigest()


def build_proxy_attempt_record(
    *,
    store: str,
    proxy_url: str,
    session_id: str,
    run_id: str,
    result: dict[str, Any],
) -> ProxyAttemptRecord:
    """Build a safe history record from a smoke/discovery result."""
    network = result.get("network") or {}
    diagnostics = result.get("proxy_diagnostics") or {}
    health = diagnostics.get("health") or {}
    preflight = diagnostics.get("preflight") or {}
    attempt = result.get("attempt_context") or {}
    discovery_success = int(result.get("product_events_count") or 0) > 0
    success = bool((result.get("cards_found", 0) > 0 or discovery_success) and not result.get("blocked"))
    reason = str(result.get("block_reason") or result.get("reason") or health.get("status") or "")
    status_counts = network.get("status_counts") or result.get("status_counts") or {}
    return ProxyAttemptRecord(
        store=store,
        proxy_url=proxy_url,
        session_id=session_id,
        run_id=run_id,
        success=success,
        reason=reason or ("ok" if success else "unknown"),
        health_status=str(health.get("status") or ""),
        traffic_risk=str(health.get("traffic_risk") or ""),
        response_count=int(network.get("responses") or result.get("events_count") or 0),
        estimated_body_bytes=int(network.get("estimated_body_bytes") or 0),
        duration_ms=int(attempt.get("duration_ms") or 0),
        observed_ip=str(result.get("browser_external_ip") or preflight.get("ip") or ""),
        preflight_ok=preflight.get("ok") if isinstance(preflight.get("ok"), bool) else None,
        status_counts=_int_counts(status_counts),
        failure_counts=_int_counts(network.get("failure_counts") or {}),
    )


def _int_counts(value: dict[str, Any]) -> dict[str, int]:
    return {str(key): int(count) for key, count in value.items()}


def _row_to_stats(row: sqlite3.Row) -> dict[str, Any]:
    attempts = int(row["attempts"] or 0)
    successes = int(row["successes"] or 0)
    return {
        "proxy_key": str(row["proxy_key"]),
        "proxy": str(row["proxy_mask"]),
        "attempts": attempts,
        "successes": successes,
        "failures": int(row["failures"] or 0),
        "success_rate": round(successes / attempts, 3) if attempts else 0.0,
        "avg_responses": round(float(row["avg_responses"] or 0), 1),
        "avg_body_bytes": int(row["avg_body_bytes"] or 0),
        "last_seen": str(row["last_seen"] or ""),
        "last_success": str(row["last_success"] or ""),
        "high_risk_attempts": int(row["high_risk_attempts"] or 0),
    }


def _score_stats(stats: dict[str, Any] | None) -> float:
    if not stats:
        return 50.0
    attempts = int(stats.get("attempts") or 0)
    success_rate = float(stats.get("success_rate") or 0)
    high_risk = int(stats.get("high_risk_attempts") or 0)
    response_bonus = min(float(stats.get("avg_responses") or 0), 30.0) / 3
    confidence = min(attempts, 10) / 10
    return 50.0 + (success_rate * 50 * confidence) + response_bonus - (high_risk * 8)
