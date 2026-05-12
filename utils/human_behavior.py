"""Small human-like browsing routines for browser based parsers."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from loguru import logger


@dataclass(frozen=True)
class HumanBehaviorProfile:
    """Timing and movement profile used while a category page is loading."""

    name: str = "default"
    min_pause_ms: int = 350
    max_pause_ms: int = 1_400
    scroll_steps_min: int = 4
    scroll_steps_max: int = 7
    scroll_delta_min: int = 320
    scroll_delta_max: int = 820
    micro_scroll_delta: int = 140
    hover_cards: int = 5
    mouse_move_steps_min: int = 8
    mouse_move_steps_max: int = 18

    def summary(self) -> dict[str, Any]:
        """Return a serializable profile summary for diagnostics."""
        return asdict(self)


def build_category_behavior_profile(category_name: str) -> HumanBehaviorProfile:
    """Build a behavior profile for a product category."""
    normalized = category_name.lower()
    if "рыб" in normalized or "fish" in normalized:
        return HumanBehaviorProfile(
            name="fish-category",
            min_pause_ms=550,
            max_pause_ms=1_800,
            scroll_steps_min=5,
            scroll_steps_max=8,
            scroll_delta_min=280,
            scroll_delta_max=760,
            hover_cards=6,
        )
    return HumanBehaviorProfile(name="default-category")


async def human_pause(page: Any, profile: HumanBehaviorProfile, factor: float = 1.0) -> None:
    """Wait for a randomized human-like pause using the browser event loop."""
    min_ms = max(0, int(profile.min_pause_ms * factor))
    max_ms = max(min_ms, int(profile.max_pause_ms * factor))
    await page.wait_for_timeout(random.randint(min_ms, max_ms))


async def browse_category_page(page: Any, profile: HumanBehaviorProfile) -> None:
    """Scroll and pause like a user browsing a category page."""
    await human_pause(page, profile, factor=1.2)
    steps = random.randint(profile.scroll_steps_min, profile.scroll_steps_max)
    logger.debug("Human behavior scroll profile '{}' with {} steps", profile.name, steps)
    for index in range(steps):
        delta = random.randint(profile.scroll_delta_min, profile.scroll_delta_max)
        if index and index % 3 == 0:
            delta = -max(profile.micro_scroll_delta, delta // 3)
        await page.mouse.wheel(0, delta)
        await human_pause(page, profile)


async def hover_product_cards(
    page: Any,
    cards: Iterable[Any],
    profile: HumanBehaviorProfile,
) -> None:
    """Move over several product cards with small pauses and micro-scrolls."""
    hovered = 0
    for card in cards:
        if hovered >= profile.hover_cards:
            break
        try:
            box = await card.bounding_box()
        except Exception as exc:
            logger.debug("Card hover skipped: {}", exc)
            continue
        if not box:
            continue

        x = float(box["x"]) + float(box["width"]) * random.uniform(0.35, 0.65)
        y = float(box["y"]) + float(box["height"]) * random.uniform(0.35, 0.65)
        steps = random.randint(profile.mouse_move_steps_min, profile.mouse_move_steps_max)
        await page.mouse.move(x, y, steps=steps)
        await human_pause(page, profile, factor=0.7)
        if hovered % 2 == 1:
            await page.mouse.wheel(0, random.randint(40, profile.micro_scroll_delta))
            await human_pause(page, profile, factor=0.5)
        hovered += 1
