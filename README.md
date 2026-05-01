# 🐟 ParserRiba: Парсер цен на рыбные товары

Профессиональная система парсинга цен на рыбные товары для крупнейших российских ритейлеров (Пятерочка, Магнит, Лента, Перекресток, О'Кей, Ашан).

## 🚀 Особенности

- **Архитектура на основе Knowledge Base**: Конфигурация магазинов (URL, селекторы, заголовки) хранится в Markdown-файлах, а не в коде.
- **Гибридный движок**: Автоматическое переключение между `curl-cffi` (быстро) и `Playwright` (обход сложных защит).
- **Система стратегий**: Встроенные модули для скроллинга, пагинации, обработки lazy-loading и капчи.
- **Policy Engine**: Автоматическая реакция на ошибки (403, 503, CAPTCHA) с ротацией прокси и задержками.
- **Региональность**: Поддержка региональных заголовков (`X-Region`, `X-Store`) для корректного получения цен.
- **Валидация данных**: Строгая типизация выходных данных через Pydantic V2.
- **Docker-ready**: Полная контейнеризация для запуска в любой среде.

## 🏗 Архитектура

```
ParserRiba/
├── knowledge_base/       # Конфиги магазинов (Markdown)
├── parsers/              # Логика парсеров (Base + специфичные)
├── strategies/           # Стратегии обхода защит
├── policies/             # Движок обработки ошибок
├── models/               # Pydantic схемы данных
├── utils/                # Утилиты (Loader, SessionManager, Logger)
├── tests/                # Интеграционные тесты
├── main.py               # Точка входа
└── docker-compose.yml    # Оркестрация
```

## 🛠 Установка

### Локальный запуск

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Lyti4/ParserRIba.git
   cd ParserRIba
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Настройте окружение (опционально):
   Скопируйте `.env.example` в `.env` и укажите свои прокси/API ключи.

### Docker запуск

```bash
docker-compose up --build
```

Результаты сохранятся в папку `output/`.

## 📖 Использование

### Базовый запуск

Запуск парсинга конкретного магазина:

```bash
python main.py --shop pyaterochka --category fish --limit 50
```

Аргументы:
- `--shop`: Название магазина (pyaterochka, magnit, lenta, auchan, okey, perekrestok).
- `--category`: Категория (по умолчанию 'fish').
- `--limit`: Лимит товаров (0 — без ограничений).
- `--region`: Региональный код (если требуется, например, для Lenta).
- `--output`: Формат вывода (json, csv, excel).

### Пример кода (Python API)

```python
import asyncio
from parsers.factory import ParserFactory
from utils.session_manager import SessionManager

async def main():
    session = SessionManager()
    parser = ParserFactory.get_parser("lenta", session, region="msk")
    
    results = await parser.parse_category(
        url="https://lenta.com/catalog/ryba...",
        limit=100
    )
    
    for product in results.products:
        print(f"{product.name}: {product.price.value} ₽")

asyncio.run(main())
```

## 📚 Knowledge Base

Система использует файлы в папке `knowledge_base/` для хранения конфигурации. Это позволяет добавлять новые магазины без изменения кода парсера.

Структура файла магазина (`*.md`):
- **URL**: Ссылки на категории.
- **Selectors**: CSS/XPath селекторы для товаров, цен, названий.
- **Headers**: Специфичные заголовки (например, `X-Region-Id`).
- **Anti-bot**: Тип защиты и рекомендуемые стратегии.

## 🧪 Тестирование

Запуск полного набора тестов:

```bash
pytest tests/ -v
```

Запуск только тестов конфигурации:
```bash
pytest tests/test_kb_loader.py -v
```

## 🔧 Конфигурация

Основные настройки находятся в `config.yaml` или передаются через переменные окружения:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `PROXY_LIST` | Список прокси серверов | `[]` |
| `HEADLESS` | Запуск браузера в фоновом режиме | `true` |
| `TIMEOUT` | Таймаут запроса (сек) | `30` |
| `RETRY_COUNT` | Количество попыток при ошибке | `3` |

## 🤝 Вклад в проект

1. Форкните репозиторий.
2. Создайте ветку для новой фичи (`git checkout -b feature/amazing-feature`).
3. Закоммитьте изменения (`git commit -m 'Add some amazing feature'`).
4. Пушните в ветку (`git push origin feature/amazing-feature`).
5. Откройте Pull Request.

## 📄 Лицензия

MIT License.

## 🆘 Поддержка

При возникновении проблем создайте Issue в репозитории с подробным описанием ошибки и логами.
