from models.schemas import Product
from utils.product_storage import ProductStorage


def _build_product(*, price: float, in_stock: bool = True) -> Product:
    return Product(
        id="4023639",
        name="Треска",
        price=price,
        image_url="https://img.example/4023639.webp",
        product_link="https://5ka.ru/product/treska--4023639/",
        category="Рыба",
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
            "name": "Треска",
            "product_link": "https://5ka.ru/product/treska--4023639/",
            "image_url": "https://img.example/4023639.webp",
            "category": "Рыба",
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
                name="Горбуша",
                price=519.99,
                image_url="https://img.example/4015936.webp",
                product_link="https://5ka.ru/product/gorbusha--4015936/",
                category="Рыба",
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
                name="Горбуша",
                price=519.99,
                image_url="https://img.example/4015936.webp",
                product_link="https://5ka.ru/product/gorbusha--4015936/",
                category="Рыба",
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
            "name": "Треска",
            "previous_price": 999.99,
            "current_price": 899.99,
        }
    ]
    assert report["changed_availability"] == [
        {
            "product_id": "4023639",
            "name": "Треска",
            "previous_in_stock": True,
            "current_in_stock": False,
        }
    ]
