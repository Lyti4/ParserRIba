"""Browser runtime registry and backend adapters."""

from utils.browser_runtime.registry import (
    DEFAULT_BROWSER_RUNTIME,
    check_browser_runtime,
    get_browser_runtime,
    launch_research_browser,
)

__all__ = [
    "DEFAULT_BROWSER_RUNTIME",
    "check_browser_runtime",
    "get_browser_runtime",
    "launch_research_browser",
]
