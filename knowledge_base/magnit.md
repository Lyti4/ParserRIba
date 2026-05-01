# 📘 Knowledge Base: Магнит (magnit.ru)

## ℹ️ Общая информация

- **Название сети**: Магнит
- **Базовый URL**: `https://magnit.ru`
- **Тип защиты**: Умеренная (возможны 403 при частых запросах)
- **Требуется JS**: Частично (каталог работает, динамические элементы)
- **Региональность**: Да, зависит от региона доставки

---

## 🔗 URLs категорий

### Основные категории (рыба и морепродукты)

| Категория | URL | Примечание |
|-----------|-----|------------|
| Рыба и морепродукты | `https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/` | Основная категория |
| Копченая рыба | `https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-kopchenaya/` | Подкатегория |
| Рыбные консервы | `https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/konservy-rybnye/` | Консервированная продукция |

### Дополнительные URL

- **Карточка товара**: `https://magnit.ru/product/{product_id}`
- **API эндпоинты** (потенциально):
  - `GET https://magnit.ru/api/products/` - список товаров
  - Параметры: `category`, `page`, `size`, `sort`

---

## 🎯 CSS Селекторы

### Карточка товара (Product Card)

```css
/* Приоритет по порядку */
div[class*="product"]
div[class*="card"]
article[class*="product"]
[data-testid="product-card"]
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
```

### Цена (Price)

```css
[class*="price"]
[class*="cost"]
.current-price
.price-value
[data-price]
```

### Старая цена (Old Price) - опционально

```css
[class*="old-price"]
[class*="discount"]
.was-price
[class*="strikethrough"]
.price-old
```

### Ссылка на товар (Product Link)

```css
a[href*="/product/"]
.card-link
.product-link
[data-testid="product-link"]
```

### Вес/Объем (Weight)

```css
[class*="weight"]
[class*="volume"]
[data-weight]
.product-weight
.unit
```

### Бренд (Brand)

```css
[class*="brand"]
[class*="manufacturer"]
[data-brand]
.product-brand
.maker-name
```

### Изображение (Image)

```css
img.product-image
[data-src]
.picture img
[class*="image"] img
.product-img
```

---

## 🌐 Заголовки запросов (Headers)

### Стандартные заголовки

```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
```

### Специфичные заголовки для Магнита

```python
{
    # Магнит может требовать указания региона
    'X-Region': '77',  # Москва
}
```

### Cookies для региона

```python
{
    # Регион доставки (пример)
    'region': 'moscow',
    'city_id': '77',
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
- **Изменения в DOM**: Появление iframe с капчей

### Стратегии обхода

1. **Impersonate профиль**: `chrome120` (наиболее стабильный для magnit.ru)
2. **Задержка перед запросом**: 2-4 секунды между страницами
3. **Ротация User-Agent**: Менять каждые 10-15 запросов
4. **Использование Playwright**: При обнаружении 403 или капчи
5. **Человеческое поведение**: 
   - Скроллинг страницы
   - Паузы между действиями

### CAPTCHA

- **Тип капчи**: Вероятно собственная или Cloudflare
- **Метод обхода**: 
  - Сохранение cookies сессии
  - Ручное решение при первом запуске
  - Playwright stealth режим
- **Сохранение сессии**: Рекомендуется (`magnit_session.json`)

---

## 📝 Особенности и заметки

### Технические нюансы

- [x] Требуется скроллинг для lazy loading товаров
- [ ] Пагинация через кнопку "Показать еще" или номер страниц
- [x] Цены зависят от региона
- [ ] Некоторые товары доступны только по карте лояльности
- [x] Динамическая подгрузка через AJAX

### Поведенческие паттерны

- **Максимум запросов в минуту**: ~10-15
- **Рекомендуемая задержка**: 2-4 секунды между страницами категорий
- **Время жизни сессии**: ~30 минут
- **Лимит товаров на странице**: Обычно 24-48 товаров

### Известные проблемы

1. **Проблема**: Блокировка при частых запросах (403)
   **Решение**: Использовать Playwright fallback, увеличить задержки

2. **Проблема**: Две цены (обычная и по карте)
   **Решение**: Парсить обе цены, приоритет отдавать цене по карте

3. **Проблема**: Не все товары видны без скролла
   **Решение**: Реализовать human_scroll стратегию

---

## 🧪 Тестовые данные

### Пример URL товара

`https://magnit.ru/product/12345678/ryba-losos-file-1kg`

### Ожидаемые данные парсинга

```json
{
  "name": "Лосось филе охлажденное, 1 кг",
  "price": 1299,
  "old_price": 1599,
  "weight": "1 кг",
  "brand": "Каждый День",
  "url": "https://magnit.ru/product/12345678",
  "image_url": "https://magnit.ru/media/products/12345678.jpg"
}
```

---

## 📅 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2024-01-XX | Начальная версия на основе parsers/magnit.py | AI Assistant |
| ... | ... | ... |

---

> **Примечание**: Этот файл должен обновляться при каждом изменении структуры сайта или обнаружении новых особенностей парсинга.
> 
> **Текущий статус**: ✅ Базовые селекторы извлечены из кода, требуется верификация актуальности
