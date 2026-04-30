# 🛠️ План исправления парсера ParserRIba

## 🎯 Цель
Сделать парсер стабильным с минимальным участием человека (только капча/логин при необходимости).

## ✅ Выполненные исправления

### 1. `parsers/base_parser.py` — Улучшенный `fetch_page()`

**Что изменено:**
- Добавлены дополнительные заголовки для маскировки (`Sec-Ch-Ua`, `Sec-Ch-Ua-Mobile`, `Sec-Ch-Ua-Platform`, `Priority`)
- Автоматический выбор профиля браузера в зависимости от сайта:
  - `5ka.ru` → `chrome124`
  - `magnit.ru` → `chrome120`
  - `lenta.com`, `auchan.ru` → `chrome124`
- Обработка ответа 403 с автоматической повторной попыткой с другим профилем
- Обработка ответа 401 с добавлением заголовков региона (`X-Region: 77`, `X-Location: Moscow`)
- Увеличен таймаут до 45 секунд

### 2. `parsers/base_parser.py` — Улучшенный `fetch_page_playwright()`

**Что изменено:**
- Увеличены задержки для лучшей имитации человека (1.5-3.5 сек перед переходом, 3.0-5.0 сек после)
- Изменён режим ожидания на `networkidle` для полной загрузки ресурсов
- Увеличен таймаут ожидания селектора до 15 секунд
- Добавлено ожидание `domcontentloaded` после прокрутки
- При ошибке теперь возвращается текущее содержимое страницы вместо `None`

### 3. `parsers/magnit.py` — Обновлённые URL категорий

**Старые URL:**
```python
"https://magnit.ru/catalog/ryba-moreprodukty/",
"https://magnit.ru/catalog/ryba-kopchenaya-solenaya/",
"https://magnit.ru/catalog/konservy-rybnye/",
```

**Новые URL:**
```python
"https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/",
"https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-svezhaya/",
"https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-kopchenaya/",
"https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/konservy/",
```

### 4. `parsers/lenta.py` — Добавлены заголовки региона

Добавлен метод `_get_headers()`:
```python
def _get_headers(self) -> dict:
    """Добавляем заголовки региона для Ленты"""
    headers = super()._get_headers()
    headers.update({'X-Region': '77', 'X-Location': 'Moscow'})
    return headers
```

### 5. `parsers/auchan.py` — Добавлены заголовки региона

Аналогично Ленте, добавлен метод `_get_headers()` с заголовками региона.

### 6. `requirements.txt` — Обновлённые версии

**Обновлено:**
- `curl-cffi>=0.6.0` → `curl-cffi>=0.7.0`
- `playwright>=1.40.0` → `playwright>=1.42.0`

### 7. `test_fix.py` — Тестовый скрипт

Создан новый файл для проверки работоспособности исправлений.

## 🚀 Как применить исправления

### Вариант A: Если вы уже клонировали репозиторий

1. **Обновите зависимости:**
   ```bash
   cd ParserRIba
   venv\Scripts\activate  # для Windows
   pip install -r requirements.txt --upgrade
   playwright install chromium
   ```

2. **Запустите тест:**
   ```bash
   python test_fix.py
   ```

3. **Если тест успешен, запустите парсер:**
   ```bash
   python main.py
   ```

### Вариант B: Если начинаете с нуля

```bash
git clone https://github.com/Lyti4/ParserRIba.git
cd ParserRIba
python -m venv venv
venv\Scripts\activate  # для Windows
pip install -r requirements.txt
playwright install chromium
python test_fix.py
python main.py
```

## 🧪 Проверка результатов

После запуска `test_fix.py` вы должны увидеть:

```
==================================================
ТЕСТ УЛУЧШЕННОГО ПАРСЕРА PARSER RIBA
==================================================

📋 ТЕСТ 1: Прямой HTTP запрос
🧪 Тестируем запрос к https://5ka.ru/cat/ryba_i_moreprodukty...
✅ Статус: 200
📏 Длина ответа: XXXXX байт
✅ Успех! Страница загружена корректно.

📋 ТЕСТ 2: Полный парсинг
🧪 Тестируем парсер Пятёрочки...
✅ Найдено товаров: XX

📦 Первые 3 товара:
  1. Название товара 1 - XXX ₽
  2. Название товара 2 - XXX ₽
  3. Название товара 3 - XXX ₽

==================================================
ИТОГИ ТЕСТОВ:
  Тест 1 (HTTP запрос): ✅ PASS
  Тест 2 (Парсинг): ✅ PASS
==================================================

🎉 Все тесты пройдены! Можно запускать main.py
```

## 🔍 Отладка

Если что-то не работает:

1. **Включите визуальный режим** в `.env`:
   ```
   VISUAL_MODE=True
   ```

2. **Проверьте логи** — они пишутся в консоль и файл `parser.log`

3. **Попробуйте другой профиль браузера** — измените в `base_parser.py` значение по умолчанию

4. **Проверьте IP** — некоторые сайты блокируют дата-центры

## 📝 Примечания

- Все изменения обратно совместимы
- Парсер теперь лучше обходит защиты от ботов
- Задержки увеличены для стабильности, но парсинг стал медленнее
- Для продакшена можно уменьшить задержки в `config.py`
