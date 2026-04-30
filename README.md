# Парсер цен на рыбные товары

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Описание

Парсер собирает цены на рыбные товары из крупнейших российских сетей:
- **Пятерочка** (5ka.ru)
- **Магнит** (magnit.ru)
- **Перекресток** (perekrestok.ru)
- **Лента** (lenta.com)
- **Ашан** (auchan.ru)
- **Окей** (okey.ru)

**Возможности:**
- ✅ Сбор данных о цене, названии, весе, бренде и категории товаров
- ✅ Обход базовой защиты от парсинга (WAF, TLS fingerprinting)
- ✅ Поддержка JavaScript-рендеринга через Playwright
- ✅ Экспорт результатов в Excel с подробной статистикой
- ✅ Визуальный режим отладки с отображением браузера
- ✅ Гибкая настройка через файл `.env`
- ✅ Логирование процесса работы

## ⚠️ Важное замечание

**Парсер работает только с домашнего/офисного компьютера!**

Серверные IP-адреса (дата-центры, облака, VPS) заблокированы всеми крупными ритейлерами. 
При запуске с сервера вы получите:
- 403 Forbidden / 401 Unauthorized
- 404 Not Found (для SPA сайтов)
- SSL Handshake Failure
- 0 найденных товаров

### Почему нужен запуск с реальной машины:

| Проблема | Причина | Решение |
|----------|---------|---------|
| **WAF блокировка** | Серверные IP в чёрных списках | Резидентный IP домашнего провайдера |
| **JavaScript рендеринг** | Контент грузится через JS | Playwright выполняет JS |
| **Требуется авторизация** | Некоторые сайты требуют login | Cookies от вашей сессии браузера |
| **TLS fingerprinting** | Определяют не-браузерный TLS | curl-cffi с browser impersonation |

## 🚀 Быстрый старт

### Для пользователей Windows

📖 **Подробная инструкция для Windows:** [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md)

**Краткая версия (5 команд):**

```bash
git clone https://github.com/Lyti4/ParserRIba.git
cd ParserRIba
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt && playwright install chromium && python main.py
```

### Шаг 1: Установка Python

Убедитесь, что у вас установлен **Python 3.9 или выше**:

```bash
python --version
```

Если нет - скачайте с https://www.python.org/downloads/

### Шаг 2: Клонирование репозитория

```bash
cd C:\Projects  # или любая другая папка
git clone <URL_репозитория>
cd <имя_репозитория>
```

Или просто скопируйте все файлы из `/workspace` в локальную папку.

### Шаг 3: Создание виртуального окружения (рекомендуется)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Шаг 4: Установка зависимостей

```bash
pip install -r requirements.txt
```

**Важно:** Для Playwright также нужно установить браузеры:

```bash
playwright install chromium
```

Это загрузит Chromium (~150 МБ) и установит необходимые системные зависимости.

### Шаг 5: Запуск парсера

```bash
python main.py
```

Результаты сохранятся в файл `fish_products.xlsx`

## 📁 Структура проекта

```
project/
├── main.py              # Точка входа
├── config.py            # Конфигурация магазинов и категорий
├── requirements.txt     # Зависимости
├── .env                 # Настройки (опционально)
├── models/
│   └── product.py       # Модель продукта
├── parsers/
│   ├── base_parser.py   # Базовый класс с обходом блокировок
│   ├── pyaterochka.py   # Парсер Пятерочки
│   ├── magnit.py        # Парсер Магнита
│   ├── perekrestok.py   # Парсер Перекрестка
│   ├── lenta.py         # Парсер Ленты
│   ├── auchan.py        # Парсер Ашана
│   └── okey.py          # Парсер Окей
└── utils/
    └── export.py        # Экспорт в Excel
```

## ⚙️ Настройка

### Файл `.env` (опционально)

Создайте файл `.env` в корне проекта для настройки (можно скопировать из `.env.example`):

```env
# Файл вывода результатов
OUTPUT_FILE=fish_products.xlsx

# Задержка между запросами в секундах (рекомендуется 2-5)
REQUEST_DELAY=3

# Таймаут запроса в секундах
REQUEST_TIMEOUT=30

# Магазины для парсинга (через запятую без пробелов)
# Доступные: pyaterochka, magnit, perekrestok, lenta, auchan, okey
# Рекомендация: начните с pyaterochka,magnit,perekrestok
STORES=pyaterochka,magnit,perekrestok
```

> **Примечание:** Если файл `.env` не создан, используются значения по умолчанию из `config.py`.

### Выбор магазинов

Есть два способа выбрать магазины для парсинга:

**Способ 1: Через файл `.env`** (рекомендуется)
```env
STORES=pyaterochka,magnit,perekrestok
```

**Способ 2: В файле `config.py`**
```python
STORES = [
    "pyaterochka",    # Пятерочка - работает лучше всего
    "magnit",         # Магнит - требует JS рендеринг
    "perekrestok",    # Перекресток - средняя доступность
    # "lenta",        # Лента - может требовать авторизации
    # "auchan",       # Ашан - может требовать авторизации
    # "okey"          # Окей - могут быть SSL проблемы
]
```

### Визуальный режим (отладка)

По умолчанию парсер работает в **визуальном режиме** — вы видите окно браузера во время работы. Это полезно для отладки и понимания процесса.

Для изменения откройте `main.py` и измените переменную:

