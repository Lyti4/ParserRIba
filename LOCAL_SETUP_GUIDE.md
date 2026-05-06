# 🚀 Инструкция по запуску ParserRiba локально

Полное руководство по установке и запуску парсера цен на рыбные товары.

---

## 📋 Требования

### Минимальные требования:
- **Python**: 3.10 или выше (протестировано на 3.12.10)
- **ОЗУ**: 4 ГБ минимум (8 ГБ рекомендуется для работы браузера)
- **Место на диске**: 1 ГБ свободного места
- **ОС**: Linux, macOS, Windows 10/11

### Для Camoufox (рекомендуется для сложных сайтов):
- **Дополнительно**: ~700 МБ для Firefox браузера
- **Ядро**: Linux с glibc 2.27+ или macOS

---

## 🔧 Шаг 1: Установка зависимостей

### 1.1 Клонирование репозитория

```bash
cd /workspace
# Если еще не клонировали:
# git clone https://github.com/Lyti4/ParserRIba.git
# cd ParserRIba
```

### 1.2 Создание виртуального окружения (рекомендуется)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

### 1.3 Установка Python пакетов

```bash
pip install -r requirements.txt
```

**Что установится:**
- `camoufox` (0.4.11) - Firefox с улучшенной маскировкой ✅
- `playwright` (1.44.0) - браузерная автоматизация
- `playwright-stealth` - скрытие автоматизации
- `aiohttp`, `curl-cffi` - HTTP клиенты
- `pydantic` - валидация данных
- `beautifulsoup4`, `lxml` - парсинг HTML
- `loguru` - логирование
- и другие зависимости

### 1.4 Установка браузеров

#### Для Playwright (Chromium):
```bash
playwright install chromium
```

#### Для Playwright (Firefox - опционально):
```bash
playwright install firefox
```

#### Для Camoufox:
Camoufox автоматически загружает Firefox при первом запуске. 
Ничего дополнительно устанавливать не нужно! ✅

Проверка установки:
```bash
python -c "from camoufox import Camoufox; print('✅ Camoufox готов')"
python -c "from playwright.async_api import async_playwright; print('✅ Playwright готов')"
```

---

## ⚙️ Шаг 2: Настройка конфигурации

### 2.1 Проверка config.yaml

Основной файл настроек уже существует: `/workspace/config.yaml`

**Важные параметры:**

```yaml
browser:
  headless: true          # false - видеть браузер, true - фоновый режим
  timeout: 30000          # таймаут в мс
  
anti_bot:
  random_delays: true     # случайные задержки между запросами
  min_delay: 1.0          # минимальная задержка (сек)
  max_delay: 3.0          # максимальная задержка (сек)

stores:
  pyaterochka:
    enabled: true         # включить/выключить магазин
    region_id: "77"       # Москва
  magnit:
    enabled: true
  lenta:
    enabled: true
    region: "msk"
  auchan:
    enabled: true
  okey:
    enabled: true
  perekrestok:
    enabled: false        # отключен (требует авторизации)
```

### 2.2 Настройка прокси (опционально)

Если нужны прокси, создайте файл `.env`:

```bash
cp .env.example .env  # если есть шаблон
```

Или добавьте в `config.yaml`:

```yaml
network:
  proxy_rotation: true
  proxy_list:
    - "http://user:pass@proxy1.com:8080"
    - "http://user:pass@proxy2.com:8080"
```

---

## 🏃 Шаг 3: Запуск парсера

### 3.1 Быстрый старт - один магазин

```bash
# Парсинг Пятерочки (рыба и морепродукты)
python main.py --store pyaterochka

# С указанием категории
python main.py --store pyaterochka --category "Рыба и морепродукты"

# С ограничением количества товаров
python main.py --store pyaterochka --limit 50
```

### 3.2 Парсинг нескольких магазинов

```bash
# Магнит и Лента одновременно
python main.py --store magnit lenta

# Все включенные магазины из config.yaml
python main.py
```

### 3.3 Полезные флаги

```bash
# Показать список доступных магазинов
python main.py --list-stores

# Отладочная информация
python main.py --store pyaterochka --log-level DEBUG

# Запуск с видимым браузером (не headless)
python main.py --store pyaterochka --no-headless

# Сохранение в другую папку
python main.py --store pyaterochka --output results/

# Выбор формата вывода (если реализовано)
python main.py --store pyaterochka --format json  # или csv, excel
```

### 3.4 Примеры команд

```bash
# Полный парсинг всех магазинов с подробным логом
python main.py --log-level INFO --output data/

# Только тест одного магазина с ограничением
python main.py --store auchan --category fish_frozen --limit 20 --log-level DEBUG

# Запуск без головы (видимый браузер для отладки)
python main.py --store pyaterochka --no-headless --log-level DEBUG
```

---

## 🦊 Использование Camoufox

Camoufox уже интегрирован в проект! Используйте его для сайтов с сильной защитой.

### Автоматическое использование

Парсер автоматически переключается на Camoufox при обнаружении блокировок.

### Ручное использование через код

Создайте файл `test_camoufox.py`:

```python
import asyncio
from parsers.camoufox_parser import CamoufoxParser

async def main():
    async with CamoufoxParser(
        store_name="pyaterochka",
        base_url="https://5ka.ru",
        headless=True,
        region="77"
    ) as parser:
        # Загрузка страницы
        html = await parser.fetch_page_camoufox(
            url="https://5ka.ru/catalog/ryba--251C13077/",
            wait_for_selector='div[data-testid="product-card"]',
            scroll_down=True
        )
        
        if html:
            print(f"✅ Страница загружена: {len(html)} символов")
            
            # Парсинг товаров
            products = await parser.parse_products_from_page()
            print(f"📦 Найдено товаров: {len(products)}")
            
            for p in products[:5]:
                print(f"  - {p.name}: {p.price} ₽")

if __name__ == "__main__":
    asyncio.run(main())
```

