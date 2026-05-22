from utils.category_intents import (
    get_category_intent_resolver,
    resolve_fish_catalog_categories,
    resolve_wine_catalog_categories,
)


def test_resolve_fish_catalog_categories_defaults_without_kb() -> None:
    assert resolve_fish_catalog_categories("Рыба") == [
        "Рыба",
        "Морепродукты",
        "Икра и закуски",
        "Котлеты и фарш",
    ]


def test_resolve_fish_catalog_categories_prefers_compound_category() -> None:
    available = {
        "Рыба и морепродукты": "https://example.test/fish-seafood",
        "Икра и рыбные деликатесы": "https://example.test/caviar",
        "Котлеты и фарш": "https://example.test/fish-mince",
        "Мясо": "https://example.test/meat",
    }

    assert resolve_fish_catalog_categories("Рыба", available) == [
        "Рыба и морепродукты",
        "Икра и рыбные деликатесы",
        "Котлеты и фарш",
    ]


def test_resolve_fish_catalog_categories_expands_split_categories() -> None:
    available = {
        "Рыба": "https://example.test/fish",
        "Морепродукты": "https://example.test/seafood",
        "Икра и закуски": "https://example.test/caviar",
        "Котлеты и фарш": "https://example.test/fish-mince",
        "Мясо": "https://example.test/meat",
    }

    assert resolve_fish_catalog_categories("Рыба", available) == [
        "Рыба",
        "Морепродукты",
        "Икра и закуски",
        "Котлеты и фарш",
    ]


def test_resolve_fish_catalog_categories_preserves_direct_request() -> None:
    available = {
        "Рыба": "https://example.test/fish",
        "Морепродукты": "https://example.test/seafood",
        "Икра и закуски": "https://example.test/caviar",
    }

    assert resolve_fish_catalog_categories("Морепродукты", available) == ["Морепродукты"]


def test_resolve_fish_catalog_categories_excludes_non_fish_delicacies() -> None:
    available = {
        "Рыба, икра, морепродукты": "https://example.test/fish",
        "Колбаса, мясные деликатесы": "https://example.test/meat-deli",
        "Икра и закуски": "https://example.test/caviar",
    }

    assert resolve_fish_catalog_categories("Рыба", available) == [
        "Рыба, икра, морепродукты",
        "Икра и закуски",
    ]


def test_get_category_intent_resolver_returns_fish_catalog() -> None:
    resolver = get_category_intent_resolver("fish_catalog")

    assert resolver("Рыба") == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]


def test_resolve_wine_catalog_categories_defaults_without_kb() -> None:
    assert resolve_wine_catalog_categories("Вино") == ["Вино"]


def test_resolve_wine_catalog_categories_includes_all_matching_wine_branches() -> None:
    available = {
        "Безалкогольное вино": "https://example.test/non-alcoholic-wine",
        "Вино тихое": "https://example.test/still-wine",
        "Вино игристое": "https://example.test/sparkling-wine",
        "Шампанское": "https://example.test/champagne",
        "Винный напиток игристый": "https://example.test/sparkling-drink",
        "Виски": "https://example.test/whisky",
    }

    assert resolve_wine_catalog_categories("Вино", available) == [
        "Безалкогольное вино",
        "Вино тихое",
        "Вино игристое",
        "Шампанское",
        "Винный напиток игристый",
    ]


def test_resolve_wine_catalog_categories_keeps_mixed_parent_surface_when_present() -> None:
    available = {
        "Пиво, вино, энергетики": "https://example.test/mixed-parent",
        "Безалкогольное вино": "https://example.test/non-alcoholic-wine",
    }

    assert resolve_wine_catalog_categories("Вино", available) == [
        "Безалкогольное вино",
        "Пиво, вино, энергетики",
    ]


def test_get_category_intent_resolver_returns_wine_catalog() -> None:
    resolver = get_category_intent_resolver("wine_catalog")

    assert resolver("Вино", {"Безалкогольное вино": "https://example.test/non-alcoholic-wine"}) == [
        "Безалкогольное вино"
    ]
