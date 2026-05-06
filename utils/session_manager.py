"""
Session Manager for handling proxies, cookies, and header rotation.
Inspired by browser-act session management best practices.

Enhanced with:
- Pydantic models for validation (V2)
- Advanced fingerprint generation
- Adaptive delays based on success rate
- Session persistence to disk
- Regional headers support (X-Region, X-Store, etc.)
"""

import asyncio
import random
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ConfigDict


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


class SessionManager:
    """
    Manages browser sessions with proxy rotation, cookie persistence,
    and header randomization.
    
    Features:
    - Proxy pool management with automatic rotation
    - Cookie/session persistence to disk
    - Header randomization to avoid fingerprinting
    - Session health checking
    - Adaptive delays based on success rate
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
    
    # Common viewports
    VIEWPORTS = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1280, 720),
    ]

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        max_session_age: timedelta = timedelta(minutes=30),
        max_requests_per_session: int = 100,
        rotate_on_failure: bool = True,
        session_storage_path: str = "sessions",
        save_sessions_to_disk: bool = True,
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
        
        # Create session storage directory
        if self.save_sessions_to_disk:
            self.session_storage_path.mkdir(parents=True, exist_ok=True)

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

    def _generate_random_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate randomized headers to avoid fingerprinting."""
        headers = {
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
        
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def generate_fingerprint(self) -> Dict[str, Any]:
        """Generate complete browser fingerprint."""
        width, height = random.choice(self.VIEWPORTS)
        
        return {
            "user_agent": random.choice(self.USER_AGENTS),
            "viewport": {"width": width, "height": height},
            "language": random.choice(self.ACCEPT_LANGUAGES),
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "hardware_concurrency": random.choice([4, 8, 12]),
            "device_memory": random.choice([4, 8, 16]),
        }
    
    def get_adaptive_delay(self, min_delay: float = 1.0, max_delay: float = 5.0, 
                          session_id: Optional[str] = None) -> float:
        """
        Calculate adaptive delay based on session success rate.
        Lower success rate = longer delays to avoid detection.
        """
        base_delay = random.uniform(min_delay, max_delay)
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            success_rate = session.success_rate
            
            # If success rate < 0.7, increase delay significantly
            if success_rate < 0.7:
                multiplier = 2.0 + (0.7 - success_rate) * 3
                return base_delay * multiplier
            # If success rate < 0.9, increase delay moderately
            elif success_rate < 0.9:
                return base_delay * 1.5
        
        return base_delay
    
    async def save_session_to_disk(self, session_id: str) -> bool:
        """Save session data to disk."""
        if not self.save_sessions_to_disk:
            return False
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session_file = self.session_storage_path / f"{session_id}_session.json"
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.model_dump(mode='json'), f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"[SessionManager] Error saving session: {e}")
            return False
    
    async def load_session_from_disk(self, session_id: str) -> Optional[SessionData]:
        """Load session data from disk."""
        session_file = self.session_storage_path / f"{session_id}_session.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = SessionData(**data)
            
            # Check if session is still valid
            if session.age > self.max_session_age:
                print(f"[SessionManager] Session {session_id} expired, removing")
                session_file.unlink()
                return None
            
            return session
        except Exception as e:
            print(f"[SessionManager] Error loading session: {e}")
            return None
    
    async def create_session(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        load_from_disk: bool = True,
    ) -> SessionData:
        """
        Create a new session or load from disk.
        
        Args:
            session_id: Unique session identifier.
            cookies: Initial cookies.
            headers: Initial headers.
            load_from_disk: Try to load existing session from disk.
            
        Returns:
            SessionData object.
        """
        async with self._lock:
            # Try to load from disk first
            if load_from_disk:
                loaded_session = await self.load_session_from_disk(session_id)
                if loaded_session:
                    print(f"[SessionManager] Loaded session {session_id} from disk")
                    self.sessions[session_id] = loaded_session
                    return loaded_session
            
            # Create new session
            session = SessionData(
                cookies=cookies or [],
                headers=headers or self._generate_random_headers(),
                user_agent=random.choice(self.USER_AGENTS),
            )
            self.sessions[session_id] = session
            
            if self.save_sessions_to_disk:
                await self.save_session_to_disk(session_id)
            
            return session

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

    async def apply_regional_headers(
        self,
        session_id: str,
        shop_slug: str,
        kb_data: Optional[Dict[str, Any]] = None,
        region_id: Optional[str] = None,
        city_id: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> bool:
        """
        Apply regional headers based on shop requirements from Knowledge Base.
        
        Args:
            session_id: Session identifier.
            shop_slug: Shop slug (e.g., 'lenta', 'auchan', 'okey').
            kb_data: Optional KB data with header requirements.
            region_id: Region ID (for Lenta, Auchan).
            city_id: City ID (for Magnit).
            store_id: Store ID (for O'Key, Auchan).
            
        Returns:
            bool: True if headers applied successfully.
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        regional_headers = {}
        
        # Apply headers based on shop requirements
        if shop_slug == 'lenta':
            if region_id:
                regional_headers['X-Region'] = region_id
            else:
                # Default region for Lenta (Moscow)
                regional_headers['X-Region'] = '2'
                
        elif shop_slug == 'auchan':
            if region_id:
                regional_headers['X-Region'] = region_id
            if store_id:
                regional_headers['X-Shop-Id'] = store_id
            else:
                # Defaults
                regional_headers['X-Region'] = '1'
                regional_headers['X-Shop-Id'] = '1'
                
        elif shop_slug == 'magnit':
            if city_id:
                regional_headers['X-City-Id'] = city_id
            else:
                # Default city (Moscow)
                regional_headers['X-City-Id'] = '1'
                
        elif shop_slug == 'okey':
            if store_id:
                regional_headers['X-Store-Id'] = store_id
            else:
                # Default store
                regional_headers['X-Store-Id'] = '1'
                
        elif shop_slug == 'pyaterochka':
            if region_id:
                regional_headers['X-Region-Id'] = region_id
            else:
                # Default region
                regional_headers['X-Region-Id'] = '1'
                
        elif shop_slug == 'perekrestok':
            if region_id:
                regional_headers['X-Region'] = region_id
            if store_id:
                regional_headers['X-Store-Id'] = store_id
        
        # Update session headers
        if regional_headers:
            session.headers.update(regional_headers)
            await self.update_session(session_id, headers=regional_headers)
            return True
            
        return False
