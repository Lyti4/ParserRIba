"""Proxy helpers for browser and HTTP clients."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


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


def load_proxy_urls(primary: str = "", pool: str = "") -> list[str]:
    """Return proxy URLs with the primary proxy first and duplicates removed."""
    ordered: list[str] = []
    for proxy_url in [primary.strip(), *split_proxy_urls(pool)]:
        if proxy_url and proxy_url not in ordered:
            ordered.append(proxy_url)
    return ordered


def choose_proxy_for_attempt(proxy_urls: list[str], attempt: int) -> str:
    """Return a proxy URL for a 1-based attempt number."""
    if not proxy_urls:
        return ""
    return proxy_urls[(attempt - 1) % len(proxy_urls)]
