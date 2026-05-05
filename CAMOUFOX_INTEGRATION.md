# Интеграция Camoufox в ParserRiba

## 🦊 Что такое Camoufox?

**Camoufox** - это модифицированный браузер Firefox с улучшенной маскировкой под реального пользователя. Он автоматически:

- Генерирует реалистичные user-agent и browser fingerprints
- Маскирует признаки автоматизации (navigator.webdriver)
- Добавляет случайные задержки и эмулирует поведение человека
- Включает встроенные аддоны для обхода детекции
- Использует меньше ресурсов чем Chromium/Playwright

## ✅ Camoufox уже установлен

Библиотека установлена через `pip install camoufox` и готова к использованию.

> **Примечание:** Для работы Camoufox требуется ~700MB свободного места для загрузки браузера при первом запуске.

## 🔧 Как использовать CamoufoxParser

### Базовый пример

```python
from parsers.camoufox_parser import CamoufoxParser

async def parse_with_camoufox():
    async with CamoufoxParser("pyaterochka", "https://5ka.ru", headless=True) as parser:
        # Загружаем страницу
        html = await parser.fetch_page_camoufox("https://5ka.ru/catalog")
        
        # Парсим товары
        products = await parser.parse_products_from_page()
        
        print(f"Найдено товаров: {len(products)}")
```

### Продвинутый пример со стратегиями

```python
from parsers.camoufox_parser import CamoufoxParser

async def advanced_parsing():
    async with CamoufoxParser(
        "magnit", 
        "https://magnit.ru", 
        headless=True,
        region="77"  # Москва
    ) as parser:
        
        # Human-like скроллинг для lazy loading
        await parser.fetch_page_camoufox(
            "https://magnit.ru/catalog",
            wait_for_selector=".product-card",
            scroll_down=True
        )
        
        # Делаем скриншот для отладки
        await parser.screenshot("/tmp/magnit_catalog.png")
        
        # Извлекаем конкретные данные
        price = await parser.extract_with_camoufox(
            "https://magnit.ru/product/123",
            ".price-value"
        )
        
        # Парсим все товары
        products = await parser.parse_products_from_page()
```

## 📊 Сравнение с Playwright

| Характеристика | Camoufox | Playwright (Chromium) |
|---------------|----------|----------------------|
| **Маскировка** | ⭐⭐⭐⭐⭐ Лучшая | ⭐⭐⭐ Хорошая |
| **Ресурсы** | ⭐⭐⭐ Меньше RAM | ⭐⭐ Больше RAM |
| **Скорость** | ⭐⭐⭐ Быстро | ⭐⭐⭐⭐ Очень быстро |
| **Fingerprints** | Реальные | Эмулированные |
| **Антидетект** | Встроенный | Требует stealth |
| **Регион РФ** | ✅ Отлично | ✅ Хорошо |

## 🎯 Когда использовать Camoufox

### Используйте Camoufox если:
- Сайт определяет Playwright/Chromium
- Сильная антибот-защита (Cloudflare, DataDome)
- Нужны реалистичные fingerprints
- Мало оперативной памяти
- Парсинг российских сайтов

### Используйте Playwright если:
- Простые сайты без защиты
- Нужна максимальная скорость
- Требуется специфичный функционал Chromium
- Camoufox не справляется

## 🔄 Интеграция в существующий код

### Вариант 1: Замена PlaywrightParser

```python
# Было
from parsers.playwright_parser import PlaywrightParser
parser = PlaywrightParser("auchan", "https://auchan.ru")

# Стало
from parsers.camoufox_parser import CamoufoxParser
parser = CamoufoxParser("auchan", "https://auchan.ru")
```

### Вариант 2: Автоматический выбор

```python
from parsers.base_parser import BaseParser

class SmartParser(BaseParser):
    async def fetch_page_smart(self, url: str):
        # Пробуем curl-cffi
        html = await self.fetch_page(url)
        
        # Если не получилось - Camoufox
        if not html:
            logger.info("🦊 Переключаюсь на Camoufox")
            return await self.fetch_page_camoufox(url)
        
        return html
```

### Вариант 3: Fallback цепочка

