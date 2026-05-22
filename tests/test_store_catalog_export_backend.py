from pathlib import Path

from scripts.export_store_catalog import build_store_export_payload, get_store_export_backend
from utils.store_export_runtime import write_store_export


def test_get_store_export_backend_returns_pyaterochka_backend() -> None:
    backend = get_store_export_backend("pyaterochka")

    assert backend.shop == "pyaterochka"
    assert backend.intent == "fish_catalog"


def test_get_store_export_backend_returns_pyaterochka_wine_backend() -> None:
    backend = get_store_export_backend("pyaterochka", "wine_catalog")

    assert backend.shop == "pyaterochka"
    assert backend.intent == "wine_catalog"
    assert isinstance(backend.default_category, str)
    assert backend.default_category.strip()


async def test_build_store_export_payload_runs_backend_categories() -> None:
    calls: list[str] = []
    primary_category = "Рыба"

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        calls.append(category_name)
        if category_name == primary_category:
            return {
                "shop": "pyaterochka",
                "category": primary_category,
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
        category_name=primary_category,
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            primary_category: "https://example.test/fish",
            "Морепродукты": "https://example.test/seafood",
        },
        discover_func=fake_discover,
    )

    assert calls
    assert calls == payload["categories"]
    assert calls[0] == primary_category
    assert payload["shop"] == "pyaterochka"
    assert payload["intent"] == "fish_catalog"
    assert payload["products_count"] == 1
    assert payload["categories"]


def test_write_store_export_writes_run_manifest(tmp_path: Path) -> None:
    payload = {
        "shop": "pyaterochka",
        "intent": "fish_catalog",
        "category": "Рыба",
        "categories": ["Рыба"],
        "attempts_requested": 1,
        "attempts_used": 1,
        "attempt": {"status": "ok", "reason": "product_payload_captured"},
        "products_count": 0,
        "products": [],
        "exported_at": "2026-05-19T20:00:00",
    }

    export_path, db_path = write_store_export(payload, tmp_path)

    manifest_path = Path(payload["run_manifest_path"])
    assert export_path.exists()
    assert db_path == tmp_path / "products.db"
    assert db_path.exists()
    assert manifest_path.exists()
    assert payload["run_manifest"]["task_name"] == "store_catalog_export"
    assert payload["run_manifest"]["shop"] == "pyaterochka"
    assert payload["run_manifest"]["status"] == "empty"
    assert payload["run_manifest"]["summary"]["products_count"] == 0
    assert Path(payload["excel_path"]).exists()
