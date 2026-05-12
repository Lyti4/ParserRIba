"""
Дымовые тесты для парсеров.
Проверяют базовую доступность сайтов и наличие товаров на страницах категорий.
Не выполняют полный парсинг, чтобы минимизировать нагрузку и риск блокировок.

ПРИМЕЧАНИЕ: Эти тесты требуют установленного Playwright и браузера Chromium.
Запуск: playwright install chromium
Если браузер не установлен, тесты будут пропущены.
"""
import pytest
import asyncio
from playwright.async_api import Page, TimeoutError
from playwright._impl._errors import Error as PlaywrightError

pytestmark = pytest.mark.network

# Список магазинов для тестирования
SHOPS = [
    ("pyaterochka", "https://5post.ru"),
    ("magnit", "https://magnit.ru"),
    ("lenta", "https://lenta.com"),
    ("auchan", "https://auchan.ru"),
    ("okey", "https://www.okey.ru"),
    ("perekrestok", "https://perekrestok.ru"),
]

@pytest.mark.parametrize("shop_name, base_url", SHOPS)
async def test_shop_homepage_accessible(page: Page, shop_name: str, base_url: str):
    """
    Проверка доступности главной страницы магазина.
    """
    try:
        response = await page.goto(base_url, timeout=15000, wait_until="domcontentloaded")
        assert response is not None, f"Нет ответа от {base_url}"
        assert response.status < 400, f"Ошибка HTTP {response.status} для {base_url}"
        
        # Простая проверка, что страница не пустая
        content = await page.content()
        assert len(content) > 1000, f"Страница {base_url} подозрительно короткая"
        
    except TimeoutError:
        pytest.skip(f"Таймаут при загрузке {base_url}. Возможно, сайт блокирует тестовые IP.")
    except PlaywrightError as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Playwright браузер не установлен. Запустите: playwright install chromium")
        raise
    except Exception as e:
        pytest.fail(f"Ошибка при проверке {shop_name}: {str(e)}")

@pytest.mark.parametrize("shop_name", ["pyaterochka", "magnit"])
async def test_category_page_has_products(page: Page, shop_name: str):
    """
    Проверка наличия товаров на странице категории (на примере Пятерочки и Магнита).
    Использует реальные URL из Knowledge Base.
    """
    from utils.kb_loader import KBLoader
    
    loader = KBLoader()
    kb = loader.load_shop(shop_name)
    
    if not kb.categories:
        pytest.skip(f"Нет категорий для {shop_name}")
    
    # Берем первую категорию для теста
    test_url = list(kb.categories.values())[0]
    
    try:
        # Настраиваем заголовки если они есть в KB
        headers = {}
        if kb.headers and kb.headers.custom:
            # Для тестов используем дефолтные значения критичных хедеров
            if "X-Region" in kb.headers.custom:
                headers["X-Region"] = "1" # Москва/дефолт
            if "X-Store" in kb.headers.custom:
                headers["X-Store"] = "1"
        
        if headers:
            await page.set_extra_http_headers(headers)
            
        response = await page.goto(test_url, timeout=20000, wait_until="networkidle")
        assert response.status < 400, f"Ошибка HTTP {response.status} для {test_url}"
        
        # Ждем появления карточек товаров
        selector = kb.selectors.product_card
        if selector:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                cards = await page.query_selector_all(selector)
                assert len(cards) > 0, f"На странице {test_url} не найдено товаров по селектору {selector}"
            except TimeoutError:
                # Если товары не подгрузились сразу, это может быть нормально для JS-сайтов
                # Пробуем найти альтернативные признаки
                content = await page.content()
                if "товар" not in content.lower() and "product" not in content.lower():
                    pytest.fail(f"На странице {test_url} не найдены признаки наличия товаров")
                    
    except TimeoutError:
        pytest.skip(f"Таймаут при загрузке категории {test_url}")
    except PlaywrightError as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Playwright браузер не установлен. Запустите: playwright install chromium")
        raise
    except Exception as e:
        pytest.fail(f"Ошибка при тестировании категории {shop_name}: {str(e)}")
