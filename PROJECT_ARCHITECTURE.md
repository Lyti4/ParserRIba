# ParserRiba - Архитектура и Описание Проекта

## 📋 Обзор Проекта

**ParserRiba** - это современный фреймворк для парсинга цен на рыбу и морепродукты из российских розничных сетей с продвинутой защитой от антибот-систем. Проект использует **Camoufox** (модифицированный Firefox с улучшенной маскировкой) как основной инструмент для обхода защиты сайтов.

---

## 🎯 Цели Проекта

1. **Автоматизация парсинга** товаров из крупных российских ритейлеров
2. **Обход антибот-защиты** (Cloudflare, reCAPTCHA, rate limiting)
3. **Гибкая архитектура** с поддержкой Knowledge Base для каждого магазина
4. **Масштабируемость** и лёгкость добавления новых магазинов

---

## 🏗 Архитектура Проекта

```
parser_riba_temp/
├── parsers/                    # Парсеры для каждого магазина
│   ├── __init__.py
│   ├── base_parser.py          # Базовый класс парсера
│   ├── camoufox_parser.py      # Parcer на базе Camoufox
│   ├── playwright_parser.py    # Parцер на базе Playwright (резерв)
│   ├── pyaterochka.py          # Парсер Пятерочки (основной)
│   ├── magnit.py               # Парсер Магнита
│   ├── lenta.py                # Парсер Ленты
│   ├── auchan.py               # Парсер Ашана
│   ├── okey.py                 # Парсер О'Кей
│   └── perekrestok.py          # Парсер Перекрестка
│
├── knowledge_base/             # Конфигурация для каждого магазина
│   ├── template.md             # Шаблон KB
│   ├── pyaterochka.md          # KB для Пятерочки
│   ├── magnit.md
│   ├── lenta.md
│   ├── auchan.md
│   ├── okey.md
│   └── perekrestok.md
│
├── models/                     # Pydantic модели данных
│   ├── __init__.py
│   ├── product.py              # Модель товара
│   └── schemas.py              # Общие схемы (ParseResult, CategoryInfo)
│
├── strategies/                 # Стратегии автоматизации браузера
│   ├── __init__.py
│   ├── base_strategy.py        # Базовая стратегия
│   ├── scroll_strategy.py      # Стратегия скроллинга
│   ├── pagination_strategy.py  # Стратегия пагинации
│   ├── lazy_load_strategy.py   # Стратегия lazy loading
│   └── captcha_handler.py      # Обработка капчи
│
├── policies/                   # Политики обработки ошибок
│   ├── __init__.py
│   └── engine.py               # Policy Engine
│
├── utils/                      # Утилиты
│   ├── __init__.py
│   ├── kb_loader.py            # Загрузчик Knowledge Base
│   ├── logger.py               # Настройка логирования
│   ├── export.py               # Экспорт данных (CSV, JSON)
│   └── session_manager.py      # Управление сессиями и прокси
│
├── tests/                      # Тесты
│   ├── __init__.py
│   ├── conftest.py             # pytest конфигурация
│   ├── test_models.py          # Тесты моделей
│   ├── test_kb_loader.py       # Тесты KB Loader
│   └── test_parsers_smoke.py   # Smoke тесты парсеров
│
├── config.py                   # Конфигурация проекта
├── config.yaml                 # YAML конфигурация
├── main.py                     # Точка входа приложения
├── requirements.txt            # Зависимости проекта
└── README.md                   # Документация
```

---

## 🔧 Ключевые Компоненты

### 1. CamoufoxParser (Базовый класс для Пятерочки)

**Файл:** `parsers/camoufox_parser.py`

**Назначение:** Базовый класс для всех парсеров, использующих Camoufox.

**Основные возможности:**
- ✅ Автоматическая генерация реалистичных fingerprint
- ✅ Маскировка navigator.webdriver
- ✅ Эмуляция поведения человека (humanize=True)
- ✅ Блокировка трекеров, аналитики, изображений
- ✅ Обнаружение и обработка капчи
- ✅ Human-like скроллинг
- ✅ Поддержка региональных заголовков из KB

**Пример использования:**
```python
from parsers.pyaterochka import PyaterochkaParser

async with PyaterochkaParser(region="77", headless=True) as parser:
    result = await parser.parse_category("https://5ka.ru/catalog/ryba--251C13077/")
    print(f"Найдено товаров: {result.total_products}")
```

---

### 2. PyaterochkaParser (Парсер Пятерочки)

**Файл:** `parsers/pyaterochka.py`

**Назначение:** Специализированный парсер для сайта 5ka.ru.

