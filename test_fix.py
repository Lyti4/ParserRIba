"""
Тестовый скрипт для проверки работы парсера с улучшенной маскировкой
Запустите: python test_fix.py
"""
import asyncio
from curl_cffi import requests

def test_curl_request():
    """Тест запроса к 5ka.ru с impersonate"""
    url = "https://5ka.ru/cat/ryba_i_moreprodukty"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Platform': '"Windows"',
    }
    
    print(f"🧪 Тестируем запрос к {url}...")
    try:
        resp = requests.get(
            url, 
            headers=headers, 
            impersonate='chrome124', 
            timeout=30, 
            verify=False
        )
        print(f"✅ Статус: {resp.status_code}")
        print(f"📏 Длина ответа: {len(resp.text)} байт")
        
        if resp.status_code == 200:
            # Проверяем наличие ключевых слов
            text_sample = resp.text[:2000].lower()
            if 'товар' in text_sample or 'продукт' in text_sample or 'цена' in text_sample:
                print("✅ Успех! Страница загружена корректно.")
                return True
            else:
                print("⚠️ Страница загружена, но контент может быть некорректным.")
                return False
        else:
            print(f"❌ Ошибка: статус {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False


async def test_parser():
    """Тест парсера Пятёрочки"""
    from parsers.pyaterochka import PyaterochkaParser
    
    print("\n🧪 Тестируем парсер Пятёрочки...")
    parser = PyaterochkaParser(headless=True)
    
    try:
        products = await parser.parse_fish_products()
        print(f"✅ Найдено товаров: {len(products)}")
        
        if products:
            print("\n📦 Первые 3 товара:")
            for i, p in enumerate(products[:3], 1):
                print(f"  {i}. {p.name} - {p.price} ₽")
        
        return len(products) > 0
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return False
    finally:
        await parser.close()


if __name__ == "__main__":
    print("=" * 50)
    print("ТЕСТ УЛУЧШЕННОГО ПАРСЕРА PARSER RIBA")
    print("=" * 50)
    
    # Тест 1: Прямой запрос
    print("\n📋 ТЕСТ 1: Прямой HTTP запрос")
    test1_result = test_curl_request()
    
    # Тест 2: Парсер
    print("\n📋 ТЕСТ 2: Полный парсинг")
    test2_result = asyncio.run(test_parser())
    
    # Итоги
    print("\n" + "=" * 50)
    print("ИТОГИ ТЕСТОВ:")
    print(f"  Тест 1 (HTTP запрос): {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"  Тест 2 (Парсинг): {'✅ PASS' if test2_result else '❌ FAIL'}")
    print("=" * 50)
    
    if test1_result and test2_result:
        print("\n🎉 Все тесты пройдены! Можно запускать main.py")
    else:
        print("\n⚠️ Некоторые тесты не пройдены. Проверьте логи выше.")
