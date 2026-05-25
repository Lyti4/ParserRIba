# 🏗 Архитектура ParserRiba

## Обзор системы

ParserRiba — это модульная система парсинга цен на рыбные товары для российских ритейлеров, построенная на основе **Knowledge Base** архитектуры.

## Принципы архитектуры

### 1. Конфигурация через Knowledge Base
Вся специфичная для магазинов информация хранится в Markdown-файлах, а не в коде:
- URL категорий
- CSS/XPath селекторы
- HTTP заголовки
- Стратегии обхода защит

**Преимущество**: Добавление нового магазина не требует изменения кода парсера.

### 2. Разделение ответственности
- **parsers/** — логика извлечения данных
- **strategies/** — стратегии обхода анти-бот защиты
- **policies/** — обработка ошибок и принятие решений
- **models/** — структуры данных (Pydantic)
- **utils/** — вспомогательные утилиты

### 3. Гибридный подход к запросам
- **curl-cffi** с impersonation — для простых случаев (быстро)
- **Playwright** — для сложных сайтов с JS и капчей (медленнее, но надежнее)

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                    (Точка входа, CLI)                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ParserFactory                               │
│              (Создание парсеров по названию)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Pyaterochka   │   │    Magnit     │   │    Lenta      │
│    Parser     │   │    Parser     │   │    Parser     │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BaseParser                                 │
│         (Общая логика: KB, стратегии, политики)                  │
├─────────────────────────────────────────────────────────────────┤
│  • KBLoader → ShopKnowledge                                      │
│  • Strategies: Scroll, LazyLoad, Pagination                      │
│  • PolicyEngine → Error Handling                                 │
│  • _fetch_page() / _parse_products() (абстрактные методы)       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│    curl-cffi          │       │     Playwright        │
│  (impersonate mode)   │       │   (browser autom.)    │
└───────────────────────┘       └───────────────────────┘
```

## Поток данных

```
1. main.py загружает config.yaml
         │
         ▼
2. ParserFactory создает нужный парсер
         │
         ▼
3. BaseParser.__init__() загружает KB через KBLoader
         │
         ▼
4. parse_category() вызывается для URL категории
         │
         ├─► Применяет Pre-Strategies (скролл, задержки)
         │
         ├─► _fetch_page() получает HTML
         │       │
         │       ├─► curl-cffi (быстро)
         │       └─► Playwright (если нужно)
         │
         ├─► _parse_products() извлекает данные
         │       │
         │       └─► Использует селекторы из KB
         │
         ├─► Применяет Post-Strategies
         │
         └─► Возвращает ParseResult (Pydantic модель)
                 │
                 ▼
5. Результаты сохраняются в JSON/CSV/Excel
```

## Модели данных (Pydantic)

### Иерархия моделей

```
ParseResult
├── shop: str
├── category: CategoryInfo
│   ├── name: str
│   ├── url: HttpUrl
│   └── parent_category: str
├── products: List[Product]
├── total_products: int
├── page: int
├── has_next_page: bool
└── parse_duration_ms: int

Product
├── id: Optional[str]
├── name: str
├── brand: Optional[str]
├── price: ProductPrice
│   ├── current: float
│   ├── old: Optional[float]
│   ├── unit: Optional[float]
│   └── discount_percent: Optional[int]
├── dimensions: Optional[ProductDimensions]
│   ├── weight: Optional[float]
│   ├── volume: Optional[float]
│   └── unit_type: str
├── image_url: Optional[HttpUrl]
├── product_link: HttpUrl
├── in_stock: bool
└── parsed_at: datetime
```

## Knowledge Base структура

### Формат файла (knowledge_base/{shop}.md)

```markdown
# 📘 Knowledge Base: {Название}

## ℹ️ Общая информация
- Базовый URL
- Тип защиты
- Требуется ли JS

## 🔗 URLs категорий
| Категория | URL | Примечание |
|-----------|-----|------------|

## 🎯 CSS Селекторы
### Карточка товара
```css
div[data-testid="product-card"]
```

### Название
```css
h3.product-name
```

## 🌐 Заголовки
```python
{'X-Region': '77', 'X-Custom': 'value'}
```

## 🛡 Анти-бот защита
- Триггеры блокировки
- Рекомендуемые стратегии
- Тип капчи
```

### Парсинг KB

`KBLoader` извлекает:
1. **Базовый URL** из секции "Общая информация"
2. **Категории** из таблицы в секции URLs
3. **Селекторы** из CSS code blocks
4. **Headers** из Python dict в секции заголовков
5. **Anti-bot** настройки из секции защиты

## Стратегии (patterns)

### BaseStrategy
```python
class BaseStrategy(ABC):
    @abstractmethod
    async def apply_pre(self, context: Any) -> None:
        """Действия до запроса"""
    
    @abstractmethod
    async def apply_post(self, data: Any) -> None:
        """Действия после парсинга"""
    
    @abstractmethod
    def should_apply_pre(self, context: Any) -> bool:
        """Условие применения pre-стратегии"""
```

### Реализации

| Стратегия | Назначение | Когда применяется |
|-----------|------------|-------------------|
| ScrollStrategy | Эмуляция скроллинга | При lazy-loading товаров |
| LazyLoadStrategy | Ожидание подгрузки | Для динамического контента |
| PaginationStrategy | Обработка страниц | Многостраничные категории |
| CaptchaHandler | Решение капчи | При обнаружении капчи |

## Policy Engine

### Архитектура обработки ошибок

```
Ошибка → classify_error() → ErrorType → PoliciesEngine.evaluate() → PolicyResult
                                                      │
                                                      ▼
                                         [ActionType.RETRY, ActionType.CHANGE_PROXY, ...]
```

### Типы ошибок (ErrorType)

- `HTTP_403` — Forbidden (блокировка)
- `HTTP_429` — Rate limited
- `TIMEOUT` — Превышение времени ожидания
- `CAPTCHA` — Обнаружена капча
- `SELECTOR_NOT_FOUND` — Элементы не найдены
- `EMPTY_RESPONSE` — Пустой ответ
- `NETWORK_ERROR` — Ошибка сети

### Действия (ActionType)

- `RETRY` — Повторить запрос
- `CHANGE_PROXY` — Сменить прокси
- `CHANGE_USER_AGENT` — Сменить User-Agent
- `INCREASE_DELAY` — Увеличить задержку
- `SWITCH_TO_PLAYWRIGHT` — Переключиться на браузер
- `WAIT_AND_RETRY` — Подождать и повторить
- `CLEAR_COOKIES` — Очистить cookies
- `ABORT_SESSION` — Прервать сессию

### Пример политики

```python
PolicyRule(
    error_types=[ErrorType.HTTP_403],
    actions=[
        ActionType.CHANGE_PROXY,
        ActionType.CHANGE_USER_AGENT,
        ActionType.WAIT_AND_RETRY
    ],
    max_retries=5,
    delay_between_retries=2.0,
    priority=10
)
```

## Расширение системы

### Добавление нового магазина

1. **Создать KB файл**: `knowledge_base/newstore.md`
2. **Создать парсер**: `parsers/newstore.py`
   ```python
   class NewStoreParser(BaseParser):
       async def _fetch_page(...) -> str: ...
       async def _parse_products(...) -> List[Product]: ...
       async def _has_next_page(...) -> bool: ...
       async def _get_next_page_url(...) -> Optional[str]: ...
   ```
3. **Зарегистрировать**: Добавить в `ParserFactory.PARSERS`

### Создание новой стратегии

```python
from strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    async def apply_pre(self, url: str) -> None:
        # Логика перед запросом
        
    async def apply_post(self, products: List[Product]) -> None:
        # Логика после парсинга
        
    def should_apply_pre(self, context: str) -> bool:
        return "specific" in context
```

### Добавление новой политики

```python
from policies.engine import PolicyRule, ErrorType, ActionType

engine.add_policy(PolicyRule(
    error_types=[ErrorType.CAPTCHA],
    actions=[ActionType.SOLVE_CAPTCHA, ActionType.WAIT_AND_RETRY],
    max_retries=2,
    delay_between_retries=10.0,
    priority=8
))
```

## Безопасность и анти-детект

### Методы обхода защиты

1. **Impersonation** (curl-cffi)
   - Chrome/Firefox профили
   - TLS fingerprint matching
   
2. **Stealth режим** (Playwright)
   - Удаление webdriver флагов
   - Эмуляция реального браузера
   
3. **Поведенческие паттерны**
   - Случайные задержки
   - Человеческий скроллинг
   - Ротация User-Agent

4. **Сессионные данные**
   - Сохранение cookies
   - Поддержка региональных headers

## Производительность

### Оптимизации

- **Асинхронность**: asyncio для всех I/O операций
- **Ленивая инициализация**: Браузер запускается только при необходимости
- **Кэширование**: Сохранение сессий и cookies
- **Пул соединений**: curl-cffi session reuse

### Ограничения

| Параметр | Значение | Настройка |
|----------|----------|-----------|
| Запросов в минуту | ~10-15 | REQUEST_DELAY |
| Таймаут запроса | 30 сек | REQUEST_TIMEOUT |
| Максимум retries | 3-5 | max_retries в политике |
| Время жизни сессии | ~30 мин | Зависит от сайта |

## Тестирование

### Уровни тестов

1. **Unit тесты** (`test_models.py`)
   - Валидация Pydantic моделей
   - Тесты KBLoader

2. **Integration тесты** (`test_parsers_smoke.py`)
   - Smoke-тесты парсеров
   - Проверка доступности URLs

3. **E2E тесты** (ручной запуск)
   - Полный парсинг категорий
   - Проверка выходных данных

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Только unit
pytest tests/test_models.py tests/test_kb_loader.py -v

# Smoke (требует сеть)
pytest tests/test_parsers_smoke.py -v
```

## Мониторинг и логирование

### Уровни логов

- **DEBUG**: Детальная информация для отладки
- **INFO**: Основные события (старт, завершение, прогресс)
- **WARNING**: Предупреждения (повторные попытки, fallback)
- **ERROR**: Критические ошибки

### Формат лога

```
2024-01-15 10:30:00.123 | INFO     | main:main:275 - 🎯 Магазины для парсинга: pyaterochka, magnit
2024-01-15 10:30:01.456 | INFO     | base_parser:parse_category:150 - ✅ Parsed 24 products from Рыба in 1234ms
2024-01-15 10:30:02.789 | WARNING  | policies:evaluate:223 - ⚠️  Policy triggered retry: ['change_proxy', 'wait_and_retry']
```

## Развертывание

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && playwright install chromium

COPY . .
CMD ["python", "main.py"]
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `STORES` | Список магазинов | Все из конфига |
| `HEADLESS` | Режим браузера | true |
| `PROXY_LIST` | JSON список прокси | [] |
| `LOG_LEVEL` | Уровень логирования | INFO |

## Будущие улучшения

- [ ] Поддержка API эндпоинтов (где доступны)
- [ ] Интеграция с сервисами решения капчи (2Captcha, etc.)
- [ ] Распределенный парсинг (Celery/RQ)
- [ ] Веб-интерфейс для управления
- [ ] База данных для хранения истории цен
- [ ] Графики и аналитика изменений цен
