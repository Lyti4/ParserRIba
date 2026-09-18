import subprocess
import sys
from pathlib import Path

import pytest

from scripts.export_store_catalog import build_store_export_payload, get_store_export_backend
from utils.store_export_runtime import write_store_export


def test_store_catalog_registry_import_does_not_import_pyaterochka_adapter() -> None:
    code = (
        "import sys; "
        "import utils.store_catalog_registry; "
        "blocked = {'stores.pyaterochka.product_export', 'utils.pyaterochka_catalog_capture'} & set(sys.modules); "
        "raise SystemExit(1 if blocked else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0


def test_get_store_export_backend_returns_pyaterochka_backend() -> None:
    backend = get_store_export_backend("pyaterochka", "fish_catalog")

    assert backend.shop == "pyaterochka"
    assert backend.intent == "fish_catalog"


def test_get_store_export_backend_returns_pyaterochka_wine_backend() -> None:
    backend = get_store_export_backend("pyaterochka", "wine_catalog")

    assert backend.shop == "pyaterochka"
    assert backend.intent == "wine_catalog"
    assert isinstance(backend.default_category, str)
    assert backend.default_category.strip()


def test_get_store_export_backend_fails_closed_for_unknown_store() -> None:
    with pytest.raises(ValueError, match="Unsupported store export backend"):
        get_store_export_backend("demo_store", "demo_catalog")


def test_get_store_export_backend_fails_closed_for_unknown_intent() -> None:
    with pytest.raises(ValueError, match="Unsupported store export backend"):
        get_store_export_backend("pyaterochka", "unknown_catalog")


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
                "site_filter_facets": {"fat": ["12%", "15%"]},
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

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
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
    assert payload["site_filter_facets"] == {"fat": ["12%", "15%"]}


async def test_build_store_export_payload_can_skip_intent_expansion() -> None:
    calls: list[str] = []
    explicit_category = "Рыба"

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        calls.append(category_name)
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "attempt": {"status": "empty", "reason": "no_product_payload"},
        }

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name=explicit_category,
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            explicit_category: "https://example.test/fish",
            "Морепродукты": "https://example.test/seafood",
        },
        discover_func=fake_discover,
        expand_intent=False,
    )

    assert calls == [explicit_category]
    assert payload["categories"] == [explicit_category]


async def test_build_store_export_payload_reports_rejected_raw_items() -> None:
    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        del listen_seconds, headless, manual_wait
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [{"plu": 1, "name": "Broken", "prices": {}}],
            "dom_link_evidence": {"links_by_id": {}},
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name="Broken",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={},
        discover_func=fake_discover,
        expand_intent=False,
    )

    assert payload["products_count"] == 0
    assert payload["attempt"]["reason"] == "product_items_rejected"
    assert payload["capture_diagnostics"][0]["raw_product_items"] == 1
    assert payload["capture_diagnostics"][0]["built_products"] == 0


async def test_build_store_export_payload_surfaces_captcha_reason() -> None:
    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        del listen_seconds, headless, manual_wait
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "captured_product_urls": [],
            "attempt": {"status": "blocked", "reason": "pyaterochka_captcha"},
        }

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name="Blocked",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={},
        discover_func=fake_discover,
        expand_intent=False,
    )

    assert payload["products_count"] == 0
    assert payload["attempt"]["reason"] == "pyaterochka_captcha"
    assert payload["capture_diagnostics"][0]["capture_reason"] == "pyaterochka_captcha"


async def test_build_store_export_payload_surfaces_proxy_reason() -> None:
    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        del listen_seconds, headless, manual_wait
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "captured_product_urls": [],
            "attempt": {"status": "blocked", "reason": "proxy_failure"},
        }

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name="Blocked",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={},
        discover_func=fake_discover,
        expand_intent=False,
    )

    assert payload["products_count"] == 0
    assert payload["attempt"]["reason"] == "proxy_failure"
    assert payload["capture_diagnostics"][0]["capture_reason"] == "proxy_failure"


async def test_build_store_export_payload_passes_explicit_category_url() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_discover(
        *,
        category_name: str,
        category_url: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        del listen_seconds, headless, manual_wait
        calls.append((category_name, category_url))
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": category_url,
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "attempt": {"status": "empty", "reason": "no_product_payload"},
        }

    backend = get_store_export_backend("pyaterochka", "fish_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name="Завтраки",
        category_url="https://5ka.ru/catalog/zavtraki--251C12891/",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={"Рыба": "https://example.test/fish"},
        discover_func=fake_discover,
        expand_intent=False,
    )

    assert calls == [("Завтраки", "https://5ka.ru/catalog/zavtraki--251C12891/")]
    assert payload["category_url"] == "https://5ka.ru/catalog/zavtraki--251C12891/"


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
        "site_filter_facets": {"brand": ["Море"]},
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
    assert payload["run_manifest"]["summary"]["site_filter_facets"] == {"brand": ["Море"]}
    assert Path(payload["excel_path"]).exists()


def test_write_store_export_manifest_includes_products_for_live_launcher_state(tmp_path: Path) -> None:
    payload = {
        "shop": "pyaterochka",
        "intent": "fish_catalog",
        "category": "Сыр",
        "categories": ["Сыр"],
        "attempts_requested": 1,
        "attempts_used": 1,
        "attempt": {"status": "ok", "reason": "product_payload_captured"},
        "products_count": 1,
        "products": [
            {
                "id": "cheese-1",
                "name": "Сыр тестовый",
                "category": "Сыр",
                "price": {"current": 199.99},
                "in_stock": True,
                "product_link": "https://5ka.ru/product/cheese--1/",
                "raw_data": {"supplier": "Cheese Supplier", "product_type": "Сыр"},
            }
        ],
        "site_filter_facets": {"product_type": ["Сыр"]},
        "exported_at": "2026-06-04T20:00:00",
    }

    write_store_export(payload, tmp_path, task_name="pyaterochka_catalog_export")

    summary = payload["run_manifest"]["summary"]
    assert summary["products_count"] == 1
    assert summary["products"] == payload["products"]
    assert summary["found_filters"] == {"product_type": {"Сыр": 1}}
