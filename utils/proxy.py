"""Proxy helpers for browser and HTTP clients."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class ParsedProxy:
    """Validated proxy connection settings."""

    server: str
    username: str | None = None
    password: str | None = None

    def as_playwright(self) -> dict[str, str]:
        """Return Playwright-compatible proxy configuration."""
        config = {"server": self.server}
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
        return config


@dataclass(frozen=True)
class ProxyConfig:
    """Proxy settings loaded from local environment variables."""

    enabled: bool
    urls: list[str]
    scheme: str = "http"

    @property
    def primary(self) -> str:
        """Return the first configured proxy URL, if any."""
        return self.urls[0] if self.urls else ""


def parse_proxy_url(proxy_url: str) -> ParsedProxy:
    """Parse a proxy URL into server and credentials."""
    parsed = urlsplit(proxy_url.strip())
    if not parsed.hostname or not parsed.port:
        return ParsedProxy(server=proxy_url.strip())

    scheme = parsed.scheme or "http"
    return ParsedProxy(
        server=f"{scheme}://{parsed.hostname}:{parsed.port}",
        username=unquote(parsed.username) if parsed.username else None,
        password=unquote(parsed.password) if parsed.password else None,
    )


def mask_proxy_url(proxy_url: str) -> str:
    """Return a log-safe proxy URL without credentials."""
    parsed = urlsplit(proxy_url.strip())
    if not parsed.hostname or not parsed.port:
        return "<proxy>"
    scheme = parsed.scheme or "http"
    return f"{scheme}://***:***@{parsed.hostname}:{parsed.port}"


def split_proxy_urls(value: str) -> list[str]:
    """Split comma/newline/semicolon separated proxy URLs."""
    urls: list[str] = []
    for raw_line in value.replace(";", "\n").replace(",", "\n").splitlines():
        proxy_url = raw_line.strip()
        if proxy_url:
            urls.append(proxy_url)
    return urls


def normalize_proxy_url(proxy_url: str, *, scheme: str = "http") -> str:
    """Return a URL usable by Playwright from URL or host:port:user:pass input."""
    value = proxy_url.strip()
    if not value:
        return ""
    if "://" in value:
        return value

    parts = value.split(":", 3)
    if len(parts) == 4 and parts[1].isdigit():
        host, port, username, password = parts
        safe_username = quote(username, safe="")
        safe_password = quote(password, safe="")
        return f"{scheme}://{safe_username}:{safe_password}@{host}:{port}"
    return value


def proxy_enabled_from_env(value: str | None) -> bool:
    """Return False only for explicit local opt-out values."""
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def load_proxy_urls(primary: str = "", pool: str = "", *, enabled: bool = True, scheme: str = "http") -> list[str]:
    """Return proxy URLs with the primary proxy first and duplicates removed."""
    if not enabled:
        return []
    ordered: list[str] = []
    for proxy_url in [primary.strip(), *split_proxy_urls(pool)]:
        normalized = normalize_proxy_url(proxy_url, scheme=scheme)
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


def load_proxy_config_from_env(env: Mapping[str, str]) -> ProxyConfig:
    """Load ParserRIba proxy settings from environment variables."""
    enabled = proxy_enabled_from_env(env.get("PARSER_PROXY_ENABLED"))
    scheme = (env.get("PARSER_PROXY_SCHEME") or "http").strip().lower() or "http"
    urls = load_proxy_urls(
        primary=env.get("PARSER_PROXY", ""),
        pool=env.get("PARSER_PROXIES", ""),
        enabled=enabled,
        scheme=scheme,
    )
    return ProxyConfig(enabled=enabled, urls=urls, scheme=scheme)


def choose_proxy_for_attempt(proxy_urls: list[str], attempt: int) -> str:
    """Return a proxy URL for a 1-based attempt number."""
    if not proxy_urls:
        return ""
    return proxy_urls[(attempt - 1) % len(proxy_urls)]
