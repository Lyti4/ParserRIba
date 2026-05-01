"""
Тесты для Pydantic моделей данных.
"""
import pytest
from datetime import datetime
from models.schemas import Product, ShopInfo

class TestProductModel:
    """Тесты для модели Product."""

    def test_create_valid_product(self):
        """Создание валидного продукта."""
        product = Product(
            name="Лосось атлантический",
            price=599.99,
            unit_price=1199.98,
            weight="500г",
            link="https://example.com/product/123",
            image="https://example.com/img.jpg",
            shop="pyaterochka",
            category="fish",
            scraped_at=datetime.now()
        )
        assert product.name == "Лосось атлантический"
        assert product.price == 599.99
        assert product.shop == "pyaterochka"

    def test_product_price_validation(self):
        """Проверка валидации цены (не может быть отрицательной)."""
        with pytest.raises(ValueError):
            Product(
                name="Товар",
                price=-100,
                unit_price=200,
                weight="1кг",
                link="https://example.com",
                shop="test",
                category="test",
                scraped_at=datetime.now()
            )

    def test_product_optional_fields(self):
        """Проверка опциональных полей."""
        product = Product(
            name="Товар без скидки",
            price=100,
            unit_price=100,
            weight="1шт",
            link="https://example.com",
            shop="test",
            category="test",
            scraped_at=datetime.now()
            # old_price, discount, brand, volume не указаны
        )
        assert product.old_price is None
        assert product.discount is None
        assert product.brand is None

    def test_product_url_validation(self):
        """Проверка валидации URL."""
        # Playwright и Pydantic могут иметь разные требования к URL
        # Здесь проверяем базовую структуру
        product = Product(
            name="Товар",
            price=100,
            unit_price=100,
            weight="1шт",
            link="https://valid-url.com/path?query=1",
            shop="test",
            category="test",
            scraped_at=datetime.now()
        )
        assert "https://" in product.link

class TestShopInfoModel:
    """Тесты для модели ShopInfo."""

    def test_create_shop_info(self):
        """Создание информации о магазине."""
        shop = ShopInfo(
            name="Пятерочка",
            code="pyaterochka",
            base_url="https://5post.ru",
            active=True
        )
        assert shop.name == "Пятерочка"
        assert shop.code == "pyaterochka"
        assert shop.active is True

    def test_shop_info_inactive(self):
        """Магазин может быть неактивным."""
        shop = ShopInfo(
            name="Закрытый магазин",
            code="closed",
            base_url="https://example.com",
            active=False
        )
        assert shop.active is False
