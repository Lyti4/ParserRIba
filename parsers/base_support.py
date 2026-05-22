"""Support helpers for legacy parser base orchestration."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from utils.kb_loader import ShopKnowledge


def resolve_category_name(url: str, kb: ShopKnowledge) -> str:
    """Resolve category name from KB mappings or URL fallback."""
    for name, category_url in kb.categories.items():
        if category_url in url or url in category_url:
            return name
    return url.rstrip("/").split("/")[-1].replace("-", " ").title()


def extract_selector_value(kb: ShopKnowledge, selector_type: str) -> Optional[str]:
    """Return the preferred selector string from KB data."""
    selector = kb.selectors.get(selector_type)
    if not selector:
        return None
    selector_value = selector.css or selector.xpath or selector.regex
    if not selector_value:
        return None

    has_pipe = " | " in selector_value or selector_value.count("|") > 2
    has_comma = "," in selector_value
    if not has_pipe and not has_comma:
        return selector_value

    selectors = _split_selector_candidates(selector_value, has_pipe=has_pipe)
    for item in selectors:
        if item and not item.startswith("^") and not item.startswith("("):
            return item
    return selectors[0] if selectors else None


def build_parser_info(kb: ShopKnowledge, region: Optional[str]) -> Dict[str, Any]:
    """Build one legacy parser info payload."""
    return {
        "shop": kb.name,
        "region": region,
        "categories": list(kb.categories.keys()),
        "selectors": dict(kb.selectors),
        "headers": kb.headers.standard | kb.headers.custom,
        "anti_bot": {
            "recommended_tool": kb.anti_bot.recommended_tool,
            "captcha_types": kb.anti_bot.captcha_types,
            "strategies": kb.anti_bot.strategies,
        },
    }


def _split_selector_candidates(selector_value: str, *, has_pipe: bool) -> list[str]:
    """Split multi-selector KB strings into ordered selector candidates."""
    if has_pipe:
        parts = re.split(r"\s*\|\s*", selector_value)
        return [item.strip() for item in parts]

    selectors: list[str] = []
    current = ""
    bracket_depth = 0
    for char in selector_value:
        if char == "[":
            bracket_depth += 1
            current += char
        elif char == "]":
            bracket_depth -= 1
            current += char
        elif char == "," and bracket_depth == 0:
            selectors.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        selectors.append(current.strip())
    return selectors