**Особенности:**
- Наследуется от `CamoufoxParser`
- Использует селекторы из Knowledge Base (`knowledge_base/pyaterochka.md`)
- Поддерживает пагинацию (до 10 страниц)
- Автоматический скроллинг для lazy loading
- Извлечение всех полей товара:
  - Название (`data-testid="product-name"`)
  - Цена (`data-testid="price-current"`)
  - Старая цена (`data-testid="price-old"`)
  - Вес/объем (`data-testid="product-weight"`)
  - Бренд (`data-testid="product-brand"`)
  - Изображение (`data-testid="product-image"`)

**Структура возвращаемых данных:**
```python
ParseResult(
    shop="pyaterochka",
    category=CategoryInfo(name="Рыба", url="..."),
    products=[
        Product(
            id="pyaterochka_0_20260506120000",
            name="Лосось филе охлажденное, 1 кг",
            description="Каждый День Лосось филе...",
            price=ProductPrice(current=1299.0, old=1599.0),
            category="Рыба",
            product_url="https://5ka.ru/prod/12345678",
            image_url="https://5ka.ru/media/products/...",
            attributes={"weight": "1 кг", "brand": "Каждый День"},
            in_stock=True,
            created_at=datetime.now()
        )
    ],
    total_products=24,
    errors=[],
    warnings=[],
    parse_duration_ms=5432
)
```

---

### 3. Knowledge Base (База Знаний)

**Файл:** `knowledge_base/pyaterochka.md`

**Назначение:** Централизованное хранилище конфигурации для каждого магазина.

**Структура KB:**
```markdown
# Knowledge Base: Пятерочка (5ka.ru)

## URLs категорий
- Рыба: https://5ka.ru/catalog/ryba--251C13077/
- Морепродукты: https://5ka.ru/catalog/moreprodukty--251C13078/

## CSS Селекторы
- product_card: div[data-testid="product-card"]
- product_name: div[data-testid="product-name"]
- price_current: span[data-testid="price-current"]
- price_old: span[data-testid="price-old"]
- weight_volume: span[data-testid="product-weight"]
- product_link: div[data-testid="product-card"] a
- product_image: img[data-testid="product-image"]
- brand: span[data-testid="product-brand"]

## Заголовки
- X-Region: required (значение из региона)

## Анти-бот защита
- Триггеры: 403, 429, "Проверка браузера"
- Стратегии: chrome124 impersonate, задержки 2-4 сек
- CAPTCHA: Cloudflare Turnstile
```

**Загрузка KB:**
```python
from utils.kb_loader import KBLoader

loader = KBLoader()
kb = loader.load_shop("pyaterochka")
print(kb.selectors["product_card"]["css"])  # div[data-testid="product-card"]
print(kb.headers.custom)  # {"X-Region": "required"}
```

---

### 4. Strategies (Стратегии)

**Назначение:** Переиспользуемые паттерны автоматизации браузера.

| Стратегия | Описание | Когда используется |
|-----------|----------|-------------------|
| `ScrollStrategy` | Плавный скроллинг страницы | Lazy loading товаров |
| `PaginationStrategy` | Навигация по страницам | Многостраничные каталоги |
| `LazyLoadStrategy` | Ожидание загрузки контента | Динамическая подгрузка |
| `CaptchaHandler` | Обнаружение и обработка капчи | При появлении CAPTCHA |

**Пример:**
```python
from strategies.scroll_strategy import ScrollStrategy

strategy = ScrollStrategy(page, config={"max_scrolls": 10})
await strategy.apply(page)
```

---

### 5. Policies Engine (Движок Политик)

**Назначение:** Автоматическая обработка ошибок и восстановление.

**Встроенные политики:**
- **HTTP 403**: Сменить proxy + UA + повторить (макс. 5 раз)
- **HTTP 429**: Увеличить задержку + повторить (макс. 3 раза)
- **CAPTCHA**: Переключиться на Playwright + ручное решение
- **Timeout**: Сменить proxy + повторить (макс. 3 раза)
- **Selector not found**: Переключиться на Playwright

**Пример:**
```python
from policies.engine import PoliciesEngine, ErrorType

engine = PoliciesEngine()
action = await engine.evaluate({"status_code": 403})
# action = "rotate_proxy_and_retry"
```

---

## 🔄 Поток Данных

```
1. Инициализация парсера
   ↓
2. Загрузка Knowledge Base
   ↓
3. Запуск Camoufox (через start_browser())
   ↓
4. Применение региональных заголовков из KB
   ↓
5. Загрузка страницы (fetch_page_camoufox)
   ├─ Проверка на капчу
   ├─ Ожидание селектора
   └─ Скроллинг для lazy load
   ↓
6. Парсинг HTML (BeautifulSoup + селекторы из KB)
   ↓
7. Валидация данных (Pydantic)
   ↓
8. Возврат ParseResult
```

