"""
Модуль логирования для ParserRiba.
Настройка цветного консольного вывода и записи в файл.
Поддержка JSON-логов для LogStreamer в лаунчере.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Цвета для консоли
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для разных уровней логирования."""

    COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA + Colors.BOLD,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON форматтер для структурированных логов (LogStreamer)."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Добавляем extra поля если есть
        if hasattr(record, 'extra'):
            log_data["extra"] = record.extra
        
        # Добавляем exception если есть
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logger(
    name: str = "parser_riba",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
    colors: bool = True,
    json_logs: bool = False,
    json_log_file: Optional[str] = None
) -> logging.Logger:
    """
    Настройка логгера с выводом в консоль и файл.

    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу лога (если None, файл не создается)
        console_output: Выводить ли в консоль
        colors: Использовать ли цвета в консоли
        json_logs: Включить JSON-логи для LogStreamer
        json_log_file: Путь к JSON лог файлу

    Returns:
        Настроенный logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Очистка существующих хендлеров
    logger.handlers.clear()

    # Форматы
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_format_str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    if colors:
        console_format = ColoredFormatter(console_format_str, datefmt="%H:%M:%S")
    else:
        console_format = logging.Formatter(console_format_str, datefmt="%H:%M:%S")

    # Файловый хендлер
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # В файл пишем всё
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    # JSON хендлер для LogStreamer
    if json_logs:
        json_file = json_log_file or (log_file.replace('.log', '.json') if log_file else 'logs/parser_riba.json')
        json_path = Path(json_file)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_handler = logging.FileHandler(json_file, encoding="utf-8")
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
        logger.info(f"JSON логи включены: {json_file}")

    # Консольный хендлер
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    return logger


# Глобальный логгер по умолчанию
default_logger = setup_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Получить логгер по имени или дефолтный."""
    if name:
        return setup_logger(name)
    return default_logger


if __name__ == "__main__":
    # Тест логгера
    logger = get_logger("test")
    logger.debug("Это отладочное сообщение")
    logger.info("Информационное сообщение")
    logger.warning("Предупреждение")
    logger.error("Ошибка")
    logger.critical("Критическая ошибка")
