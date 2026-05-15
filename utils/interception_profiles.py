"""Store-specific interception route profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class InterceptionProfile:
    """Rules for classifying safe intercepted routes for one store."""

    store: str
    product_api_path_markers: tuple[str, ...]
    api_path_markers: tuple[str, ...] = ("/api/",)
    challenge_markers: tuple[str, ...] = ("captcha", "challenge", "antibot")
    image_markers: tuple[str, ...] = ("image/", ".png", ".jpg", ".jpeg", ".webp", ".svg")
    script_markers: tuple[str, ...] = (".js",)
    allowed_hosts: tuple[str, ...] = field(default_factory=tuple)

    def classify_route(self, url: str, content_type: str = "") -> str:
        """Classify a URL using this store profile."""
        lowered = url.lower()
        path = urlsplit(lowered).path
        host = urlsplit(lowered).netloc
        if self.allowed_hosts and not any(host.endswith(item) for item in self.allowed_hosts):
            return "external"
        if any(marker in lowered for marker in self.challenge_markers):
            return "challenge"
        if any(marker in path for marker in self.product_api_path_markers):
            return "product_api"
        if any(marker in path for marker in self.api_path_markers):
            return "api"
        if any(marker in lowered for marker in self.image_markers):
            return "asset_image"
        if "javascript" in content_type.lower() or any(path.endswith(marker) for marker in self.script_markers):
            return "asset_script"
        return "document" if "html" in content_type.lower() else "unknown"


PYATEROCHKA_INTERCEPTION_PROFILE = InterceptionProfile(
    store="pyaterochka",
    allowed_hosts=("5ka.ru", "5d.5ka.ru"),
    challenge_markers=("xpvnsulc", "captcha", "challenge", "antibot"),
    product_api_path_markers=("/api/catalog", "/api/orders", "/api/products", "/api/search"),
)

GENERIC_INTERCEPTION_PROFILE = InterceptionProfile(
    store="generic",
    challenge_markers=("xpvnsulc", "captcha", "challenge", "antibot"),
    product_api_path_markers=("/api/catalog", "/api/products", "/api/search", "/api/orders"),
)


def get_interception_profile(store: str, knowledge: Any | None = None) -> InterceptionProfile:
    """Return route classification profile for a store."""
    profile = _profile_from_knowledge(store, knowledge)
    if profile:
        return profile
    if store.lower() == "pyaterochka":
        return PYATEROCHKA_INTERCEPTION_PROFILE
    return GENERIC_INTERCEPTION_PROFILE


def _profile_from_knowledge(store: str, knowledge: Any | None) -> InterceptionProfile | None:
    config = getattr(knowledge, "interception", None)
    if not config:
        return None
    product_markers = tuple(getattr(config, "product_api_path_markers", []) or [])
    allowed_hosts = tuple(getattr(config, "allowed_hosts", []) or [])
    if not product_markers and not allowed_hosts:
        return None
    return InterceptionProfile(
        store=store,
        product_api_path_markers=product_markers or GENERIC_INTERCEPTION_PROFILE.product_api_path_markers,
        api_path_markers=tuple(getattr(config, "api_path_markers", []) or GENERIC_INTERCEPTION_PROFILE.api_path_markers),
        challenge_markers=tuple(
            getattr(config, "challenge_markers", []) or GENERIC_INTERCEPTION_PROFILE.challenge_markers
        ),
        image_markers=tuple(getattr(config, "image_markers", []) or GENERIC_INTERCEPTION_PROFILE.image_markers),
        script_markers=tuple(getattr(config, "script_markers", []) or GENERIC_INTERCEPTION_PROFILE.script_markers),
        allowed_hosts=allowed_hosts,
    )
