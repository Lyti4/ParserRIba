# 📋 Шаблон Knowledge Base для магазина

## ℹ️ Общая информация

- **Название сети**: [Название]
- **Базовый URL**: `https://example.ru`
- **Тип защиты**: [Cloudflare / Akamai / None / Custom]
- **Требуется JS**: [Да/Нет]
- **Региональность**: [Да/Нет, какие регионы]

---

## 🔗 URLs категорий

### Основные категории (рыба и морепродукты)

| Категория | URL | Примечание |
|-----------|-----|------------|
| Рыба и морепродукты | `https://...` | Основная категория |
| Копченая рыба | `https://...` | Подкатегория |
| Консервы | `https://...` | Подкатегория |
| Икра и деликатесы | `https://...` | Подкатегория |

### Дополнительные URL

- **API эндпоинты**: (если есть скрытые API)
  - `GET https://.../api/products?category=fish`
  - Параметры: `page`, `limit`, `sort`
  
- **URL для пагинации**: (если отличается от стандартного)
  - Паттерн: `https://.../catalog/fish?page={page}`

---

## 🎯 CSS Селекторы

### Карточка товара (Product Card)

```css
/* Основные селекторы (приоритет по порядку) */
div[data-testid="product-card"]
div.catalog-item
article.product-card
[class*="product-card"]
[class*="card"]
```

### Название товара (Name)

```css
h3
[class*="name"]
[class*="title"]
a[href*="/prod/"]
[data-name]
```

### Цена (Price)

```css
[class*="price"]
[class*="cost"]
span[data-testid*="price"]
[data-price]
.current-price
.price-value
```

### Старая цена (Old Price) - опционально

```css
[class*="old-price"]
[class*="discount"]
.was-price
```

### Ссылка на товар (Product Link)

```css
a[href*="/prod/"]
a[href*="/product/"]
.card-link
```

### Вес/Объем (Weight)

```css
[class*="weight"]
[class*="volume"]
[data-weight]
.product-weight
```

### Бренд (Brand)

```css
[class*="brand"]
[class*="manufacturer"]
[data-brand]
.product-brand
```

### Изображение (Image)

```css
img.product-image
[data-src]
.picture img
```

---

## 🌐 Заголовки запросов (Headers)

### Стандартные заголовки

```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
```

### Специфичные заголовки для этого магазина

```python
{
    'X-Region': '77',  # Москва
    'X-Location': 'Moscow',
    # Другие специфичные заголовки...
}
```

### Cookies для региона

```python
{
    'region_id': '77',
    'city': 'Moscow',
    # Другие cookies...
}
```

---

## 🛡 Анти-бот защита

### Признаки блокировки (Block Triggers)

- **HTTP статусы**: 403, 429, 401
- **Редиректы**: На страницу капчи `/captcha`, `/check`
- **Слова в HTML**: 
  - "Проверка браузера"
  - "CAPTCHA"
  - "Access denied"
  - "Forbidden"
- **Изменения в DOM**: Появление iframe с капчей

### Стратегии обхода

1. **Impersonate профиль**: `chrome124`, `chrome120`, `safari15_3`
2. **Задержка перед запросом**: 2-5 секунд
3. **Ротация User-Agent**: Менять каждые N запросов
4. **Использование Playwright**: При обнаружении 403
5. **Человеческое поведение**: 
   - Скроллинг страницы
   - Случайные движения мыши (в browser mode)
   - Паузы между действиями

### CAPTCHA

- **Тип капчи**: [reCAPTCHA v2 / hCaptcha / Cloudflare Turnstile / Другая]
- **Метод обхода**: [Ручное решение / 2Captcha API / Обход через cookies]
- **Сохранение сессии**: Да/Нет (файл `session.json`)

---

## 📝 Особенности и заметки

### Технические нюансы

- [ ] Требуется скроллинг для lazy loading товаров
- [ ] Пагинация через кнопку "Показать еще"
- [ ] Цены зависят от региона (необходимо устанавливать регион)
- [ ] Некоторые товары доступны только по карте лояльности
- [ ] Динамическая подгрузка через AJAX

### Поведенческие паттерны

- **Максимум запросов в минуту**: ~10-15
- **Рекомендуемая задержка**: 2-4 секунды между страницами
- **Время жизни сессии**: ~30 минут

### Известные проблемы

1. **Проблема**: [Описание]
   **Решение**: [Как обходим]

2. **Проблема**: [Описание]
   **Решение**: [Как обходим]

---

## 🧪 Тестовые данные

### Пример URL товара

`https://example.ru/product/ryba-losos-filé-1kg-12345`

### Ожидаемые данные парсинга

```json
{
  "name": "Лосось филе охлажденное, 1 кг",
  "price": 1299,
  "old_price": 1599,
  "weight": "1 кг",
  "brand": "Каждый День",
  "url": "https://example.ru/product/...",
  "image_url": "https://example.ru/images/..."
}
```

---

## 📅 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| YYYY-MM-DD | Начальная версия | [Имя] |
| ... | ... | ... |

---

> **Примечание**: Этот файл должен обновляться при каждом изменении структуры сайта или обнаружении новых особенностей парсинга.
