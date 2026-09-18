import sqlite3

from models.catalog_discovery import DiscoveryNode, SiteProfileVersion
from models.onboarding import ArtifactPaths, OnboardingResult
from models.schemas import Product
from utils.discovery_profile_repository import SQLiteDiscoveryProfileRepository
from utils.onboarding_storage import OnboardingStorage
from utils.product_storage import ProductStorage


def _build_product(*, price: float, in_stock: bool = True) -> Product:
    return Product(
        id="4023639",
        name="\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0",
        price=price,
        image_url="https://img.example/4023639.webp",
        product_link="https://5ka.ru/product/treska--4023639/",
        category="\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
        in_stock=in_stock,
    )


def test_product_storage_upserts_current_product_state(tmp_path) -> None:
    store = ProductStorage(tmp_path / "products.db")

    store.save_products("pyaterochka", [_build_product(price=999.99, in_stock=True)])
    store.save_products("pyaterochka", [_build_product(price=899.99, in_stock=False)])

    current = store.list_products("pyaterochka")

    assert current == [
        {
            "store": "pyaterochka",
            "product_id": "4023639",
            "name": "\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0",
            "product_link": "https://5ka.ru/product/treska--4023639/",
            "image_url": "https://img.example/4023639.webp",
            "category": "\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
            "subcategory": "",
            "in_stock": False,
            "current_price": 899.99,
            "old_price": None,
            "unit_price": None,
            "currency": "RUB",
        }
    ]


def test_product_storage_appends_price_history(tmp_path) -> None:
    store = ProductStorage(tmp_path / "products.db")

    store.save_products("pyaterochka", [_build_product(price=999.99, in_stock=True)])
    store.save_products("pyaterochka", [_build_product(price=899.99, in_stock=False)])

    history = store.list_price_history("pyaterochka", "4023639")

    assert len(history) == 2
    assert history[0]["current_price"] == 999.99
    assert history[0]["in_stock"] is True
    assert history[1]["current_price"] == 899.99
    assert history[1]["in_stock"] is False


def test_product_storage_reports_latest_snapshot_changes(tmp_path) -> None:
    store = ProductStorage(tmp_path / "products.db")

    store.save_products(
        "pyaterochka",
        [
            _build_product(price=999.99, in_stock=True),
            Product(
                id="4015936",
                name="\u0420\u201c\u0420\u0455\u0421\u0402\u0420\u00b1\u0421\u0453\u0421\u20ac\u0420\u00b0",
                price=519.99,
                image_url="https://img.example/4015936.webp",
                product_link="https://5ka.ru/product/gorbusha--4015936/",
                category="\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
                in_stock=True,
            ),
        ],
    )
    store.save_products(
        "pyaterochka",
        [
            _build_product(price=899.99, in_stock=False),
            Product(
                id="4015936",
                name="\u0420\u201c\u0420\u0455\u0421\u0402\u0420\u00b1\u0421\u0453\u0421\u20ac\u0420\u00b0",
                price=519.99,
                image_url="https://img.example/4015936.webp",
                product_link="https://5ka.ru/product/gorbusha--4015936/",
                category="\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
                in_stock=True,
            ),
        ],
    )

    report = store.latest_snapshot_report("pyaterochka")

    assert report["products_count"] == 2
    assert report["latest_snapshot_at"]
    assert report["previous_snapshot_at"]
    assert report["changed_prices"] == [
        {
            "product_id": "4023639",
            "name": "\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0",
            "previous_price": 999.99,
            "current_price": 899.99,
        }
    ]
    assert report["changed_availability"] == [
        {
            "product_id": "4023639",
            "name": "\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0",
            "previous_in_stock": True,
            "current_in_stock": False,
        }
    ]


def test_product_storage_saves_and_loads_onboarding_session(tmp_path) -> None:
    store = OnboardingStorage(tmp_path / "products.db")
    session = OnboardingResult(
        session_id="session-1",
        shop_slug="pyaterochka",
        site_url="https://5ka.ru",
        intent="fish_catalog",
        status="runtime_ready",
        selected_categories=["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0", "\u0420\u045a\u0420\u0455\u0421\u0402\u0420\u00b5\u0420\u0457\u0421\u0402\u0420\u0455\u0420\u0491\u0421\u0453\u0420\u0454\u0421\u201a\u0421\u2039"],
        artifact_paths=ArtifactPaths(session_state_path=str(tmp_path / "session.json")),
    )

    store.save_onboarding_session(session)
    saved = store.get_onboarding_session("session-1")

    assert saved["session_id"] == "session-1"
    assert saved["status"] == "runtime_ready"
    assert saved["selected_categories"] == ["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0", "\u0420\u045a\u0420\u0455\u0421\u0402\u0420\u00b5\u0420\u0457\u0421\u0402\u0420\u0455\u0420\u0491\u0421\u0453\u0420\u0454\u0421\u201a\u0421\u2039"]
    assert saved["schema_version"] == 1


def test_product_storage_initializes_discovery_profile_tables(tmp_path) -> None:
    db_path = tmp_path / "products.db"
    store = ProductStorage(db_path)

    store.initialize()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "discovery_profiles" in tables
    assert "discovery_profile_versions" in tables


def test_onboarding_storage_reads_latest_profile_metadata(tmp_path) -> None:
    db_path = tmp_path / "products.db"
    ProductStorage(db_path).initialize()
    repository = SQLiteDiscoveryProfileRepository(db_path)
    repository.save_profile_version(
        SiteProfileVersion(
            profile_id="profile-1",
            version_id="version-2",
            shop_slug="pyaterochka",
            site_url="https://5ka.ru",
            run_id="run-2",
            primary_root_ids=["fish"],
            nodes=[DiscoveryNode(node_id="fish", label_ru="Рыба")],
            notes=["latest"],
        )
    )

    metadata = OnboardingStorage(db_path).get_latest_profile_metadata("pyaterochka", "https://5ka.ru")

    assert metadata["profile_id"] == "profile-1"
    assert metadata["profile_version_id"] == "version-2"
    assert metadata["updated_at"]
