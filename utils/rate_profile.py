"""Rate and cooldown profiles for parser runs."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RateProfile:
    """Timing limits for one store or parser mode."""

    name: str = "protected-store"
    max_concurrency: int = 1
    max_attempts: int = 3
    first_navigation_pause_ms: tuple[int, int] = (3_000, 8_000)
    warmup_ms: tuple[int, int] = (10_000, 30_000)
    post_load_settle_ms: tuple[int, int] = (8_000, 20_000)
    category_pause_ms: tuple[int, int] = (20_000, 60_000)
    empty_result_cooldown_ms: tuple[int, int] = (20_000, 45_000)
    network_cooldown_ms: tuple[int, int] = (10_000, 30_000)
    block_cooldown_ms: tuple[int, int] = (300_000, 900_000)
    discovery_listen_seconds: tuple[int, int] = (180, 300)

    def choose_delay_ms(self, bounds: tuple[int, int], rng: random.Random | None = None) -> int:
        """Return a random delay inside inclusive millisecond bounds."""
        source = rng or random
        low, high = bounds
        return source.randint(low, max(low, high))

    def cooldown_for_reason(self, reason: str, rng: random.Random | None = None) -> int:
        """Return a cooldown in milliseconds for a normalized result reason."""
        normalized = reason.lower()
        if "captcha" in normalized or "antibot" in normalized or normalized in {"http_403", "http_429"}:
            return self.choose_delay_ms(self.block_cooldown_ms, rng)
        if normalized.startswith("network_") or "proxy" in normalized:
            return self.choose_delay_ms(self.network_cooldown_ms, rng)
        return self.choose_delay_ms(self.empty_result_cooldown_ms, rng)

    def summary(self) -> dict[str, Any]:
        """Return a JSON-safe summary for run reports."""
        return asdict(self)


def protected_store_rate_profile(name: str = "protected-store") -> RateProfile:
    """Return the default conservative profile for defended e-commerce sites."""
    return RateProfile(name=name)
