"""
Скрипт для скачивания GeoIP базы данных GeoLite2-City.mmdb
в локальную папку проекта, чтобы избежать проблем с путями.
"""
import os
import sys
import requests
from pathlib import Path

def download_geoip():
    # Путь для сохранения в корне проекта (без кириллицы)
    base_dir = Path(__file__).parent
    geoip_path = base_dir / "GeoLite2-City.mmdb"
    
    # Ссылка на актуальную базу (MaxMind через прокси или прямой репозиторий)
    # Используем надежный источник
    url = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"
    
    if geoip_path.exists():
        print(f"✅ Файл уже существует: {geoip_path}")
        print(f"   Размер: {geoip_path.stat().st_size / 1024 / 1024:.2f} MB")
        return str(geoip_path)

    print(f"🌍 Скачивание GeoIP базы данных...")
    print(f"   Источник: {url}")
    print(f"   Куда: {geoip_path}")
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(geoip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Прогресс бар
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        bar_len = 40
                        filled = int(bar_len * downloaded // total_size)
                        bar = '█' * filled + '░' * (bar_len - filled)
                        sys.stdout.write(f'\r   [{bar}] {percent:.1f}%')
                        sys.stdout.flush()
        
        print()  # Новая строка после прогресс бара
        print(f"✅ Успешно скачано: {geoip_path}")
        print(f"   Размер: {geoip_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        return str(geoip_path)
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        if geoip_path.exists():
            geoip_path.unlink()  # Удаляем битый файл
        return None

if __name__ == "__main__":
    path = download_geoip()
    if path:
        print("\n🎉 Готово! Теперь запустите парсер:")
        print("   python main.py --store pyaterochka --no-headless --log-level INFO")
    else:
        print("\n⚠️ Не удалось скачать базу. Проверьте интернет-соединение.")
        sys.exit(1)
