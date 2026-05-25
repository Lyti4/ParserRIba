from scripts.export_pyaterochka_products import build_products_from_result, resolve_export_category_names


def test_resolve_export_category_names_defaults_to_fish_and_seafood() -> None:
    assert resolve_export_category_names("Рыба") == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]
    assert resolve_export_category_names("Рыба и морепродукты") == [
        "Рыба",
        "Морепродукты",
        "Икра и закуски",
        "Котлеты и фарш",
    ]
    assert resolve_export_category_names("Морепродукты") == ["Морепродукты"]


def test_resolve_export_category_names_prefers_matching_kb_categories() -> None:
    available = {
        "Рыба и морепродукты": "https://example.test/fish-seafood",
        "Икра и рыбные деликатесы": "https://example.test/caviar",
        "Котлеты и фарш": "https://example.test/fish-mince",
        "Мясо": "https://example.test/meat",
    }

    assert resolve_export_category_names("Рыба", available) == [
        "Рыба и морепродукты",
        "Икра и рыбные деликатесы",
        "Котлеты и фарш",
    ]
    assert resolve_export_category_names("Рыба и морепродукты", available) == [
        "Рыба и морепродукты",
        "Икра и рыбные деликатесы",
        "Котлеты и фарш",
    ]


def test_resolve_export_category_names_expands_split_kb_categories() -> None:
    available = {
        "Рыба": "https://example.test/fish",
        "Морепродукты": "https://example.test/seafood",
        "Икра и закуски": "https://example.test/caviar",
        "Котлеты и фарш": "https://example.test/fish-mince",
        "Мясо": "https://example.test/meat",
    }

    assert resolve_export_category_names("Рыба", available) == [
        "Рыба",
        "Морепродукты",
        "Икра и закуски",
        "Котлеты и фарш",
    ]


def test_resolve_export_category_names_keeps_fish_derived_categories() -> None:
    available = {
        "Рыба": "https://example.test/fish",
        "Морепродукты": "https://example.test/seafood",
        "Икра и рыбные деликатесы": "https://example.test/caviar",
        "Котлеты и фарш": "https://example.test/semi-finished",
    }

    assert resolve_export_category_names("Рыба", available) == [
        "Рыба",
        "Морепродукты",
        "Икра и рыбные деликатесы",
        "Котлеты и фарш",
    ]


def test_resolve_export_category_names_supports_full_wine_catalog() -> None:
    available = {
        "Безалкогольное вино": "https://example.test/non-alcoholic-wine",
        "Вино тихое": "https://example.test/still-wine",
        "Вино игристое": "https://example.test/sparkling-wine",
        "Шампанское": "https://example.test/champagne",
        "Винный напиток игристый": "https://example.test/sparkling-drink",
        "Морепродукты": "https://example.test/seafood",
    }

    assert resolve_export_category_names("Вино", available, intent="wine_catalog") == [
        "Безалкогольное вино",
        "Вино тихое",
        "Вино игристое",
        "Шампанское",
        "Винный напиток игристый",
    ]


def test_build_products_from_result_prefers_raw_capture() -> None:
    result = {
        "category": "Рыба",
        "raw_product_items": [
            {
                "plu": 4023639,
                "name": "Треска",
                "prices": {"regular": "999.99"},
                "image_links": [{"url": "https://img.example/4023639.webp"}],
                "is_available": True,
            }
        ],
        "dom_link_evidence": {
            "links_by_id": {
                "4023639": "https://5ka.ru/product/treska--4023639/",
            }
        },
        "api_first": {"samples": []},
    }

    products = build_products_from_result(result)

    assert len(products) == 1
    assert products[0].id == "4023639"
    assert str(products[0].product_link) == "https://5ka.ru/product/treska--4023639/"
