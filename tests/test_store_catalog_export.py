from scripts.export_store_catalog import build_store_export_payload, get_store_export_backend


def test_get_store_export_backend_returns_pyaterochka_backend() -> None:
    backend = get_store_export_backend("pyaterochka")

    assert backend.shop == "pyaterochka"
    assert backend.intent == "fish_catalog"


async def test_build_store_export_payload_runs_backend_categories() -> None:
    calls: list[str] = []

    async def fake_discover(*, category_name: str, listen_seconds: int, headless: bool | str | None, manual_wait: bool):
        calls.append(category_name)
        if category_name == "Рыба":
            return {
                "shop": "pyaterochka",
                "category": "Рыба",
                "category_url": "https://example.test/fish",
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
                        "4023639": "https://example.test/product/treska--4023639/",
                    }
                },
                "attempt": {"status": "ok", "reason": "product_payload_captured"},
            }
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "attempt": {"status": "empty", "reason": "no_product_payload"},
        }

    backend = get_store_export_backend("pyaterochka")
    payload = await build_store_export_payload(
        backend=backend,
        category_name="Рыба",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            "Рыба": "https://example.test/fish",
            "Морепродукты": "https://example.test/seafood",
        },
        discover_func=fake_discover,
    )

    assert calls == ["Рыба", "Морепродукты"]
    assert payload["shop"] == "pyaterochka"
    assert payload["intent"] == "fish_catalog"
    assert payload["products_count"] == 1
    assert payload["categories"] == ["Рыба", "Морепродукты"]
