# Конфигурация приложения

# Пути к файлам
OUTPUT_FILE = "fish_prices.xlsx"
LOG_FILE = "parser.log"

# Список магазинов для парсинга
STORES = [
    "pyaterochka",
    "magnit",
    "perekrestok",
    "lenta",
    "auchan",
    "okey"
]

# Категории рыбных товаров
FISH_CATEGORIES = [
    "рыба свежая",
    "рыба замороженная",
    "рыба копченая",
    "рыба соленая",
    "морепродукты",
    "консервы рыбные",
    "икра"
]

# Настройки парсинга
REQUEST_TIMEOUT = 30  # таймаут запроса в секундах
RETRY_COUNT = 3  # количество повторных попыток
DELAY_BETWEEN_REQUESTS = 2  # задержка между запросами в секундах

# Настройки Selenium (если нужны)
HEADLESS_BROWSER = True
BROWSER_WAIT_TIME = 10
