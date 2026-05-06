"""
Конфигурация парсера
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Магазины для парсинга
STORES = [
    "pyaterochka",
    "magnit",
    "perekrestok",
    "lenta",
    "auchan",
    "okey"
]

# Файл для экспорта
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "fish_products.xlsx")

# Задержки между запросами (секунды)
REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", "3"))

# Таймаут запроса (секунды)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Категории рыбных товаров по магазинам
CATEGORIES = {
    "pyaterochka": [
        "https://5ka.ru/cat/ryba_i_moreprodukty",
        "https://5ka.ru/cat/ryba_kopchenaya_i_solenaya",
        "https://5ka.ru/cat/ikra_i_rybnye_delikatesy",
        "https://5ka.ru/cat/konservy_rybnye",
    ],
    "magnit": [
        "https://magnit.ru/catalog/ryba-moreprodukty/",
        "https://magnit.ru/catalog/ryba-kopchenaya-solenaya/",
        "https://magnit.ru/catalog/konservy-rybnye/",
    ],
    "perekrestok": [
        "https://perekrestok.ru/catalog/ryba-moreprodukty",
        "https://perekrestok.ru/catalog/ryba-kopchenaya-solenaya",
        "https://perekrestok.ru/catalog/ikra-delikatesy",
        "https://perekrestok.ru/catalog/konservy-rybnye",
        "https://perekrestok.ru/catalog/moreprodukty",
    ],
    "lenta": [
        "https://lenta.com/catalog/ryba-moreprodukty",
        "https://lenta.com/catalog/ryba-kopchenaya-solenaya",
        "https://lenta.com/catalog/ikra-rybnye-delikatesy",
        "https://lenta.com/catalog/konservy-rybnye",
        "https://lenta.com/catalog/moreprodukty",
    ],
    "auchan": [
        "https://auchan.ru/catalog/ryba-moreprodukty",
        "https://auchan.ru/catalog/ryba-kopchenaya-solenaya",
        "https://auchan.ru/catalog/ikra-rybnye-delikatesy",
        "https://auchan.ru/catalog/konservy-rybnye",
        "https://auchan.ru/catalog/moreprodukty",
    ],
    "okey": [
        "https://www.okey.ru/catalog/ryba-moreprodukty",
        "https://www.okey.ru/catalog/ryba-kopchenaya-solenaya",
        "https://www.okey.ru/catalog/ikra-rybnye-delikatesy",
        "https://www.okey.ru/catalog/konservy-rybnye",
        "https://www.okey.ru/catalog/moreprodukty",
    ]
}
