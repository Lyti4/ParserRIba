# 📘 Knowledge Base: Лента (lenta.com)

## ℹ️ Общая информация

- **Название сети**: Лента
- **Базовый URL**: `https://lenta.com`
- **Тип защиты**: Умеренная/Высокая (требуется указание региона)
- **Требуется JS**: Да (каталог использует динамическую подгрузку)
- **Региональность**: Да, обязательно (Москва = 77)

---

## 🔗 URLs категорий

### Основные категории (рыба и морепродукты)

| Категория | URL | Примечание |
|-----------|-----|------------|
| Рыба и морепродукты | `https://lenta.com/catalog/ryba-moreprodukty` | Основная категория |
| Копченая и соленая рыба | `https://lenta.com/catalog/ryba-kopchenaya-solenaya` | Подкатегория |
| Икра и рыбные деликатесы | `https://lenta.com/catalog/ikra-rybnye-delikatesy` | Премиум сегмент |
| Рыбные консервы | `https://lenta.com/catalog/konservy-rybnye` | Консервированная продукция |
| Морепродукты | `https://lenta.com/catalog/moreprodukty` | Креветки, мидии и др. |

### Дополнительные URL

- **Карточка товара**: `https://lenta.com/product/{product_id}`
- **API эндпоинты** (потенциально):
  - `GET https://lenta.com/api/v1/products/` - список товаров
  - Параметры: `categoryId`, `page`, `pageSize`, `sort`

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
.product-tile
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

### Специфичные заголовки для Ленты

```python
{
    # Лента ТРЕБУЕТ указания региона
    'X-Region': '77',  # Москва (обязательно!)
    'X-Location': 'Moscow',
}
```

### Cookies для региона

```python
{
    # Регион доставки (обязательно)
    'region_id': '77',
    'city': 'Moscow',
    'location': 'moscow',
}
```

---

## 🛡 Анти-бот защита

### Признаки блокировки (Block Triggers)

- **HTTP статусы**: 403, 429, 401
- **Редиректы**: На страницу `/captcha` или `/check`
- **Слова в HTML**: 
  - "Проверка браузера"
  - "CAPTCHA"
  - "Access denied"
  - "Forbidden"
  - "Укажите регион"
- **Изменения в DOM**: Появление iframe с капчей, модальное окно выбора региона

### Стратегии обхода

1. **Impersonate профиль**: `chrome124` или `chrome120`
2. **Задержка перед запросом**: 3-5 секунд между страницами
3. **Ротация User-Agent**: Менять каждые 10-15 запросов
4. **Использование Playwright**: При обнаружении 403 или капчи
5. **Человеческое поведение**: 
   - Скроллинг страницы
   - Паузы между действиями
   - Установка региона при первом посещении

### CAPTCHA

- **Тип капчи**: Вероятно Cloudflare или собственная
- **Метод обхода**: 
  - Сохранение cookies сессии
  - Ручное решение при первом запуске
  - Playwright stealth режим
  - Предварительная установка региона
- **Сохранение сессии**: Обязательно (`lenta_session.json`)

---

## 📝 Особенности и заметки

### Технические нюансы

- [x] Требуется скроллинг для lazy loading товаров
- [ ] Пагинация через кнопку "Показать еще" или номер страниц
- [x] Цены зависят от региона (ОБЯЗАТЕЛЬНО указывать регион)
- [ ] Некоторые товары доступны только по карте лояльности
- [x] Динамическая подгрузка через AJAX
- [x] Модальное окно выбора региона при первом посещении

### Поведенческие паттерны

- **Максимум запросов в минуту**: ~10-12
- **Рекомендуемая задержка**: 3-5 секунд между страницами категорий
- **Время жизни сессии**: ~30 минут
- **Лимит товаров на странице**: Обычно 24-48 товаров

### Известные проблемы

1. **Проблема**: Блокировка без указанного региона (401/403)
   **Решение**: Обязательно передавать X-Region: 77 и cookies региона

2. **Проблема**: Блокировка при частых запросах (403)
   **Решение**: Использовать Playwright fallback, увеличить задержки

3. **Проблема**: Две цены (обычная и по карте лояльности)
   **Решение**: Парсить обе цены, приоритет отдавать цене по карте

4. **Проблема**: Не все товары видны без скролла
   **Решение**: Реализовать human_scroll стратегию для полной загрузки

---

## 🧪 Тестовые данные

### Пример URL товара

`https://lenta.com/product/12345678/ryba-losos-file-ohlazhdennoe-1kg`

### Ожидаемые данные парсинга

```json
{
  "name": "Лосось филе охлажденное, 1 кг",
  "price": 1299,
  "old_price": 1599,
  "weight": "1 кг",
  "brand": "Каждый День",
  "url": "https://lenta.com/product/12345678",
  "image_url": "https://lenta.com/media/products/12345678.jpg"
}
```

---

## 📅 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2024-01-XX | Начальная версия на основе parsers/lenta.py | AI Assistant |
| ... | ... | ... |

---

> **Примечание**: Этот файл должен обновляться при каждом изменении структуры сайта или обнаружении новых особенностей парсинга.
> 
> **Текущий статус**: ✅ Базовые селекторы извлечены из кода, требуется верификация актуальности
> 
> **Критично**: Обязательно указывать регион (X-Region: 77) для всех запросов!
