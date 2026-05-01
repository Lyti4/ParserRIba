"""
Конфигурация для интеграционных тестов.
"""
import pytest
import asyncio
from playwright.async_api import async_playwright

@pytest.fixture(scope="session")
def event_loop():
    """Создание экземпляра цикла событий для сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser():
    """Фикстура для запуска браузера Playwright."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

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
