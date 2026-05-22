"""Store-neutral category intent resolution helpers."""

from __future__ import annotations

from typing import Callable, Final

FISH_CATALOG_DEFAULT_CATEGORIES: Final[list[str]] = [
    "Рыба",
    "Морепродукты",
    "Икра и закуски",
    "Котлеты и фарш",
]
FISH_CATALOG_PRIMARY_CATEGORIES: Final[list[str]] = ["Рыба", "Морепродукты"]
FISH_CATALOG_COMPOUND_CATEGORY: Final[str] = "Рыба и морепродукты"
FISH_CATALOG_PRIMARY_KEYWORDS: Final[tuple[str, ...]] = ("рыб", "морепродукт")
FISH_CATALOG_DERIVED_KEYWORDS: Final[tuple[str, ...]] = ("икра", "закуск", "котлет", "фарш")
FISH_CATALOG_DERIVED_GROUPS: Final[tuple[tuple[str, ...], ...]] = (
    ("икра", "закуск"),
    ("котлет", "фарш"),
)

WINE_CATALOG_DEFAULT_CATEGORY: Final[str] = "Вино"
WINE_CATALOG_PRIMARY_CATEGORIES: Final[list[str]] = [
    "Вино",
    "Вино тихое",
    "Вино игристое",
    "Шампанское",
    "Безалкогольное вино",
]
WINE_CATALOG_DERIVED_CATEGORIES: Final[list[str]] = [
    "Винный напиток",
    "Винный напиток игристый",
]
WINE_CATEGORY_ORDER_RULES: Final[tuple[tuple[str, ...], ...]] = (
    ("безалкоголь", "вино"),
    ("вино", "тих"),
    ("вино", "игрист"),
    ("шампан",),
    ("винный напит", "игрист"),
    ("винный напит",),
    ("пиво", "вино"),
)

CategoryIntentResolver = Callable[[str, dict[str, str] | None], list[str]]


def resolve_fish_catalog_categories(
    category_name: str,
    available_categories: dict[str, str] | None = None,
) -> list[str]:
    """Resolve categories for the fish-and-seafood catalog intent."""
    normalized = str(category_name or "").strip()
    if not available_categories:
        if normalized in {"", "Рыба", FISH_CATALOG_COMPOUND_CATEGORY}:
            return list(FISH_CATALOG_DEFAULT_CATEGORIES)
        return [normalized]

    if normalized in {"", "Рыба", FISH_CATALOG_COMPOUND_CATEGORY}:
        exact_matches = _find_exact_category_matches(available_categories, FISH_CATALOG_PRIMARY_CATEGORIES)
        exact_compound = _find_exact_category_name(available_categories, FISH_CATALOG_COMPOUND_CATEGORY)
        keyword_matches = _find_keyword_category_names(
            available_categories,
            primary_keywords=FISH_CATALOG_PRIMARY_KEYWORDS,
            derived_keywords=FISH_CATALOG_DERIVED_KEYWORDS,
            derived_groups=FISH_CATALOG_DERIVED_GROUPS,
        )
        ordered: list[str] = []
        if exact_compound:
            ordered.append(exact_compound)
        ordered.extend(name for name in exact_matches if name not in ordered)
        ordered.extend(name for name in keyword_matches if name not in ordered)
        if ordered:
            return ordered
    return [normalized]


def resolve_wine_catalog_categories(
    category_name: str,
    available_categories: dict[str, str] | None = None,
) -> list[str]:
    """Resolve categories for the wine catalog intent."""
    normalized = str(category_name or "").strip()
    if not available_categories:
        if normalized in {"", WINE_CATALOG_DEFAULT_CATEGORY}:
            return [WINE_CATALOG_DEFAULT_CATEGORY]
        return [normalized]

    if normalized in {"", WINE_CATALOG_DEFAULT_CATEGORY}:
        ordered = _find_ordered_wine_category_names(available_categories)
        if ordered:
            return ordered
    return [normalized]


def get_category_intent_resolver(intent: str) -> CategoryIntentResolver:
    """Return resolver for a known category intent."""
    normalized = str(intent or "").strip().casefold()
    if normalized == "fish_catalog":
        return resolve_fish_catalog_categories
    if normalized == "wine_catalog":
        return resolve_wine_catalog_categories
    raise ValueError(f"Unsupported category intent: {intent}")


def _find_exact_category_name(available_categories: dict[str, str], target_name: str) -> str:
    target = target_name.casefold()
    for category_name in available_categories:
        if category_name.casefold() == target:
            return category_name
    return ""


def _find_exact_category_matches(
    available_categories: dict[str, str],
    target_names: list[str],
) -> list[str]:
    matches: list[str] = []
    for target_name in target_names:
        match = _find_exact_category_name(available_categories, target_name)
        if match and match not in matches:
            matches.append(match)
    return matches


def _find_keyword_category_names(
    available_categories: dict[str, str],
    *,
    primary_keywords: tuple[str, ...],
    derived_keywords: tuple[str, ...],
    derived_groups: tuple[tuple[str, ...], ...],
) -> list[str]:
    primary_matches: list[str] = []
    derived_matches: list[str] = []
    for category_name in available_categories:
        folded = category_name.casefold()
        if any(keyword in folded for keyword in primary_keywords):
            primary_matches.append(category_name)
            continue
        if any(keyword in folded for keyword in derived_keywords):
            derived_matches.append(category_name)

    ordered_derived: list[str] = []
    for group in derived_groups:
        for category_name in derived_matches:
            folded = category_name.casefold()
            if any(keyword in folded for keyword in group) and category_name not in ordered_derived:
                ordered_derived.append(category_name)
    return primary_matches + ordered_derived


def _find_ordered_wine_category_names(available_categories: dict[str, str]) -> list[str]:
    ordered: list[str] = []
    exact_matches = _find_exact_category_matches(
        available_categories,
        WINE_CATALOG_PRIMARY_CATEGORIES + WINE_CATALOG_DERIVED_CATEGORIES,
    )
    rule_matches = _find_categories_by_rules(available_categories, WINE_CATEGORY_ORDER_RULES)
    for category_name in rule_matches:
        if category_name not in ordered:
            ordered.append(category_name)
    for category_name in exact_matches:
        if category_name not in ordered:
            ordered.append(category_name)
    return ordered


def _find_categories_by_rules(
    available_categories: dict[str, str],
    rules: tuple[tuple[str, ...], ...],
) -> list[str]:
    ordered: list[str] = []
    for rule in rules:
        for category_name in available_categories:
            folded = category_name.casefold()
            if all(part in folded for part in rule) and category_name not in ordered:
                ordered.append(category_name)
    return ordered
