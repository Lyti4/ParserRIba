"""
Тесты для проверки целостности Knowledge Base.
"""
import os
import pytest
from utils.kb_loader import KBLoader

class TestKnowledgeBase:
    """Тесты для валидации файлов базы знаний."""

    @pytest.fixture
    def loader(self):
        return KBLoader()

    @pytest.fixture
    def shops(self):
        return ["pyaterochka", "magnit", "lenta", "auchan", "okey", "perekrestok"]

    def test_kb_directory_exists(self):
        """Проверка существования директории knowledge_base."""
        assert os.path.exists("knowledge_base"), "Директория knowledge_base не найдена"

    def test_template_exists(self, loader):
        """Проверка существования шаблона."""
        assert os.path.exists("knowledge_base/template.md"), "Шаблон template.md не найден"

    @pytest.mark.parametrize("shop_name", ["pyaterochka", "magnit", "lenta", "auchan", "okey", "perekrestok"])
    def test_shop_file_exists(self, shop_name):
        """Проверка существования файлов для каждого магазина."""
        path = f"knowledge_base/{shop_name}.md"
        assert os.path.exists(path), f"Файл {path} не найден"

    @pytest.mark.parametrize("shop_name", ["pyaterochka", "magnit", "lenta", "auchan", "okey", "perekrestok"])
    def test_shop_config_loading(self, loader, shop_name):
        """Проверка загрузки конфигурации для каждого магазина."""
        kb = loader.load_shop(shop_name)
        assert kb is not None, f"Не удалось загрузить конфиг для {shop_name}"
        assert kb.name.lower() == shop_name, f"Имя магазина не совпадает: {kb.name}"

    @pytest.mark.parametrize("shop_name", ["pyaterochka", "magnit", "lenta", "auchan", "okey", "perekrestok"])
    def test_shop_has_categories(self, loader, shop_name):
        """Проверка наличия категорий у каждого магазина."""
        kb = loader.load_shop(shop_name)
        assert len(kb.categories) > 0, f"У магазина {shop_name} нет категорий"

    @pytest.mark.parametrize("shop_name", ["pyaterochka", "magnit", "lenta", "auchan", "okey", "perekrestok"])
    def test_shop_has_selectors(self, loader, shop_name):
        """Проверка наличия селекторов у каждого магазина."""
        kb = loader.load_shop(shop_name)
        assert kb.selectors.product_card is not None, f"У магазина {shop_name} нет селектора product_card"
        assert kb.selectors.product_name is not None, f"У магазина {shop_name} нет селектора product_name"
        assert kb.selectors.price_current is not None, f"У магазина {shop_name} нет селектора price_current"

    def test_perekrestok_requires_playwright(self, loader):
        """Проверка того, что Перекресток требует Playwright."""
        kb = loader.load_shop("perekrestok")
        assert kb.recommended_tool == "playwright", "Перекресток должен использовать Playwright"

    def test_lenta_requires_region_header(self, loader):
        """Проверка требования X-Region для Ленты."""
        kb = loader.load_shop("lenta")
        # Проверяем наличие заметки о регионе или хедера
        has_region_note = any("region" in note.lower() for note in kb.notes)
        has_region_header = "X-Region" in str(kb.headers.custom) if kb.headers.custom else False
        assert has_region_note or has_region_header, "Лента должна требовать X-Region"
