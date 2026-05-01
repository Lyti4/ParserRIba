"""
Pagination Strategy for handling multi-page catalogs.
"""

import asyncio
from typing import Optional, List
from playwright.async_api import Page

from .base_strategy import BaseStrategy


class PaginationStrategy(BaseStrategy):
    """
    Strategy for handling pagination in product catalogs.
    
    Supports:
    - Click-based pagination (Next button)
    - URL-based pagination (page=N)
    - Scroll-to-load pagination
    """

    def __init__(self, page: Page, config: Optional[dict] = None):
        super().__init__(page, config)
        self.next_selector = self.config.get("next_selector")
        self.active_selector = self.config.get("active_selector", ".active")
        self.disabled_selector = self.config.get("disabled_selector", ".disabled")
        self.timeout = self.config.get("timeout", 30000)

    async def execute(self, **kwargs) -> bool:
        """
        Navigate to the next page.
        
        Returns:
            bool: True if successfully navigated to next page.
        """
        if not self.next_selector:
            return False
            
        try:
            # Check if next button exists and is not disabled
            next_button = self.page.locator(self.next_selector)
            is_disabled = await next_button.evaluate(
                "el => el.classList.contains('disabled') or el.hasAttribute('disabled')"
            )
            
            if is_disabled:
                return False
                
            # Click next button
            await next_button.click(timeout=self.timeout)
            await self.page.wait_for_load_state("networkidle", timeout=self.timeout)
            await asyncio.sleep(1.0)  # Wait for content to render
            
            return True
        except Exception as e:
            print(f"Pagination error: {e}")
            return False

    async def can_apply(self) -> bool:
        """Check if pagination controls exist."""
        if not self.next_selector:
            return False
            
        try:
            next_button = self.page.locator(self.next_selector)
            return await next_button.count() > 0
        except Exception:
            return False

    async def get_current_page(self) -> int:
        """Get current page number."""
        try:
            active = self.page.locator(f"{self.next_selector}/../*{self.active_selector}")
            count = await active.count()
            if count > 0:
                text = await active.first.inner_text()
                return int(text)
        except Exception:
            pass
        return 1

    async def get_total_pages(self) -> int:
        """Get total number of pages."""
        # Implementation depends on site structure
        return 1

    async def has_next_page(self) -> bool:
        """Check if there is a next page."""
        return await self.can_apply() and not await self._is_last_page()

    async def _is_last_page(self) -> bool:
        """Check if current page is the last one."""
        try:
            next_button = self.page.locator(self.next_selector)
            return await next_button.evaluate(
                "el => el.classList.contains('disabled') or el.hasAttribute('disabled')"
            )
        except Exception:
            return True
