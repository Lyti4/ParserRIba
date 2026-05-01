# 📘 Knowledge Base: Перекресток (perekrestok.ru)

## ℹ️ Общая информация

- **Название сети**: Перекресток
- **Базовый URL**: `https://perekrestok.ru`
- **Тип защиты**: Высокая (Cloudflare, капча при первом посещении)
- **Требуется JS**: Да (обязательно, каталог полностью динамический)
- **Региональность**: Да, зависит от региона доставки

---

## 🔗 URLs категорий

### Основные категории (рыба и морепродукты)

| Категория | URL | Примечание |
|-----------|-----|------------|
| Каталог (основная) | `https://perekrestok.ru/catalog` | Вход в каталог |
| Главная | `https://perekrestok.ru` | Для получения cookies |

**Примечание**: Перекресток использует автоматический поиск категорий через обход каталога, а не прямые ссылки на категории.

### Дополнительные URL

- **Карточка товара**: `https://perekrestok.ru/product/{product_id}`
- **API эндпоинты** (потенциально):
  - `GET https://perekrestok.ru/api/v4/products/` - список товаров
  - Параметры: `categoryId`, `page`, `limit`, `sort`, `filters`

---

## 🎯 CSS Селекторы

### Карточка товара (Product Card)

```css
/* Приоритет по порядку */
div[class*="product-card"]
div[class*="ProductCard"]
article[class*="product"]
div[data-product-id]
div[class*="catalog-item"]
div[class*="good-item"]
li[class*="product"]
.product-item
.good-item
.catalog-item
```

### Название товара (Name)

```css
h3
[class*="name"]
[class*="title"]
a[href*="/product/"]
[data-name]
.product-title
.product-name
```

### Цена (Price)

```css
[class*="price"]
[class*="cost"]
.current-price
.price-value
[data-price]
.price-current
```

### Старая цена (Old Price) - опционально

```css
[class*="old-price"]
[class*="discount"]
.was-price
[class*="strikethrough"]
.price-old
.price-previous
```

### Ссылка на товар (Product Link)

```css
a[href*="/product/"]
.card-link
.product-link
[data-testid="product-link"]
.product-url
```

### Вес/Объем (Weight)

```css
[class*="weight"]
[class*="volume"]
[data-weight]
.product-weight
.unit
.weight-value
```

### Бренд (Brand)

```css
[class*="brand"]
[class*="manufacturer"]
[data-brand]
.product-brand
.maker-name
.brand-name
```

### Изображение (Image)

```css
img.product-image
[data-src]
.picture img
[class*="image"] img
.product-img
.product-picture
```

---

## 🌐 Заголовки запросов (Headers)

### Стандартные заголовки

```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
```

### Специфичные заголовки для Перекрестка

```python
{
    # Перекресток может требовать указания региона
    'X-Region': '77',  # Москва
    'X-Delivery-Address': 'Moscow',
}
```

### Cookies для региона

```python
{
    # Регион доставки (пример)
    'region_id': '77',
    'city': 'Moscow',
    'delivery_address': 'moscow',
}
```

---

## 🛡 Анти-бот защита

### Признаки блокировки (Block Triggers)

- **HTTP статусы**: 403, 429
- **Редиректы**: На страницу `/captcha` или `/check`
- **Слова в HTML**: 
  - "Проверка браузера"
  - "CAPTCHA"
  - "Access denied"
  - "Forbidden"
  - "Подтвердите, что вы человек"
- **Изменения в DOM**: Появление iframe с капчей (Cloudflare Turnstile)

### Стратегии обхода

1. **Impersonate профиль**: `chrome124` (наиболее стабильный)
2. **Задержка перед запросом**: 3-5 секунд между страницами
3. **Ротация User-Agent**: Менять каждые 10-15 запросов
4. **Использование Playwright**: ОБЯЗАТЕЛЬНО для Перекрестка
5. **Человеческое поведение**: 
   - Скроллинг страницы (human_scroll)
   - Паузы между действиями
   - Решение капчи при первом запуске

### CAPTCHA

- **Тип капчи**: Cloudflare Turnstile / reCAPTCHA v2
- **Метод обхода**: 
  - Сохранение cookies сессии (ОБЯЗАТЕЛЬНО)
  - Ручное решение при первом запуске (90 секунд пауза)
  - Playwright stealth режим
  - Файл сессии: `perekrestok_session.json`
- **Сохранение сессии**: КРИТИЧНО важно для повторных запусков

---

## 📝 Особенности и заметки

### Технические нюансы

- [x] Требуется скроллинг для lazy loading товаров (ОБЯЗАТЕЛЬНО)
- [x] Пагинация через кнопку "Показать еще" или бесконечный скролл
- [x] Цены зависят от региона
- [ ] Некоторые товары доступны только по карте лояльности
- [x] Динамическая подгрузка через AJAX
- [x] Автоматический поиск категорий через обход каталога
- [x] Фильтрация товаров по ключевым словам (рыба, морепродукты)

### Поведенческие паттерны

- **Максимум запросов в минуту**: ~8-10 (осторожно!)
- **Рекомендуемая задержка**: 3-5 секунд между страницами
- **Время жизни сессии**: ~30 минут
- **Лимит товаров на странице**: Обычно 24-48 товаров

### Известные проблемы

1. **Проблема**: Капча при первом посещении (Cloudflare Turnstile)
   **Решение**: Пауза 90 секунд для ручного решения, сохранение cookies

2. **Проблема**: Блокировка при частых запросах (403)
   **Решение**: Использовать сохраненную сессию, увеличить задержки

3. **Проблема**: Не все товары видны без скролла
   **Решение**: Реализовать human_scroll стратегию (5 прокруток минимум)

4. **Проблема**: Товары не только рыбные в общем каталоге
   **Решение**: Использовать фильтрацию по ключевым словам (FISH_KEYWORDS)

---

## 🧪 Тестовые данные

### Пример URL товара

`https://perekrestok.ru/product/12345678/ryba-losos-file-ohlazhdennoe-1kg`

### Ожидаемые данные парсинга

```json
{
  "name": "Лосось филе охлажденное, 1 кг",
  "price": 1299,
  "old_price": 1599,
  "weight": "1 кг",
  "brand": "Каждый День",
  "url": "https://perekrestok.ru/product/12345678",
  "image_url": "https://perekrestok.ru/media/products/12345678.jpg"
}
```

---

## 📅 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2024-01-XX | Начальная версия на основе parsers/perekrestok.py | AI Assistant |
| ... | ... | ... |

---

> **Примечание**: Этот файл должен обновляться при каждом изменении структуры сайта или обнаружении новых особенностей парсинга.
> 
> **Текущий статус**: ✅ Базовые селекторы извлечены из кода, требуется верификация актуальности
> 
> **Критично**: 
> - Обязательно использование Playwright (не работает через curl-cffi)
> - Обязательно сохранение сессии (cookies) после первого запуска
> - Обязателен human_scroll для полной загрузки товаров
> - Используется автоматическая фильтрация по ключевым словам
