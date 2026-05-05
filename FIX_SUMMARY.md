# 🛠 Исправление ошибок ParserRiba

## ✅ Что было исправлено

### 1. Ошибка `'AntiBotConfig' object has no attribute 'get'`

**Проблема:** В коде использовался метод `.get()` для объекта `AntiBotConfig`, который является Pydantic моделью, а не словарем.

**Решение:** Все обращения к полям `anti_bot` заменены на использование `getattr()`:

```python
# Было (ошибка):
if self.kb.anti_bot.get("requires_scrolling"):

# Стало (работает):
strategies = getattr(self.kb.anti_bot, 'strategies', []) or []
if 'scrolling' in strategies:
```

**Измененные файлы:**
- `/workspace/parsers/base_parser.py` - обновлены методы `_init_strategies()`, `_init_policies()`, `fetch_page()`, `parse_category()`, `parse_all_categories()`

### 2. Ошибка инициализации стратегий

**Проблема:** Стратегии (`ScrollStrategy`, `PaginationStrategy`, etc.) требовали объект `page` при инициализации, но создавались в конструкторе парсера до запуска браузера.

**Решение:** Изменена логика инициализации стратегий:
- Теперь стратегии не создаются в конструкторе
- Сохраняется только конфигурация (`_strategies_config`)
- Стратегии будут создаваться динамически при наличии страницы

### 3. Ошибка `PoliciesEngine.add_policy()` с неправильными аргументами

**Проблема:** Вызывался метод с именованными аргументами `status_code`, `action`, которые не существуют в сигнатуре метода.

**Решение:** Использован правильный API `PoliciesEngine`:
```python
from policies.engine import PolicyRule, ErrorType, ActionType

self.policy_engine.add_policy(PolicyRule(
    error_types=[ErrorType.CAPTCHA],
    actions=[ActionType.SWITCH_TO_PLAYWRIGHT, ActionType.WAIT_AND_RETRY],
    max_retries=1,
    delay_between_retries=5.0,
    priority=15
))
```

---

## 🦊 Camoufox - Проблема с местом на диске

**Ошибка:** `[Errno 28] No space left on device`

**Причина:** Camoufox требует ~700 МБ для загрузки браузера Firefox, но на диске доступно только 168 МБ.

**Решения для локального запуска (Windows):**

### Вариант 1: Освободить место на диске
```cmd
# Очистить временные файлы
cleanmgr

# Удалить старые загрузки
del /Q %USERPROFILE%\Downloads\*.tmp
```

### Вариант 2: Использовать Playwright вместо Camoufox
В файле `parsers/pyaterochka.py` измените параметр `headless`:
```python
super().__init__(
    store_name=shop_name,
    base_url="https://5ka.ru",
    headless=False,  # Видимый браузер для прохождения капчи
    region=region or "77"
)
```

### Вариант 3: Запустить с уже установленным Camoufox
Если у вас есть другой диск с большим количеством места:
```cmd
set CAMOUFOX_CACHE=D:\cache\camoufox
python main.py --store pyaterochka
```

---

## 🚀 Инструкция по запуску на Windows

### 1. Активация виртуального окружения
```cmd
cd C:\Путь\К\Проекту\ParserRIba
env\Scripts\activate
```

### 2. Проверка установки
```cmd
python --version
pip list | findstr camoufox
pip list | findstr playwright
```

### 3. Запуск парсинга
```cmd
# Список магазинов
python main.py --list-stores

# Запуск Пятерочки (видимый браузер для капчи)
python main.py --store pyaterochka --log-level INFO

# Запуск с отладкой
python main.py --store pyaterochka --log-level DEBUG
```

### 4. Если Camoufox не устанавливается из-за места
Используйте резервный вариант с Playwright - он уже установлен и требует меньше места.

---

## 📊 Текущий статус

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| KB Loader | ✅ Работает | Загружает селекторы, headers, anti-bot config |
| BaseParser | ✅ Исправлен | Все `.get()` заменены на `getattr()` |
| Strategies | ✅ Исправлены | Ленивая инициализация |
| Policies | ✅ Исправлены | Правильный API `PolicyRule` |
| Camoufox | ⚠️ Требует места | Нужно 700 МБ на диске |
| Playwright | ✅ Готов | Альтернатива Camoufox |

---

## 🎯 Следующие шаги

1. **На Windows:** Освободить место на диске или использовать Playwright
2. **Протестировать парсинг:** Запустить с видимым браузером для прохождения капчи
3. **Проверить результат:** Убедиться, что товары парсятся корректно
