# 📘 Knowledge Base: Пятерочка (5ka.ru)

## ℹ️ Общая информация

- **Название сети**: Пятерочка
- **Базовый URL**: `https://5ka.ru`
- **Тип защиты**: Умеренная (возможны 403 при частых запросах)
- **Требуется JS**: Частично (каталог работает, но некоторые элементы динамические)
- **Региональность**: Да, зависит от региона доставки

---

## 🔗 URLs категорий

### Основные категории (рыба и морепродукты) - обновлено 2026-05-04

| Категория | URL | Примечание |
|-----------|-----|------------|
| Рыба | `https://5ka.ru/catalog/ryba--251C13077/` | Основная категория |
| Морепродукты | `https://5ka.ru/catalog/moreprodukty--251C13078/` | Подкатегория |
| Котлеты и фарш | `https://5ka.ru/catalog/kotlety-farsh--251C13079/` | Полуфабрикаты |
| Икра и закуски | `https://5ka.ru/catalog/ikra-zakuski--251C13080/` | Деликатесы |

### Дополнительные URL

- **Карточка товара**: `https://5ka.ru/prod/{product_id}`
- **API эндпоинты** (потенциально):
  - `GET https://5ka.ru/api/v2/products/` - список товаров
  - Параметры: `direction`, `limit`, `offset`, `query`, `store`

---

## API Interception

- **allowed_hosts**:
  - `5ka.ru`
  - `5d.5ka.ru`
- **product_api_path_markers**:
  - `/api/catalog`
  - `/api/orders`
  - `/api/products`
  - `/api/search`
- **api_path_markers**:
  - `/api/`
- **challenge_markers**:
  - `xpvnsulc`
  - `captcha`
  - `challenge`
  - `antibot`
- **image_markers**:
  - `image/`
  - `.png`
  - `.jpg`
  - `.jpeg`
  - `.webp`
  - `.svg`
- **script_markers**:
  - `.js`

---

## 🎯 CSS Селекторы

### Карточка товара (Product Card)

```css
article[class*="Card"]
div[class*="product-card"]
[data-testid="product-card"]
.catalog-item
```

### Название товара (Name)

```css
h2[class*="name"]
[data-testid="product-name"]
.product-title
a[class*="link"]
```

### Цена (Price) - текущая цена

```css
span[class*="price"]
[data-testid="price-current"]
.current-price
.price-value
```

### Старая цена (Old Price) - опционально

```css
span[class*="old-price"], [data-testid="price-old"], .old-price, .price-old
```

### Ссылка на товар (Product Link)

```css
article[class*="Card"] a, div[class*="product-card"] a, [data-testid="product-card"] a, .catalog-item a
```

### Вес/Объем (Weight)

```css
span[class*="weight"], [data-testid="product-weight"], .product-weight, .unit
```

### Бренд (Brand)

```css
span[class*="brand"], [data-testid="product-brand"], .product-brand, .manufacturer
```

### Изображение (Image)

```css
img[class*="image"], [data-testid="product-image"], .product-image img, picture img
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

### Специфичные заголовки для Пятерочки

```python
{
    # Пятерочка может требовать указания региона
    'X-Region': '77',  # Москва
    # Cookie с регионом можно передать вручную
}
```

### Cookies для региона

```python
{
    # Регион доставки (пример)
    'delivery_zone': 'moscow',
    'region_id': '77',
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
  - "Слишком много запросов"
- **Изменения в DOM**: Появление iframe с капчей

### Стратегии обхода

1. **Impersonate профиль**: `chrome124` (наиболее стабильный)
2. **Задержка перед запросом**: 2-4 секунды между страницами
3. **Ротация User-Agent**: Менять каждые 10-15 запросов
4. **Использование Playwright**: При обнаружении 403 или капчи
5. **Человеческое поведение**: 
   - Скроллинг страницы вниз/вверх
   - Паузы между кликами
   - Случайные задержки

### CAPTCHA

- **Тип капчи**: Вероятно Cloudflare Turnstile или собственная
- **Метод обхода**: 
  - Сохранение cookies сессии
  - Ручное решение при первом запуске
  - Playwright stealth режим
- **Сохранение сессии**: Рекомендуется (`pyaterochka_session.json`)

---

## 📝 Особенности и заметки

### Технические нюансы

- [x] Требуется скроллинг для lazy loading товаров (не все товары загружаются сразу)
- [ ] Пагинация через кнопку "Показать еще" или номер страниц
- [x] Цены зависят от региона (необходимо устанавливать регион доставки)
- [ ] Некоторые товары доступны только по карте лояльности ("Цена по карте")
- [x] Динамическая подгрузка через AJAX при скролле

### Поведенческие паттерны

- **Максимум запросов в минуту**: ~10-15
- **Рекомендуемая задержка**: 2-4 секунды между страницами категорий
- **Время жизни сессии**: ~30 минут
- **Лимит товаров на странице**: Обычно 24-48 товаров

### Известные проблемы

1. **Проблема**: Блокировка при частых запросах (403)
   **Решение**: Использовать Playwright fallback, увеличить задержки, ротировать прокси

2. **Проблема**: Две цены (обычная и по карте)
   **Решение**: Парсить обе цены, приоритет отдавать цене по карте (нижняя)

3. **Проблема**: Не все товары видны без скролла
   **Решение**: Реализовать human_scroll стратегию для полной загрузки

---

## 🧪 Тестовые данные

### Пример URL товара

`https://5ka.ru/prod/12345678/ryba-losos-file-ohlazhdennoe-1kg`

### Ожидаемые данные парсинга

```json
{
  "name": "Лосось филе охлажденное, 1 кг",
  "price": 1299,
  "old_price": 1599,
  "weight": "1 кг",
  "brand": "Каждый День",
  "url": "https://5ka.ru/prod/12345678",
  "image_url": "https://5ka.ru/media/products/12345678.jpg"
}
```

---

## 📅 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2024-01-XX | Начальная версия на основе parsers/pyaterochka.py | AI Assistant |
| ... | ... | ... |

---

> **Примечание**: Этот файл должен обновляться при каждом изменении структуры сайта или обнаружении новых особенностей парсинга.
> 
> **Текущий статус**: ✅ Базовые селекторы извлечены из кода, требуется верификация актуальности
