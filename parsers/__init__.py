# Инициализация пакетов

from parsers.base_parser import BaseParser
from parsers.pyaterochka import PyaterochkaParser
from parsers.magnit import MagnitParser
from parsers.perekrestok import PerekrestokParser
from parsers.lenta import LentaParser
from parsers.auchan import AuchanParser
from parsers.okey import OkeyParser

__all__ = [
    'BaseParser',
    'PyaterochkaParser',
    'MagnitParser',
    'PerekrestokParser',
    'LentaParser',
    'AuchanParser',
    'OkeyParser',
]
