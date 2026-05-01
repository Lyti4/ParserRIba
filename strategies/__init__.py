"""
Strategies module for ParserRiba.
Contains reusable browser automation strategies inspired by browser-act best practices.
"""

from .base_strategy import BaseStrategy
from .scroll_strategy import ScrollStrategy
from .pagination_strategy import PaginationStrategy
from .captcha_handler import CaptchaHandler
from .lazy_load_strategy import LazyLoadStrategy

__all__ = [
    "BaseStrategy",
    "ScrollStrategy",
    "PaginationStrategy",
    "CaptchaHandler",
    "LazyLoadStrategy",
]