---

## 🛡 Методы Обхода Защиты

### Camoufox Преимущества

1. **Реальные指纹 (fingerprints)**
   - Генерируются через browserforge
   - Включают OS, браузер, шрифты, WebGL

2. **Маскировка webdriver**
   - `navigator.webdriver = undefined`
   - Скрытие признаков автоматизации

3. **Human-like поведение**
   - `humanize=True` добавляет случайные задержки
   - Плавные движения курсора

4. **Блокировка трекеров**
   - Аналитика, телеметрия блокируются через route

5. **Региональность**
   - Geolocation Europe/Moscow
   - Locale ru-RU
   - Timezone Moscow

---

## 📊 Поддерживаемые Магазины

| Магазин | Базовый URL | Инструмент | Регион Header | Статус |
|---------|-------------|------------|---------------|--------|
| Пятерочка | 5ka.ru | Camoufox | X-Region-Id | ✅ Готов |
| Магнит | magnit.ru | Camoufox | X-City-Id | 🟡 В разработке |
| Лента | lenta.com | Camoufox | X-Region | 🟡 В разработке |
| Ашан | auchan.ru | Camoufox | X-Region | 🟡 В разработке |
| О'Кей | okey.ru | Camoufox | X-Store-Id | 🟡 В разработке |
| Перекресток | perekrestok.ru | Camoufox | X-Client-Id | 🟡 В разработке |

---

## 🚀 Быстрый Старт

### Установка зависимостей

```bash
cd /workspace/parser_riba_temp
pip install -r requirements.txt
playwright install firefox  # Для Camoufox
```

### Запуск парсера Пятерочки

```python
import asyncio
from parsers.pyaterochka import PyaterochkaParser

async def main():
    parser = PyaterochkaParser(region="77", headless=True)
    
    try:
        result = await parser.parse_category(
            "https://5ka.ru/catalog/ryba--251C13077/"
        )
        
        print(f"✅ Найдено товаров: {result.total_products}")
        for product in result.products[:5]:
            print(f"  - {product.name}: {product.price.current}₽")
            
    finally:
        await parser.close_browser()

asyncio.run(main())
```

### Запуск через main.py

```bash
python main.py --store pyaterochka --category ryba --region 77
```

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest tests/ -v

# Smoke тесты парсеров
pytest tests/test_parsers_smoke.py -v

# Тесты KB Loader
pytest tests/test_kb_loader.py -v
```

---

## 📝 Расширение (Добавление Нового Магазина)

1. **Создать KB файл:** `knowledge_base/newstore.md`
2. **Создать парсер:** `parsers/newstore.py` (наследовать от `CamoufoxParser`)
3. **Добавить селекторы** в KB
4. **Настроить headers** в KB
5. **Протестировать** через pytest

**Пример шаблона парсера:**
```python
from parsers.camoufox_parser import CamoufoxParser

class NewStoreParser(CamoufoxParser):
    def __init__(self, region="77", headless=True):
        super().__init__(
            store_name="newstore",
            base_url="https://newstore.ru",
            headless=headless,
            region=region
        )
    
    async def parse_category(self, url: str) -> ParseResult:
        # Реализация парсинга
        pass
```

---

## 🎯 Соответствие Camoufox API

### Вызовы Camoufox в проекте

| Функция | Camoufox API | Использование в проекте |
|---------|--------------|------------------------|
| `AsyncCamoufox()` | `camoufox.async_api.AsyncCamoufox` | `camoufox_parser.py:76` |
| `launch_options` | `camoufox.utils.launch_options` | Через `AsyncCamoufox.__init__` |
| `headless` | Параметр запуска | `headless=True/False` |
| `humanize` | Параметр запуска | `humanize=True` (по умолчанию) |
| `locale` | Параметр запуска | `locale="ru-RU"` |
| `geolocation` | Через context args | `Europe/Moscow` |
| `get_ua()` | Метод для получения UA | `await self._camoufox.get_ua()` |

### Параметры launch_options

```python
# Из camoufox.utils.launch_options
launch_options(
    headless=True,              # Фоновый режим
    locale="ru-RU",             # Локаль
    humanize=True,              # Эмуляция человека
    i_know_what_im_doing=True,  # Отключение предупреждений
    os=["windows", "linux"],    # OS для fingerprint
    block_images=False,         # Не блокировать изображения
    geoip=False,                # Не использовать GeoIP
    timezone="Europe/Moscow",   # Таймзона
)
```

---

## 📄 Лицензия

MIT License

---

## 📞 Контакты

GitHub: https://github.com/Lyti4/ParserRIba

---

**Дата обновления:** Май 2026  
**Версия:** 1.0.0  
**Статус:** Активная разработка
