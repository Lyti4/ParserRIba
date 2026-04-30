import logging
import sys
from datetime import datetime

def setup_logger(name: str, log_file: str = "parser.log", level=logging.INFO):
    """Настройка логгера для парсера"""
    
    # Форматирование сообщения
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Обработчик файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Обработчик консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
