"""
Session Manager for handling proxies, cookies, and header rotation.
Inspired by browser-act session management best practices.
"""

import asyncio
import random
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class SessionData:
    """Session data including cookies and headers."""
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    is_valid: bool = True
    
    @property
    def age(self) -> timedelta:
        """Get session age."""
        return datetime.now() - self.created_at
    
    @property
    def idle_time(self) -> timedelta:
        """Get time since last use."""
        return datetime.now() - self.last_used


class SessionManager:
    """
    Manages browser sessions with proxy rotation, cookie persistence,
    and header randomization.
    
    Features:
    - Proxy pool management with automatic rotation
    - Cookie/session persistence
    - Header randomization to avoid fingerprinting
    - Session health checking
    - Automatic retry on failure
    """

    # Common user agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Common accept languages
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "ru-RU,ru;q=0.9,en;q=0.8",
        "de-DE,de;q=0.9,en;q=0.8",
        "fr-FR,fr;q=0.9,en;q=0.8",
    ]

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        max_session_age: timedelta = timedelta(minutes=30),
        max_requests_per_session: int = 100,
        rotate_on_failure: bool = True,
    ):
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.sessions: Dict[str, SessionData] = {}
        self.max_session_age = max_session_age
        self.max_requests_per_session = max_requests_per_session
        self.rotate_on_failure = rotate_on_failure
        self._lock = asyncio.Lock()

    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """
        Get next proxy from the pool using round-robin rotation.
        
        Returns:
            ProxyConfig or None if no proxies configured.
        """
        if not self.proxies:
            return None
            
        async with self._lock:
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            return proxy

    async def get_random_proxy(self) -> Optional[ProxyConfig]:
        """
        Get random proxy from the pool.
        
        Returns:
            ProxyConfig or None if no proxies configured.
        """
        if not self.proxies:
            return None
            
        return random.choice(self.proxies)

    async def create_session(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> SessionData:
        """
        Create a new session with optional initial data.
        
        Args:
            session_id: Unique session identifier.
            cookies: Initial cookies.
            headers: Initial headers.
            
        Returns:
            SessionData object.
        """
        async with self._lock:
            session = SessionData(
                cookies=cookies or [],
                headers=headers or self._generate_random_headers(),
            )
            self.sessions[session_id] = session
            return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get existing session by ID.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            SessionData or None if not found or expired.
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            
            if not session:
                return None
                
            # Check if session is still valid
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
        """
        Update session data.
        
        Args:
            session_id: Session identifier.
            cookies: New cookies to add/replace.
            headers: New headers to add/replace.
            
        Returns:
            bool: True if updated successfully.
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
                
            if cookies is not None:
                # Merge cookies
                existing_cookies = {c["name"]: c for c in session.cookies}
                for cookie in cookies:
                    existing_cookies[cookie["name"]] = cookie
                session.cookies = list(existing_cookies.values())
                
            if headers is not None:
                session.headers.update(headers)
                
            session.last_used = datetime.now()
            return True

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate and remove a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            bool: True if invalidated successfully.
        """
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def _is_session_valid(self, session: SessionData) -> bool:
        """Check if session is still valid."""
        if not session.is_valid:
            return False
            
        # Check age
        if session.age > self.max_session_age:
            return False
            
        # Check request count
        if session.request_count >= self.max_requests_per_session:
            return False
            
        # Check idle time (optional: expire after long idle)
        # if session.idle_time > timedelta(hours=1):
        #     return False
            
        return True

    def _generate_random_headers(self) -> Dict[str, str]:
        """Generate randomized headers to avoid fingerprinting."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    async def rotate_proxy_on_failure(self) -> Optional[ProxyConfig]:
        """
        Rotate proxy after failure.
        
        Returns:
            New proxy config or None.
        """
        if not self.rotate_on_failure:
            return None
            
        # Skip current proxy (it's already incremented in get_next_proxy)
        # Just get the next one
        return await self.get_next_proxy()

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "total_proxies": len(self.proxies),
            "active_sessions": len([s for s in self.sessions.values() if s.is_valid]),
            "total_sessions": len(self.sessions),
            "current_proxy_index": self.current_proxy_index,
        }
