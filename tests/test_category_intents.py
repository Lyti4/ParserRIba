from utils.category_intents import get_category_intent_resolver, resolve_fish_catalog_categories


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


def test_get_category_intent_resolver_returns_fish_catalog() -> None:
    resolver = get_category_intent_resolver("fish_catalog")

    assert resolver("Рыба") == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]
