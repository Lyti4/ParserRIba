# 🐟 ParserRiba: Парсер цен на рыбные товары

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Профессиональная система парсинга цен на рыбные товары для крупнейших российских ритейлеров с архитектурой на основе Knowledge Base.

## 🏪 Поддерживаемые магазины

| Магазин | Статус | Инструмент | Особенности |
|---------|--------|------------|-------------|
| Пятерочка | ✅ | Camoufox/Playwright | data-testid селекторы, скроллинг |
| Магнит | ✅ | Playwright | reCAPTCHA v2, X-City-Id header |
| Лента | ✅ | Playwright | Cloudflare Turnstile, X-Region header |
| Перекресток | ✅ | Playwright | Cookies + X-Client-Id обязательны |
| Ашан | ✅ | Playwright | X-Region + X-Shop-Id headers |
| О'Кей | ✅ | Playwright | X-Store-Id header |

## ✨ Ключевые особенности

### 🧠 Архитектура на основе Knowledge Base
Конфигурация магазинов хранится в Markdown-файлах (`knowledge_base/*.md`), а не в коде:
- URL категорий
- CSS/XPath селекторы
- HTTP заголовки
- Стратегии обхода анти-бот защиты

Это позволяет добавлять новые магазины **без изменения кода парсера**.

### 🔄 Гибридный движок
Автоматическое переключение между:
- **curl-cffi** — быстрый запрос с impersonation (Chrome/Firefox профили)
- **Playwright** — полноценный браузер для сложных случаев с JS и капчей

### 🛡 Система стратегий
Встроенные модули для обхода защит:
- `ScrollStrategy` — эмуляция человеческого скроллинга
- `LazyLoadStrategy` — ожидание подгрузки контента
- `PaginationStrategy` — обработка пагинации
- `CaptchaHandler` — обработка капчи

### 📋 Policy Engine
Автоматическая реакция на ошибки через конфигурируемые политики:
| Ошибка | Действие |
|--------|----------|
| 403 Forbidden | Смена прокси + User-Agent + ожидание |
| 429 Rate Limited | Увеличение задержки + ожидание |
| CAPTCHA | Попытка решения + длительное ожидание |
| Timeout | Смена прокси + повтор |
| Selector Not Found | Переключение на Playwright |

