# 📋 План реализации интеграции Camoufox в ParserRIba

**Дата создания:** 2025-01-XX  
**Статус:** В процессе  
**Ответственный:** AI Assistant

---

## 🎯 Цель

Полная интеграция библиотеки **Camoufox** (современный браузер для обхода анти-бот защиты) вместо текущего Playwright/curl-cffi стека.

---

## ✅ Выполнено (Этап 0 - Подготовка)

### Сделано:
1. ✅ Изучена структура репозитория `/workspace`
2. ✅ Проанализированы все ключевые файлы:
   - `parsers/base_parser.py` - базовый парсер
   - `utils/session_manager.py` - менеджер сессий
   - `utils/fingerprint.py` - генерация отпечатков
   - `models/schemas.py` - Pydantic модели
   - `requirements.txt` - зависимости
   - `strategies/scroll_strategy.py` - стратегии скроллинга
   - `utils/logger.py` - система логирования
3. ✅ Создан этот файл плана (`IMPLEMENTATION_PLAN.md`)

---

## 📍 Текущий этап: Этап 1 - Базовая интеграция Camoufox

### Задачи этапа 1 (Низкая сложность):

#### 1.1 Playwright-совместимый запуск ⭐
- **Файл:** `parsers/base_parser.py`
- **Задача:** Заменить `browser.new_page()` на `Camoufox().new_page()`
- **Статус:** ⏳ Ожидает выполнения
- **Ссылка:** README.md#python-usage

#### 1.4 Блокировка изображений/ресурсов ⭐
- **Файл:** `utils/session_manager.py`
- **Задача:** Добавить `block_images=True`, `block_webgl=True` в опции запуска
- **Статус:** ⏳ Ожидает выполнения
- **Ссылка:** README.md#capabilities

#### 1.5 Human-like курсор ⭐
- **Файл:** `strategies/scroll_strategy.py`
- **Задача:** Включить `humanize=True` в Camoufox (C++ реализация надёжнее)
- **Статус:** ⏳ Ожидает выполнения
- **Ссылка:** README.md#stealth-overview

---

## 📍 Этап 2 - Средняя сложность

### Задачи этапа 2:

#### 2.1 Автоматическая генерация отпечатков ⭐⭐
- **Файл:** `utils/session_manager.py`
- **Задача:** Использовать встроенный BrowserForge через параметр `config={}`
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#fingerprint-injection

#### 2.2 Согласование geoip + прокси ⭐⭐
- **Файл:** `parsers/base_parser.py`, `config.yaml`
- **Задача:** Добавить параметр `geoip=True` при инициализации
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#geoip

#### 2.3 Шрифты под ОС + анти-фингерпринтинг ⭐⭐
- **Файл:** `utils/fingerprint.py`
- **Задача:** Использовать встроенную систему шрифтов Camoufox
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#anti-font-fingerprinting

#### 2.4 Виртуальный дисплей для headful на сервере ⭐⭐
- **Файл:** `utils/session_manager.py`
- **Задача:** Добавить `headless="virtual"` для Linux-серверов
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#python-interface

#### 2.5 Загрузка аддонов (uBlock) ⭐⭐
- **Файл:** `parsers/base_parser.py`
- **Задача:** Передать `addons=["path/to/ublock"]` при инициализации
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#addons

#### 2.6 Структурированные логи для GUI ⭐⭐
- **Файл:** `utils/logger.py`, `launcher/controllers/log_streamer.py`
- **Задача:** Добавить JSON-логи для LogStreamer в лаунчере
- **Статус:** ⏳ Не начато (требуется создать launcher/)
- **Примечание:** Внутренняя доработка

#### 2.7 Экспорт метрик (время, блокировки) ⭐⭐
- **Файл:** `models/schemas.py`, `utils/export.py`
- **Задача:** Добавить сбор метрик в ParseResult
- **Статус:** ⏳ Не начато
- **Примечание:** Внутренняя доработка

---

## 📍 Этап 3 - Высокая сложность

### Задачи этапа 3:

#### 3.1 WebRTC / Canvas / WebGL spoofing ⭐⭐⭐
- **Файл:** `utils/fingerprint.py`
- **Задача:** Включить через `config={"webgl": {...}}`
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#fingerprint-spoofing

#### 3.2 Пер-контекстная ротация (alpha) ⭐⭐⭐
- **Файл:** `requirements.txt`, `parsers/base_parser.py`
- **Задача:** Использовать пакет `cloverlabs-camoufox` вместо `camoufox`
- **Статус:** ⏳ Не начато
- **Ссылка:** README.md#making-full-use

---

## 📊 Итоговая таблица статуса

| № | Функция | Статус | Сложность | Файлы |
|---|---------|--------|-----------|-------|
| 1 | Playwright-совместимый запуск | ⏳ Ожидает | ⭐ | parsers/base_parser.py |
| 2 | Автогенерация отпечатков | ⏳ Не начато | ⭐⭐ | utils/session_manager.py |
| 3 | GeoIP + прокси | ⏳ Не начато | ⭐⭐ | parsers/base_parser.py, config.yaml |
| 4 | Блокировка ресурсов | ⏳ Ожидает | ⭐ | utils/session_manager.py |
| 5 | Human-like курсор | ⏳ Ожидает | ⭐ | strategies/scroll_strategy.py |
| 6 | WebRTC/Canvas/WebGL | ⏳ Не начато | ⭐⭐⭐ | utils/fingerprint.py |
| 7 | Шрифты + анти-фингерпринт | ⏳ Не начато | ⭐⭐ | utils/fingerprint.py |
| 8 | Пер-контекстная ротация | ⏳ Не начато | ⭐⭐⭐ | requirements.txt, parsers/base_parser.py |
| 9 | Виртуальный дисплей | ⏳ Не начато | ⭐⭐ | utils/session_manager.py |
| 10 | Аддоны (uBlock) | ⏳ Не начато | ⭐⭐ | parsers/base_parser.py |
| 11 | JSON-логи для GUI | ⏳ Не начато | ⭐⭐ | utils/logger.py |
| 12 | Экспорт метрик | ⏳ Не начато | ⭐⭐ | models/schemas.py, utils/export.py |

---

## 🔧 Следующие шаги

1. **Немедленно:** Начать выполнение задач Этапа 1 (низкая сложность)
2. **После Этапа 1:** Протестировать базовую работу Camoufox
3. **Затем:** Перейти к Этапу 2 (средняя сложность)
4. **В конце:** Реализовать Этап 3 (высокая сложность)

---

## 📝 Примечания

- Все изменения должны быть обратно совместимы
- Требуется тестирование после каждого этапа
- Логирование всех изменений для отладки
- Сохранение текущей функциональности Playwright как fallback

