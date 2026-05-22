"""
Session Manager for handling proxies, cookies, and header rotation.
Inspired by browser-act session management best practices.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.session_manager_support import (
    USER_AGENTS,
    ProxyConfig,
    SessionData,
    adaptive_delay,
    generate_fingerprint,
    generate_random_headers,
    load_session_from_disk as load_session_from_disk_impl,
    regional_headers_for_shop,
    save_session_to_disk as save_session_to_disk_impl,
)


class SessionManager:
    """
    Manages browser sessions with proxy rotation, cookie persistence,
    and header randomization.
    """

    USER_AGENTS = USER_AGENTS

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        max_session_age: timedelta = timedelta(minutes=30),
        max_requests_per_session: int = 100,
        rotate_on_failure: bool = True,
        session_storage_path: str = "sessions",
        save_sessions_to_disk: bool = True,
        block_images: bool = True,
        block_webgl: bool = False,
        humanize: bool = True,
        headless: str = "virtual",
    ):
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.sessions: Dict[str, SessionData] = {}
        self.max_session_age = max_session_age
        self.max_requests_per_session = max_requests_per_session
        self.rotate_on_failure = rotate_on_failure
        self.session_storage_path = Path(session_storage_path)
        self.save_sessions_to_disk = save_sessions_to_disk
        self._lock = asyncio.Lock()
        self.block_images = block_images
        self.block_webgl = block_webgl
        self.humanize = humanize
        self.headless = headless
        if self.save_sessions_to_disk:
            self.session_storage_path.mkdir(parents=True, exist_ok=True)

    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy from the pool using round-robin rotation."""
        if not self.proxies:
            return None
        async with self._lock:
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            return proxy

    async def get_random_proxy(self) -> Optional[ProxyConfig]:
        """Get random proxy from the pool."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def create_session(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        load_from_disk: bool = True,
    ) -> SessionData:
        """Create a new session or load one from disk."""
        async with self._lock:
            if load_from_disk:
                loaded_session = await self.load_session_from_disk(session_id)
                if loaded_session:
                    self.sessions[session_id] = loaded_session
                    return loaded_session
            session = SessionData(
                cookies=cookies or [],
                headers=headers or self._generate_random_headers(),
                user_agent=random.choice(self.USER_AGENTS),
            )
            self.sessions[session_id] = session
            if self.save_sessions_to_disk:
                await self.save_session_to_disk(session_id)
            return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get existing session by ID."""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            if not self._is_session_valid(session):
                session.is_valid = False
                del self.sessions[session_id]
                return None
            session.last_used = datetime.now()
            session.request_count += 1
            return session

    async def update_session(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Update session data."""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            if cookies is not None:
                existing_cookies = {cookie["name"]: cookie for cookie in session.cookies}
                for cookie in cookies:
                    existing_cookies[cookie["name"]] = cookie
                session.cookies = list(existing_cookies.values())
            if headers is not None:
                session.headers.update(headers)
            session.last_used = datetime.now()
            return True

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate and remove a session."""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def _is_session_valid(self, session: SessionData) -> bool:
        """Check if session is still valid."""
        if not session.is_valid:
            return False
        if session.age > self.max_session_age:
            return False
        if session.request_count >= self.max_requests_per_session:
            return False
        return True

    def _generate_random_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate randomized headers to avoid fingerprinting."""
        return generate_random_headers(custom_headers, user_agents=self.USER_AGENTS)

    def generate_fingerprint(self) -> Dict[str, Any]:
        """Generate complete browser fingerprint."""
        return generate_fingerprint(user_agents=self.USER_AGENTS)

    def get_adaptive_delay(
        self,
        min_delay: float = 1.0,
        max_delay: float = 5.0,
        session_id: Optional[str] = None,
    ) -> float:
        """Calculate adaptive delay based on session success rate."""
        return adaptive_delay(
            self.sessions,
            min_delay=min_delay,
            max_delay=max_delay,
            session_id=session_id,
        )

    async def save_session_to_disk(self, session_id: str) -> bool:
        """Save session data to disk."""
        return await save_session_to_disk_impl(
            self.sessions,
            session_id=session_id,
            session_storage_path=self.session_storage_path,
            save_sessions_to_disk_enabled=self.save_sessions_to_disk,
        )

    async def load_session_from_disk(self, session_id: str) -> Optional[SessionData]:
        """Load session data from disk."""
        return await load_session_from_disk_impl(
            session_id=session_id,
            session_storage_path=self.session_storage_path,
            max_session_age=self.max_session_age,
        )

    async def rotate_proxy_on_failure(self) -> Optional[ProxyConfig]:
        """Rotate proxy after failure."""
        if not self.rotate_on_failure:
            return None
        return await self.get_next_proxy()

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "total_proxies": len(self.proxies),
            "active_sessions": len([session for session in self.sessions.values() if session.is_valid]),
            "total_sessions": len(self.sessions),
            "current_proxy_index": self.current_proxy_index,
        }

    async def apply_regional_headers(
        self,
        session_id: str,
        shop_slug: str,
        kb_data: Optional[Dict[str, Any]] = None,
        region_id: Optional[str] = None,
        city_id: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> bool:
        """Apply regional headers based on shop requirements."""
        session = await self.get_session(session_id)
        if not session:
            return False
        regional_headers = regional_headers_for_shop(
            shop_slug=shop_slug,
            region_id=region_id,
            city_id=city_id,
            store_id=store_id,
        )
        if not regional_headers:
            return False
        session.headers.update(regional_headers)
        await self.update_session(session_id, headers=regional_headers)
        return True
