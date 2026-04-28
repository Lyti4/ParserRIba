# Парсер цен на рыбные товары

## 📋 Описание

Парсер собирает цены на рыбные товары из крупнейших российских сетей:
- **Пятерочка** (5ka.ru)
- **Магнит** (magnit.ru)
- **Перекресток** (perekrestok.ru)
- **Лента** (lenta.com)
- **Ашан** (auchan.ru)
- **Окей** (okey.ru)

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

Создайте файл `.env` в корне проекта для настройки:

```env
# Файл вывода
OUTPUT_FILE=fish_products.xlsx

# Задержка между запросами (секунды)
REQUEST_DELAY=3

# Таймаут запроса (секунды)
REQUEST_TIMEOUT=30

# Магазины для парсинга (через запятую)
# STORES=pyaterochka,magnit,perekrestok
```

### Выбор магазинов

Откройте `config.py` и измените список магазинов:

```python
STORES = [
    "pyaterochka",    # Пятерочка - работает лучше всего
    "magnit",         # Магнит - требует JS рендеринг
    "perekrestok",    # Перекресток - средняя доступность
    # "lenta",        # Лента - требует авторизации
    # "auchan",       # Ашан - требует авторизации
    # "okey"          # Окей - могут быть SSL проблемы
]
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

Файл `fish_products.xlsx` содержит:

| Поле | Описание |
|------|----------|
| name | Название товара |
| price | Цена (руб) |
| store | Магазин |
| url | Ссылка на товар |
| category | Категория |
| brand | Бренд |
| weight | Вес/объём |
| scraped_at | Время парсинга |

## 🔧 Для разработчиков

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

### Изменение селекторов

Откройте файл парсера и найдите строки с `soup.select()`:

```python
# Было
product_cards = soup.select('div[class*="product"]')

# Стало (пример)
product_cards = soup.select('article.card-product')
```

## 📝 Лицензия

MIT