```python
VISUAL_MODE = True   # Показывать окно браузера (медленнее, но наглядно)
VISUAL_MODE = False  # Работать в фоновом режиме (быстрее)
```

## 🛠️ Решение проблем

### Ошибка: `ModuleNotFoundError: No module named 'curl_cffi'`

```bash
pip install --upgrade curl-cffi
```

### Ошибка: SSL Handshake Failure (Окей)

Проблема с SSL сертификатами. Попробуйте:

```bash
# Обновить сертификаты
pip install --upgrade certifi
```

Или исключите Окей из парсинга в `config.py`.

### Ошибка: 401 Unauthorized (Лента, Ашан)

Эти сайты требуют авторизации. Варианты решения:

1. **Исключить из парсинга** (рекомендуется):
   ```python
   STORES = ["pyaterochka", "magnit", "perekrestok"]
   ```

2. **Использовать cookies** (продвинутый):
   - Откройте сайт в браузере
   - Войдите в аккаунт
   - Скопируйте cookies
   - Добавьте в парсер

### Ошибка: 0 товаров найдено

1. Проверьте, что запускаете с **домашнего IP** (не сервер/VPS)
2. Увеличьте задержку в `.env`: `REQUEST_DELAY=5`
3. Попробуйте парсить по одному магазину

### Ошибка: BeautifulSoup не находит элементы

Селекторы сайтов меняются. Проверьте актуальные селекторы:
1. Откройте сайт в браузере
2. F12 → Elements
3. Найдите классы карточек товаров
4. Обновите селекторы в файле парсера

## 📊 Выходные данные

Файл `fish_products.xlsx` содержит следующие поля:

| Поле | Описание | Пример |
|------|----------|--------|
| name | Название товара | "Семга охлажденная стейк" |
| price | Цена (руб) | 899.99 |
| store | Магазин | "pyaterochka" |
| url | Ссылка на товар | "https://5ka.ru/..." |
| category | Категория | "Рыба и морепродукты" |
| brand | Бренд | "Russian Fish" |
| weight | Вес/объём | "500 г" |
| image_url | URL изображения товара | "https://..." |
| description | Описание товара | "Свежая семга..." |
| scraped_at | Время парсинга | "2024-01-15T10:30:00" |

После завершения парсинга в консоль выводится топ-20 лучших предложений по цене.

## 🔧 Для разработчиков

### Playwright - продвинутый парсинг

Для сайтов со сложной защитой используется **Playwright** - это бесплатный open-source инструмент, который:

- ✅ Запускает настоящий браузер Chromium
- ✅ Выполняет весь JavaScript как реальный пользователь
- ✅ Обходит детекцию автоматизации
- ✅ Делает скриншоты страниц
- ✅ Сохраняет cookies и сессии
- ✅ Работает локально на вашем компьютере

**Пример использования:**

```python
from parsers.playwright_parser import PlaywrightParser

parser = PlaywrightParser("Магазин", "https://site.ru")

# Запуск браузера (headless=False покажет окно браузера)
await parser.start_browser(headless=False)

# Загрузка страницы с полным рендерингом
html = await parser.fetch_page_playwright("https://site.ru/catalog")

# Скриншот для отладки
await parser.screenshot("page.png")

# Извлечение данных по селектору
price = await parser.extract_with_playwright(
    url="https://site.ru/product/1",
    selector=".price-value",
    attribute=None  # None для текста, или укажите атрибут
)

# Закрытие
await parser.close()
```

**Режим отладки:** Чтобы видеть браузер в действии, используйте `headless=False`:
```python
await parser.start_browser(headless=False)
```

Это особенно полезно при разработке и отладке селекторов.

### Добавление нового магазина

1. Создайте файл `parsers/newstore.py`:
```python
from typing import List
from models.product import FishProduct
from parsers.base_parser import BaseParser

class NewstoreParser(BaseParser):
    def __init__(self):
        super().__init__("Название", "https://site.ru")
        self.categories = ["https://site.ru/catalog/fish"]
    
    def get_category_urls(self) -> List[str]:
        return self.categories
    
    async def parse_fish_products(self) -> List[FishProduct]:
        # Ваша логика парсинга
        pass
```

2. Добавьте в `main.py`:
```python
from parsers.newstore import NewstoreParser
PARSERS["newstore"] = NewstoreParser
```

3. Добавьте категории в `config.py`

### Логирование

Парсер использует библиотеку **loguru** для логирования:

- **Консоль**: выводятся информационные сообщения об процессе парсинга
- **Файл `parser.log`**: детальные логи для отладки (rotation каждые 10 МБ)

Логи содержат:
- Время запуска и завершения парсинга по каждому магазину
- Количество найденных товаров
- Ошибки и исключения с полным traceback

### Изменение селекторов

Откройте файл парсера и найдите строки с `soup.select()`:

```python
# Было
product_cards = soup.select('div[class*="product"]')

# Стало (пример)
product_cards = soup.select('article.card-product')
```

## 📞 Поддержка

Если вы столкнулись с проблемами:

1. Проверьте [секцию решения проблем](#-решение-проблем)
2. Изучите логи в файле `parser.log`
3. Убедитесь, что запускаете с домашнего IP (не VPS/сервер)
4. Попробуйте запустить в визуальном режиме (`VISUAL_MODE = True`)

## 📝 Лицензия

MIT
