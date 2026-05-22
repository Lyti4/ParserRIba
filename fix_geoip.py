#!/usr/bin/env python3
"""
Скрипт для исправления пути к GeoIP базе данных Camoufox на Windows.
Находит скачанный файл GeoLite2-City.mmdb во временной папке и копирует его
в директорию пакета camoufox.
"""
import os
import shutil
import sys
from pathlib import Path
from loguru import logger

def find_and_copy_geoip():
    # Путь к окружению проекта
    env_path = Path(__file__).parent / "env" / "Lib" / "site-packages" / "camoufox"
    dest_file = env_path / "GeoLite2-City.mmdb"
    
    # Если файл уже существует, выходим
    if dest_file.exists():
        logger.info("GeoLite2-City.mmdb already exists: {}", dest_file)
        return True
    
    # Временные директории для поиска
    temp_dirs = [
        Path(os.getenv("TEMP", r"C:\Windows\Temp")),
        Path(r"C:\Users\Дима\AppData\Local\Temp"),
        Path.home() / "AppData" / "Local" / "Temp",
    ]
    
    # Ищем файл
    mmdb_file = None
    logger.info("Searching for GeoLite2-City.mmdb...")
    
    for temp_dir in temp_dirs:
        if not temp_dir.exists():
            continue
            
        for root, dirs, files in os.walk(temp_dir):
            if "GeoLite2-City.mmdb" in files:
                mmdb_file = Path(root) / "GeoLite2-City.mmdb"
                logger.info("Found candidate: {}", mmdb_file)
                break
        if mmdb_file:
            break
    
    if not mmdb_file:
        logger.error("GeoLite2-City.mmdb was not found in temp directories.")
        logger.info("Run the parser once to trigger the download, interrupt it, then rerun this script.")
        return False
    
    # Создаём директорию назначения, если её нет
    env_path.mkdir(parents=True, exist_ok=True)
    
    # Копируем файл
    try:
        shutil.copy2(mmdb_file, dest_file)
        logger.info("Copied GeoLite2 database: {} -> {}", mmdb_file, dest_file)
        logger.info("You can now run: python main.py --store pyaterochka --no-headless --log-level INFO")
        return True
    except Exception as e:
        logger.error("Copy failed: {}", e)
        return False

if __name__ == "__main__":
    success = find_and_copy_geoip()
    sys.exit(0 if success else 1)
