"""Support models and helpers for session manager runtime."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    country: Optional[str] = None
    is_residential: bool = True

    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class SessionData(BaseModel):
    """Session data including cookies and headers."""

    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={datetime: lambda v: v.isoformat()})

    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    local_storage: Dict[str, str] = Field(default_factory=dict)
    user_agent: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: datetime = Field(default_factory=datetime.now)
    request_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    is_valid: bool = True

    @property
    def age(self) -> timedelta:
        """Get session age."""
        return datetime.now() - self.created_at

    @property
    def idle_time(self) -> timedelta:
        """Get time since last use."""
        return datetime.now() - self.last_used

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.fail_count
        if total == 0:
            return 1.0
        return self.success_count / total


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "ru-RU,ru;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
]
VIEWPORTS = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
]


def generate_random_headers(
    custom_headers: Optional[Dict[str, str]] = None,
    *,
    user_agents: list[str] | None = None,
    accept_languages: list[str] | None = None,
) -> Dict[str, str]:
    """Generate randomized headers to avoid fingerprinting."""
    headers = {
        "User-Agent": random.choice(user_agents or USER_AGENTS),
        "Accept-Language": random.choice(accept_languages or ACCEPT_LANGUAGES),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    if custom_headers:
        headers.update(custom_headers)
    return headers


def generate_fingerprint(*, user_agents: list[str] | None = None) -> Dict[str, Any]:
    """Generate complete browser fingerprint."""
    width, height = random.choice(VIEWPORTS)
    return {
        "user_agent": random.choice(user_agents or USER_AGENTS),
        "viewport": {"width": width, "height": height},
        "language": random.choice(ACCEPT_LANGUAGES),
        "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
        "hardware_concurrency": random.choice([4, 8, 12]),
        "device_memory": random.choice([4, 8, 16]),
    }


def adaptive_delay(
    sessions: dict[str, SessionData],
    *,
    min_delay: float,
    max_delay: float,
    session_id: Optional[str],
) -> float:
    """Calculate adaptive delay based on session success rate."""
    base_delay = random.uniform(min_delay, max_delay)
    if session_id and session_id in sessions:
        session = sessions[session_id]
        success_rate = session.success_rate
        if success_rate < 0.7:
            multiplier = 2.0 + (0.7 - success_rate) * 3
            return base_delay * multiplier
        if success_rate < 0.9:
            return base_delay * 1.5
    return base_delay


async def save_session_to_disk(
    sessions: dict[str, SessionData],
    *,
    session_id: str,
    session_storage_path: Path,
    save_sessions_to_disk_enabled: bool,
) -> bool:
    """Save session data to disk."""
    if not save_sessions_to_disk_enabled:
        return False
    session = sessions.get(session_id)
    if not session:
        return False
    session_file = session_storage_path / f"{session_id}_session.json"
    try:
        with open(session_file, "w", encoding="utf-8") as handle:
            json.dump(session.model_dump(mode="json"), handle, indent=2, default=str)
        return True
    except Exception as exc:
        logger.warning("SessionManager save_session_to_disk failed for {}: {}", session_id, exc)
        return False


async def load_session_from_disk(
    *,
    session_id: str,
    session_storage_path: Path,
    max_session_age: timedelta,
) -> Optional[SessionData]:
    """Load session data from disk."""
    session_file = session_storage_path / f"{session_id}_session.json"
    if not session_file.exists():
        return None
    try:
        with open(session_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        session = SessionData(**data)
        if session.age > max_session_age:
            logger.warning("SessionManager session {} expired on disk; removing", session_id)
            session_file.unlink()
            return None
        return session
    except Exception as exc:
        logger.warning("SessionManager load_session_from_disk failed for {}: {}", session_id, exc)
        return None


def regional_headers_for_shop(
    *,
    shop_slug: str,
    region_id: Optional[str] = None,
    city_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> Dict[str, str]:
    """Return regional headers based on shop-specific expectations."""
    headers: Dict[str, str] = {}
    if shop_slug == "lenta":
        headers["X-Region"] = region_id or "2"
    elif shop_slug == "auchan":
        headers["X-Region"] = region_id or "1"
        headers["X-Shop-Id"] = store_id or "1"
    elif shop_slug == "magnit":
        headers["X-City-Id"] = city_id or "1"
    elif shop_slug == "okey":
        headers["X-Store-Id"] = store_id or "1"
    elif shop_slug == "pyaterochka":
        headers["X-Region-Id"] = region_id or "1"
    elif shop_slug == "perekrestok":
        if region_id:
            headers["X-Region"] = region_id
        if store_id:
            headers["X-Store-Id"] = store_id
    return headers