### 🌍 Региональность
Поддержка региональных заголовков для корректного получения цен:
- `X-Region` (Лента)
- `X-City-Id` (Магнит)
- `X-Store-Id` (О'Кей)
- `X-Client-Id` (Перекресток)

### 📊 Валидация данных
Строгая типизация через **Pydantic V2**:
```python
class Product(BaseModel):
    name: str
    price: ProductPrice
    dimensions: Optional[ProductDimensions]
    product_link: HttpUrl
    in_stock: bool
```

## 📁 Структура проекта

```
ParserRiba/
├── main.py                    # Точка входа, CLI интерфейс
├── config.yaml                # Конфигурация (магазины, категории)
├── requirements.txt           # Зависимости Python
├── docker-compose.yml         # Docker оркестрация
│
├── parsers/                   # Парсеры магазинов
│   ├── base_parser.py         # Базовый класс с KB интеграцией
│   ├── pyaterochka.py         # Пятерочка (Camoufox)
│   ├── magnit.py              # Магнит
│   ├── lenta.py               # Лента
│   ├── perekrestok.py         # Перекресток
│   ├── auchan.py              # Ашан
│   ├── okey.py                # О'Кей
│   ├── camoufox_parser.py     # Базовый Camoufox парсер
│   └── playwright_parser.py   # Базовый Playwright парсер
│
├── knowledge_base/            # Конфигурация магазинов (Markdown)
│   ├── pyaterochka.md
│   ├── magnit.md
│   ├── lenta.md
│   ├── perekrestok.md
│   ├── auchan.md
│   ├── okey.md
│   └── template.md            # Шаблон для нового магазина
│
├── models/                    # Pydantic схемы данных
│   ├── schemas.py             # Product, ParseResult, CategoryInfo
│   └── product.py             # FishProduct (обратная совместимость)
│
├── utils/                     # Утилиты
│   ├── kb_loader.py           # Загрузчик Knowledge Base
│   ├── logger.py              # Настройка логирования
│   ├── session_manager.py     # Управление сессиями браузера
│   └── export.py              # Экспорт в JSON/CSV/Excel
│
├── strategies/                # Стратегии обхода защит
│   ├── base_strategy.py       # Базовый класс стратегии
│   ├── scroll_strategy.py     # Эмуляция скроллинга
│   ├── lazy_load_strategy.py  # Ожидание lazy-loading
│   ├── pagination_strategy.py # Обработка пагинации
│   └── captcha_handler.py     # Обработка капчи
│
├── policies/                  # Policy Engine
│   └── engine.py              # Движок обработки ошибок
│
├── tests/                     # Тесты
│   ├── test_kb_loader.py      # Тесты загрузчика KB
│   ├── test_models.py         # Тесты моделей
│   └── test_parsers_smoke.py  # Smoke-тесты парсеров
│
└── logs/                      # Логи приложения
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Клонирование репозитория
git clone https://github.com/Lyti4/ParserRIba.git
cd ParserRiba

# Установка Python зависимостей
pip install -r requirements.txt

# Установка браузеров Playwright
playwright install chromium
playwright install firefox
```

### 2. Базовый запуск

```bash
# Парсинг всех включенных магазинов из конфига
python main.py

# Парсинг конкретного магазина
python main.py --store pyaterochka

# Несколько магазинов
python main.py --store magnit lenta

# Список доступных магазинов
python main.py --list-stores

# С указанием категорий
python main.py --store pyaterochka --category "Рыба" "Морепродукты"

# Запуск с видимым браузером (для отладки)
python main.py --store pyaterochka --no-headless

# Изменение уровня логирования
python main.py --store pyaterochka --log-level DEBUG
```

### 3. Использование как библиотеки

```python
import asyncio
from parsers.pyaterochka import PyaterochkaParser
from utils.kb_loader import KBLoader

async def main():
    # Инициализация парсера
    parser = PyaterochkaParser(
        shop_name="pyaterochka",
        region="77",  # Москва
        headless=True
    )
    
    # Загрузка Knowledge Base
    kb = KBLoader().load_shop("pyaterochka")
    
    # Парсинг категории
    category_url = kb.categories.get("Рыба")
    result = await parser.parse_category(category_url)
    
    # Обработка результатов
    print(f"Найдено товаров: {result.total_products}")
    for product in result.products:
        print(f"{product.name}: {product.price.current} ₽")

asyncio.run(main())
```

## ⚙️ Конфигурация

### config.yaml

```yaml
stores:
  pyaterochka:
    enabled: true
    categories:
      - "Рыба"
      - "Морепродукты"
    region: "77"
  
  magnit:
    enabled: true
    categories:
      - "Рыба и морепродукты"
    city_id: "1"

browser:
  headless: true
  timeout: 30000
  proxy: null

logging:
  level: INFO
  file: logs/parser_riba.log
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OUTPUT_FILE` | Файл для экспорта | `fish_products.xlsx` |
| `REQUEST_DELAY` | Задержка между запросами (сек) | `3` |
| `REQUEST_TIMEOUT` | Таймаут запроса (сек) | `30` |
| `PROXY_LIST` | Список прокси (JSON) | `[]` |

## 🐳 Docker

### Запуск через docker-compose

```bash
docker-compose up --build
```

### Ручной запуск

```bash
# Сборка образа
docker build -t parser-riba .

# Запуск
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e STORES=pyaterochka,magnit \
  parser-riba
```

## 🧪 Тестирование

```bash
# Все тесты
pytest tests/ -v

# Только тесты конфигурации
pytest tests/test_kb_loader.py -v

# Smoke-тесты парсеров (требуют сеть)
pytest tests/test_parsers_smoke.py -v

# С покрытием
pytest --cov=parsers --cov-report=html
```

## 📖 Добавление нового магазина

### Шаг 1: Создайте файл Knowledge Base

Скопируйте `knowledge_base/template.md` в `knowledge_base/newstore.md`:

```markdown
# 📘 Knowledge Base: Новый Магазин

## ℹ️ Общая информация
- **Базовый URL**: `https://newstore.ru`
- **Тип защиты**: [описание]

## 🔗 URLs категорий
| Категория | URL |
|-----------|-----|
| Рыба | `https://newstore.ru/catalog/fish` |

## 🎯 CSS Селекторы
### Карточка товара
```css
div.product-card
```

### Название
```css
h3.product-title
```

## 🌐 Заголовки
```python
{'X-Custom-Header': 'value'}
```

## 🛡 Анти-бот защита
- [ ] Требуется скроллинг
- [ ] Есть капча
- [ ] Нужен Playwright
```

### Шаг 2: Создайте парсер

```python
# parsers/newstore.py
from parsers.base_parser import BaseParser
from models.schemas import Product, ParseResult

class NewStoreParser(BaseParser):
    async def _fetch_page(self, url: str, page: int) -> str:
        # Реализация загрузки страницы
        
    async def _parse_products(self, html: str, category_url: str) -> List[Product]:
        # Реализация парсинга
        
    async def _has_next_page(self, html: str, page: int) -> bool:
        # Проверка пагинации
        
    async def _get_next_page_url(self, html: str, category_url: str, page: int) -> Optional[str]:
        # Получение URL следующей страницы
```

### Шаг 3: Зарегистрируйте парсер

Добавьте в `main.py` в `ParserFactory.PARSERS`:

```python
PARSERS = {
    "newstore": NewStoreParser,
    # ...
}
```

## 🔧 Расширенные возможности

### Кастомные политики

```python
from policies.engine import PoliciesEngine, PolicyRule, ErrorType, ActionType

engine = PoliciesEngine()

# Добавить свою политику
engine.add_policy(PolicyRule(
    error_types=[ErrorType.HTTP_403],
    actions=[ActionType.CHANGE_PROXY, ActionType.WAIT_AND_RETRY],
    max_retries=5,
    delay_between_retries=3.0,
    priority=10
))
```

### Стратегии

```python
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy

strategy = ScrollStrategy(
    scroll_pause=0.5,
    max_scrolls=10,
    human_like=True
)

await strategy.apply(page)
```

## 📊 Выходные данные

### JSON формат

```json
{
  "shop": "pyaterochka",
  "category": {
    "name": "Рыба",
    "url": "https://5ka.ru/catalog/ryba/"
  },
  "products": [
    {
      "name": "Лосось филе",
      "price": {
        "current": 1299.99,
        "old": 1599.99,
        "currency": "RUB",
        "discount_percent": 19
      },
      "dimensions": {
        "weight": 1000,
        "unit_type": "g"
      },
      "product_link": "https://5ka.ru/prod/12345",
      "in_stock": true,
      "parsed_at": "2024-01-15T10:30:00"
    }
  ],
  "total_products": 1,
  "page": 1,
  "parse_duration_ms": 2345
}
```

## 🆘 Решение проблем

### Частые ошибки

| Проблема | Решение |
|----------|---------|
| 403 Forbidden | Используйте `--no-headless`, увеличьте задержки |
| CAPTCHA | Решите вручную первый раз, сохраните cookies |
| Timeout | Проверьте прокси, увеличьте `REQUEST_TIMEOUT` |
| Нет товаров | Обновите селекторы в Knowledge Base |

### Отладка

```bash
# Режим отладки с видимым браузером
python main.py --store pyaterochka --no-headless --log-level DEBUG

# Просмотр логов
tail -f logs/parser_riba.log
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Пушните (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

## 📞 Контакты

- GitHub: [@Lyti4](https://github.com/Lyti4)
- Issues: [GitHub Issues](https://github.com/Lyti4/ParserRIba/issues)
