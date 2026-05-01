"""
Тесты для Pydantic моделей данных.
"""
import pytest
from datetime import datetime
from models.schemas import Product, ShopInfo, ProductPrice

class TestProductModel:
    """Тесты для модели Product."""

    def test_create_valid_product(self):
        """Создание валидного продукта с числовой ценой."""
        product = Product(
            name="Лосось атлантический",
            price=599.99,  # Передаем числом, валидатор обернет в ProductPrice
            product_link="https://example.com/product/123",
            shop="pyaterochka",
            category="fish"
        )
        assert product.name == "Лосось атлантический"
        assert isinstance(product.price, ProductPrice)
        assert product.price.current == 599.99
        assert product.shop == "pyaterochka"

    def test_create_product_with_dict_price(self):
        """Создание продукта со словарем цены."""
        product = Product(
            name="Лосось атлантический",
            price={"current": 599.99, "old": 799.99},
            product_link="https://example.com/product/123",
            shop="pyaterochka"
        )
        assert product.price.current == 599.99
        assert product.price.old == 799.99

    def test_product_optional_fields(self):
        """Проверка опциональных полей."""
        product = Product(
            name="Товар без скидки",
            price=100,
            product_link="https://example.com",
            shop="test",
            category="test"
        )
        assert product.brand is None
        assert product.dimensions is None

    def test_product_url_validation(self):
        """Проверка валидации URL."""
        product = Product(
            name="Товар",
            price=100,
            product_link="https://valid-url.com/path?query=1",
            shop="test",
            category="test"
        )
        assert "https://" in str(product.product_link)

class TestShopInfoModel:
    """Тесты для модели ShopInfo."""

    def test_create_shop_info(self):
        """Создание информации о магазине."""
        shop = ShopInfo(
            name="pyaterochka",
            display_name="Пятерочка",
            base_url="https://5post.ru"
        )
        assert shop.name == "pyaterochka"
        assert shop.display_name == "Пятерочка"
        assert shop.active is True  # default

    def test_shop_info_inactive(self):
        """Магазин может быть неактивным."""
        shop = ShopInfo(
            name="closed",
            display_name="Закрытый магазин",
            base_url="https://example.com",
            active=False
        )
        assert shop.active is False
