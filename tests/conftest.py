"""
Конфигурация для интеграционных тестов.
"""
import pytest
import asyncio
import sys
import os

# Добавляем корень проекта в sys.path для корректного импорта модулей
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from playwright.async_api import async_playwright

# Настраиваем asyncio для pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Устанавливаем режим asyncio по умолчанию
pytestmark = pytest.mark.asyncio(scope="session")


def pytest_collection_modifyitems(config, items):
    """Skip live network smoke tests unless explicitly requested."""
    if os.environ.get("RUN_NETWORK_SMOKE") == "1":
        return

    skip_network = pytest.mark.skip(
        reason="live website smoke tests are disabled; set RUN_NETWORK_SMOKE=1 to run them"
    )
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)

@pytest.fixture(scope="session")
def event_loop_policy():
    """Используем политику событий Windows для совместимости."""
    # ИЗМЕНЕНО: Playwright запускает driver через subprocess; на Windows
    # SelectorEventLoopPolicy падает с NotImplementedError.
    return asyncio.WindowsProactorEventLoopPolicy() if sys.platform == "win32" else None

@pytest.fixture(scope="session")
async def browser():
    """Фикстура для запуска браузера Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e) or "ENOSPC" in str(e):
            pytest.skip(f"Playwright браузер не установлен или недостаточно места: {e}")
        else:
            raise

@pytest.fixture
async def context(browser):
    """Создание контекста браузера для каждого теста."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    yield context
    await context.close()

@pytest.fixture
async def page(context):
    """Создание страницы для каждого теста."""
    page = await context.new_page()
    yield page
    await page.close()