```python
async def robust_fetch(url: str):
    # 1. curl-cffi (быстро)
    html = await curl_fetch(url)
    if html and "captcha" not in html:
        return html
    
    # 2. Camoufox (надёжно)
    html = await camoufox_fetch(url)
    if html:
        return html
    
    # 3. Playwright (резерв)
    return await playwright_fetch(url)
```

## 🛠️ Настройки Camoufox

### Геолокация

```python
parser = CamoufoxParser(
    "store",
    "https://store.ru",
    geolocation={"latitude": 55.7558, "longitude": 37.6173}  # Москва
)
```

### Видимый режим (для отладки)

```python
parser = CamoufoxParser(
    "store",
    "https://store.ru",
    headless=False  # Показывать браузер
)
```

### Исключение аддонов (экономия памяти)

```python
parser = CamoufoxParser(
    "store",
    "https://store.ru",
    exclude_addons=["ublock-origin"]  # Не загружать uBlock
)
```

## 📝 Knowledge Base интеграция

CamoufoxParser автоматически использует селекторы и настройки из вашей Knowledge Base:

```python
# knowledge_base/pyaterochka.md должен содержать:
selectors:
  product_card: ".catalog-item"
  product_name: ".item__name"
  price_current: ".price-value"
  product_link: "a.item__link"
  product_image: "img.item__image"

anti_bot:
  requires_js: true
  has_lazy_load: true
  recommended_tool: "camoufox"
```

## 🚀 Производительность

### Потребление памяти:
- Camoufox: ~150-250 MB на экземпляр
- Playwright Chromium: ~300-500 MB на экземпляр

### Время запуска:
- Первый запуск: ~10-20 сек (загрузка браузера)
- Повторный запуск: ~2-3 сек (кэш)

### Рекомендации:
- Используйте 1-2 экземпляра одновременно
- Закрывайте браузер после использования (`async with`)
- Кэшируйте HTML для повторного парсинга

## 🔍 Отладка

### Скриншоты ошибок

```python
try:
    html = await parser.fetch_page_camoufox(url)
except Exception as e:
    await parser.screenshot(f"/tmp/error_{url.replace('/', '_')}.png")
```

### Логирование

```python
import logging
logging.getLogger('camoufox').setLevel(logging.DEBUG)
```

### Проверка маскировки

```python
await page.goto("https://bot.sannysoft.com")
await page.screenshot(path="test_result.png")
```

## ⚠️ Ограничения

1. **Место на диске**: Требуется ~700MB для браузера
2. **Первый запуск**: Долгая загрузка при первой установке
3. **Firefox only**: Некоторые сайты оптимизированы только под Chrome
4. **Асинхронность**: Только async API (нет sync версии для парсинга)

## 🆘 Troubleshooting

### Ошибка: "No space left on device"

```bash
# Очистите кэш
rm -rf /root/.cache/camoufox
rm -rf /tmp/camoufox_*

# Или установите переменную окружения
export CAMOUFOX_CACHE_DIR=/path/to/larger/disk
```

### Ошибка: "Browser failed to launch"

```python
# Попробуйте видимый режим для диагностики
parser = CamoufoxParser("store", url, headless=False)

# Или исключите тяжёлые аддоны
parser = CamoufoxParser("store", url, exclude_addons=["ublock-origin"])
```

### Сайт всё ещё детектирует бота

```python
# Увеличьте задержки
await asyncio.sleep(random.uniform(3.0, 5.0))

# Используйте human-like скроллинг
await parser.human_like_scroll()

# Добавьте больше случайности
parser = CamoufoxParser(
    "store", 
    url,
    viewport={"width": random.randint(1366, 1920), 
              "height": random.randint(768, 1080)}
)
```

## 📚 Дополнительные ресурсы

- [Официальный репозиторий Camoufox](https://github.com/daijro/camoufox)
- [Документация Playwright](https://playwright.dev/python)
- [Ваш ParserRiba репозиторий](https://github.com/Lyti4/ParserRIba)

---

**Итог:** Camoufox успешно интегрирован в ParserRiba и готов к использованию для парсинга сложных сайтов с антибот-защитой! 🎉
