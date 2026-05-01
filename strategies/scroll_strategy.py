"""
Scroll Strategy for handling infinite scroll and lazy-loaded content.
"""

import asyncio
from typing import Optional
from playwright.async_api import Page

from .base_strategy import BaseStrategy


class ScrollStrategy(BaseStrategy):
    """
    Strategy for scrolling pages to load dynamic content.
    
    Handles:
    - Infinite scroll catalogs
    - Lazy-loaded images
    - Progressive content loading
    """

    def __init__(self, page: Page, config: Optional[dict] = None):
        super().__init__(page, config)
        self.scroll_delay = self.config.get("scroll_delay", 1.0)
        self.max_scrolls = self.config.get("max_scrolls", 10)
        self.scroll_step = self.config.get("scroll_step", 500)

    async def execute(self, **kwargs) -> bool:
        """
        Execute scroll strategy to load all content.
        
        Args:
            **kwargs: Additional parameters (e.g., target_height)
            
        Returns:
            bool: True if scroll completed successfully.
        """
        target_height = kwargs.get("target_height")
        scrolls_performed = 0
        last_height = 0
        
        while scrolls_performed < self.max_scrolls:
            # Get current scroll height
            current_height = await self.page.evaluate("document.body.scrollHeight")
            
            # Check if we reached the target or bottom
            if target_height and current_height >= target_height:
                break
            if current_height == last_height:
                # No more content to load
                break
                
            # Scroll down
            await self.page.mouse.wheel(0, self.scroll_step)
            await asyncio.sleep(self.scroll_delay)
            
            last_height = current_height
            scrolls_performed += 1
            
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        
        return True

    async def can_apply(self) -> bool:
        """Check if page has scrollable content."""
        scroll_height = await self.page.evaluate("document.body.scrollHeight")
        client_height = await self.page.evaluate("document.documentElement.clientHeight")
        return scroll_height > client_height