Запуск:
```bash
python test_camoufox.py
```

---

## 🐳 Запуск в Docker (альтернатива)

Если не хотите ставить зависимости локально:

```bash
# Сборка и запуск
docker-compose up --build

# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

Результаты сохранятся в папку `data/` или `output/`.

---

## 📂 Структура выходных данных

После парсинга данные сохраняются в:

```
data/
├── pyaterochka_20260105_143022.json
├── magnit_20260105_143145.json
└── lenta_20260105_143310.json
```

Формат JSON:
```json
[
  {
    "name": "Лосось филе охлажденное, 1 кг",
    "price": {"current": 1299.0, "old": 1599.0},
    "currency": "RUB",
    "category": "Рыба и морепродукты",
    "product_link": "https://5ka.ru/prod/12345",
    "image_url": "https://...",
    "in_stock": true,
    "shop": "pyaterochka",
    "timestamp": "2026-01-05T14:30:22"
  }
]
```

---

## 🛠 Решение проблем

### Ошибка: "Executable doesn't exist"

**Проблема**: Браузер Playwright не установлен или недостаточно места.

**Решение**:
```bash
# Переустановить браузер
playwright install chromium --force

# Или использовать Camoufox (он сам скачает Firefox)
python test_camoufox.py
```

### Ошибка: "ENOSPC: No space left on device"

**Проблема**: Закончилось место на диске.

**Решение**:
```bash
# Проверить место
df -h

# Очистить кэш pip
pip cache purge

# Удалить старые браузеры
rm -rf ~/.cache/ms-playwright
```

### Ошибка: "403 Forbidden" или капча

**Проблема**: Сайт заблокировал запрос.

**Решение**:
1. Увеличьте задержки в `config.yaml`:
   ```yaml
   anti_bot:
     min_delay: 3.0
     max_delay: 7.0
   ```

2. Запустите с видимым браузером для ручного прохождения капчи:
   ```bash
   python main.py --store pyaterochka --no-headless
   ```

3. Используйте Camoufox (лучшая маскировка):
   ```bash
   python test_camoufox.py
   ```

### Ошибка: "ImportError: camoufox"

**Проблема**: Camoufox не установлен.

**Решение**:
```bash
pip install camoufox
python -c "from camoufox import Camoufox; print('OK')"
```

### Тихий вывод (нет товаров)

**Проблема**: Селекторы устарели или сайт изменился.

**Решение**:
1. Проверьте логи с уровнем DEBUG:
   ```bash
   python main.py --store pyaterochka --log-level DEBUG
   ```

2. Обновите селекторы в `knowledge_base/pyaterochka.md`

3. Запустите в режиме отладки с видимым браузером:
   ```bash
   python main.py --store pyaterochka --no-headless --log-level DEBUG
   ```

---

## 🧪 Тестирование

Запуск тестов:

```bash
# Все тесты
pytest tests/ -v

# Только тесты конфигурации
pytest tests/test_kb_loader.py -v

# Тесты парсеров (дымовые)
pytest tests/test_parsers_smoke.py -v
```

---

## 📊 Мониторинг и логи

Логи сохраняются в:
- **Файл**: `logs/parser_riba.log`
- **Консоль**: Вывод во время выполнения

Просмотр логов в реальном времени:
```bash
tail -f logs/parser_riba.log
```

---

## 🎯 Рекомендации по использованию

### Для стабильного парсинга:

1. **Используйте headless=false** при первом запуске для прохождения капчи
2. **Настройте задержки** под конкретный магазин
3. **Сохраняйте профиль браузера** (уже настроено в PyaterochkaParser)
4. **Чередуйте магазины** чтобы не превышать лимиты
5. **Используйте Camoufox** для сайтов с сильной защитой

### Оптимальные настройки для разных магазинов:

| Магазин | Рекомендация | Задержка |
|---------|-------------|----------|
| Пятерочка | Playwright + профиль | 2-4 сек |
| Магнит | curl-cffi или Playwright | 1-3 сек |
| Лента | Camoufox | 3-5 сек |
| Ашан | Camoufox | 2-4 сек |
| О'Кей | Playwright | 2-3 сек |

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `cat logs/parser_riba.log`
2. Запустите с `--log-level DEBUG`
3. Создайте Issue на GitHub с:
   - Версией Python
   - Версиями пакетов (`pip list`)
   - Фрагментом лога с ошибкой
   - Командой которую запускали

---

## ✅ Чек-лист перед запуском

- [ ] Python 3.10+ установлен
- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] Браузеры установлены (`playwright install chromium`)
- [ ] Camoufox проверяется (`python -c "from camoufox import Camoufox"`)
- [ ] Config.yaml настроен
- [ ] Есть место на диске (>1 ГБ)
- [ ] Папка `logs/` существует
- [ ] Интернет соединение стабильно

**Готово! Можно запускать:**
```bash
python main.py --store pyaterochka
```

---

> **Дата обновления инструкции**: 2026-01-05  
> **Версия ParserRiba**: 1.0.0  
> **Протестировано на**: Python 3.12.10, Camoufox 0.4.11, Playwright 1.44.0
