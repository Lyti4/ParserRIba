import asyncio
from pathlib import Path

from models.schemas import Product
from models.task_actor import RunManifest
from utils.local_task_registry import list_local_tasks, run_local_task
from utils.product_storage import ProductStorage


async def test_local_task_registry_runs_pyaterochka_export_task(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    async def fake_discover(*, category_name: str, listen_seconds: int, headless: bool | str | None, manual_wait: bool):
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [
                {
                    "plu": 4023639,
                    "name": "\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0",
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

    manifest = await run_local_task(
        "pyaterochka_fish_export",
        {
            "category": "\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
            "attempts": 1,
            "listen_seconds": 1,
            "manual_wait": False,
            "headless": True,
        },
        root_dir=tmp_path,
        discover_func=fake_discover,
    )

    assert isinstance(manifest, RunManifest)
    assert manifest.task_name == "pyaterochka_catalog_export"
    assert manifest.shop == "pyaterochka"
    assert manifest.intent == "fish_catalog"
    assert manifest.status == "ok"
    assert manifest.summary["products_count"] == 1
    assert manifest.summary["backend"] == "pyaterochka"
    assert Path(manifest.artifact_paths["json_path"]).exists()
    assert Path(manifest.artifact_paths["db_path"]).exists()
    assert Path(manifest.artifact_paths["manifest_path"]).exists()


async def test_local_task_registry_runs_pyaterochka_wine_export_task(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": f"https://example.test/{category_name}",
            "raw_product_items": [
                {
                    "plu": 4225897,
                    "name": "\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                    "prices": {"regular": "699.99"},
                    "image_links": [{"url": "https://img.example/4225897.webp"}],
                    "is_available": True,
                },
                {
                    "plu": 4225898,
                    "name": "\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 \u0420\u0451\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5 OddBird Spumante Veneto \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                    "prices": {"regular": "899.99"},
                    "image_links": [{"url": "https://img.example/4225898.webp"}],
                    "is_available": True,
                },
            ],
            "dom_link_evidence": {
                "links_by_id": {
                    "4225897": "https://example.test/product/wine--4225897/",
                    "4225898": "https://example.test/product/wine--4225898/",
                }
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    manifest = await run_local_task(
        "pyaterochka_wine_export",
        {
            "category": "\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455",
            "attempts": 1,
            "listen_seconds": 1,
            "manual_wait": False,
            "headless": True,
        },
        root_dir=tmp_path,
        discover_func=fake_discover,
    )

    assert isinstance(manifest, RunManifest)
    assert manifest.task_name == "pyaterochka_wine_export"
    assert manifest.shop == "pyaterochka"
    assert manifest.intent == "wine_catalog"
    assert manifest.status == "ok"
    assert manifest.summary["products_count"] == 1
    style_counts = manifest.summary["export_summary"]["wine_breakdown"]["style_counts"]
    assert len(style_counts) == 1
    assert list(style_counts.values()) == [1]
    assert Path(manifest.artifact_paths["json_path"]).exists()
    assert Path(manifest.artifact_paths["db_path"]).exists()
    assert Path(manifest.artifact_paths["manifest_path"]).exists()


def test_local_task_registry_lists_export_and_onboarding_tasks() -> None:
    tasks = list_local_tasks()

    assert tasks == [
        "site_onboarding_discovery",
        "store_catalog_export",
        "store_report_export",
        "store_report_filter_options",
    ]
    assert "store_report_export" in tasks
    assert "store_report_filter_options" in tasks
    assert "site_onboarding_discovery" in tasks


async def test_local_task_registry_runs_onboarding_discovery_task(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence, SiteProfileVersion
    from utils.catalog_tree_discovery.runner import CatalogTreeDiscoveryRunResult

    original_probe = site_onboarding._run_catalog_research_sync

    def fake_probe(*args, **kwargs):
        del kwargs
        assert args[1] is None
        return CatalogTreeDiscoveryRunResult(
            profile=SiteProfileVersion(
                profile_id="profile:unknown-store_example",
                version_id="version-1",
                shop_slug="unknown-store_example",
                site_url="https://unknown-store.example/catalog",
                run_id="run-1",
                primary_root_ids=["category-1"],
                nodes=[],
                edges=[],
                notes=[],
            ),
            phase_events=[],
            streamed_categories=["Рыба"],
            current_phase="build_tree",
            mode="live",
            partial=False,
            catalog_discovery=CatalogDiscoveryResult(
                reachable=True,
                status_code=200,
                final_url="https://unknown-store.example/catalog",
                surface_type="category_tree",
                category_links=[
                    CategoryEvidence(name="Рыба", url="https://unknown-store.example/catalog/fish"),
                ],
            ),
            limits={"max_repeat_urls": 3, "max_empty_branches": 5, "max_discovery_depth": 8},
        )

    site_onboarding._run_catalog_research_sync = fake_probe
    try:
        manifest = await run_local_task(
            "site_onboarding_discovery",
            {
                "site_url": "https://unknown-store.example",
                "intent": "fish_catalog",
                "selected_categories": ["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0"],
            },
            root_dir=tmp_path,
        )
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert manifest.task_name == "site_onboarding_discovery"
    assert manifest.shop == "unknown-store_example"
    assert manifest.intent == "fish_catalog"
    assert manifest.status == "discovery_only"
    assert manifest.summary["category_count"] == 1
    assert manifest.summary["selected_categories"] == ["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0"]
    assert Path(manifest.artifact_paths["session_state_path"]).exists()


async def test_local_task_registry_runs_known_site_onboarding_outside_active_event_loop(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence, SiteProfileVersion
    from utils.catalog_tree_discovery.runner import CatalogTreeDiscoveryRunResult

    original_probe = site_onboarding._run_catalog_research_sync

    def fake_probe(*args, **kwargs):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return CatalogTreeDiscoveryRunResult(
                profile=SiteProfileVersion(
                    profile_id="profile:pyaterochka",
                    version_id="version-1",
                    shop_slug="pyaterochka",
                    site_url="https://5ka.ru/catalog",
                    run_id="run-1",
                    primary_root_ids=["category-1"],
                    nodes=[],
                    edges=[],
                    notes=[],
                ),
                phase_events=[],
                streamed_categories=["Рыба"],
                current_phase="build_tree",
                mode="live",
                partial=False,
                catalog_discovery=CatalogDiscoveryResult(
                    reachable=True,
                    status_code=200,
                    final_url="https://5ka.ru/catalog",
                    surface_type="category_tree",
                    category_links=[
                        CategoryEvidence(name="Рыба", url="https://5ka.ru/catalog/ryba--251C13077/"),
                    ],
                ),
                limits={"max_repeat_urls": 3, "max_empty_branches": 5, "max_discovery_depth": 8},
            )
        raise AssertionError("browser discovery ran inside the active asyncio loop")

    site_onboarding._run_catalog_research_sync = fake_probe
    try:
        manifest = await run_local_task(
            "site_onboarding_discovery",
            {
                "site_url": "https://5ka.ru/",
                "intent": "fish_catalog",
                "selected_categories": [],
                "headless": True,
                "manual_wait": False,
                "listen_seconds": 1,
            },
            root_dir=tmp_path,
        )
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert manifest.task_name == "site_onboarding_discovery"
    assert manifest.status == "runtime_ready"
    assert manifest.summary["category_count"] == 1
    assert manifest.summary["active_profile_id"] == "profile:pyaterochka"
    assert manifest.summary["active_profile_version_id"] == "version-1"
    assert manifest.summary["streamed_categories"] == ["Рыба"]
    assert manifest.summary["current_phase"] == "build_tree"
    assert manifest.artifact_paths["profile_snapshot_path"].endswith("version-1.json")


async def test_local_task_registry_runs_store_report_export_task(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    storage = ProductStorage(tmp_path / "data" / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="4225897",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/4225897.webp",
                product_link="https://5ka.ru/product/vino-free-feather--4225897/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
            Product(
                id="4225898",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 OddBird Spumante \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/4225898.webp",
                product_link="https://5ka.ru/product/vino-oddbird--4225898/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "OddBird",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
        ],
    )

    manifest = await run_local_task(
        "store_report_export",
        {
            "selection": {
                "shop": "pyaterochka",
                "intent": "wine_catalog",
                "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            },
            "filters": {"suppliers": ["Free Feather"]},
            "output_name": "wine_free_feather",
        },
        root_dir=tmp_path,
    )

    assert manifest.task_name == "store_report_export"
    assert manifest.shop == "pyaterochka"
    assert manifest.intent == "wine_catalog"
    assert manifest.status == "ok"
    assert manifest.summary["products_count"] == 1
    assert manifest.summary["categories"] == ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"]
    assert Path(manifest.artifact_paths["excel_path"]).name == "wine_free_feather.xlsx"
    assert Path(manifest.artifact_paths["excel_path"]).exists()


async def test_local_task_registry_runs_store_report_filter_options_task(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    storage = ProductStorage(tmp_path / "data" / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="4225897",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/4225897.webp",
                product_link="https://5ka.ru/product/vino-free-feather--4225897/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
            Product(
                id="4225898",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 OddBird Spumante \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/4225898.webp",
                product_link="https://5ka.ru/product/vino-oddbird--4225898/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "OddBird",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
        ],
    )

    manifest = await run_local_task(
        "store_report_filter_options",
        {
            "selection": {
                "shop": "pyaterochka",
                "intent": "wine_catalog",
                "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            },
            "filters": {},
            "output_name": "",
        },
        root_dir=tmp_path,
    )

    assert manifest.task_name == "store_report_filter_options"
    assert manifest.shop == "pyaterochka"
    assert manifest.intent == "wine_catalog"
    assert manifest.status == "ok"
    assert manifest.summary["products_count"] == 2
    assert manifest.summary["available_filters"]["suppliers"] == ["Free Feather", "OddBird"]
    assert manifest.summary["available_filter_counts"]["suppliers"] == {
        "Free Feather": 1,
        "OddBird": 1,
    }


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
