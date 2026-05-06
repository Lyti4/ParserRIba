"""
Base Strategy class for all automation strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar

# Используем TypeVar вместо прямого импорта Page для избежания зависимости от playwright
Page = TypeVar('Page')


class BaseStrategy(ABC):
    """Abstract base class for browser automation strategies."""

    def __init__(self, page: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        self.page = page
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(self, **kwargs) -> bool:
        """
        Execute the strategy.
        
        Returns:
            bool: True if strategy executed successfully, False otherwise.
        """
        pass

    async def can_apply(self) -> bool:
        """
        Check if this strategy can be applied to the current page state.
        
        Returns:
            bool: True if strategy is applicable, False otherwise.
        """
        return True

    async def before_execute(self) -> None:
        """Hook called before strategy execution."""
        pass

    async def after_execute(self, success: bool) -> None:
        """
        Hook called after strategy execution.
        
        Args:
            success: Whether the strategy executed successfully.
        """
        pass

    async def execute_with_hooks(self, **kwargs) -> bool:
        """
        Execute strategy with before/after hooks.
        
        Returns:
            bool: Execution result.
        """
        await self.before_execute()
        try:
            result = await self.execute(**kwargs)
            await self.after_execute(True)
            return result
        except Exception as e:
            await self.after_execute(False)
            raise e
