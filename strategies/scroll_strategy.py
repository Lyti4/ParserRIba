"""
Scroll Strategy for handling infinite scroll and lazy-loaded content.
"""

import asyncio
import random
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
    
    Uses human-like scrolling patterns with random pauses and variable scroll speeds.
    Note: Camoufox's built-in humanize=True provides more reliable C++ implementation.
    """

    def __init__(self, page: Page, config: Optional[dict] = None):
        super().__init__(page, config)
        self.scroll_delay = self.config.get("scroll_delay", 1.0)
        self.max_scrolls = self.config.get("max_scrolls", 10)
        self.scroll_step = self.config.get("scroll_step", 500)
        self.human_like = self.config.get("human_like", True)  # Use human-like scrolling

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
                
            # Human-like scroll with random variation
            if self.human_like:
                # Random scroll amount with variation
                scroll_amount = self.scroll_step + random.randint(-100, 100)
                await self.page.mouse.wheel(0, scroll_amount)
                
                # Random pause between scrolls (human behavior)
                pause = random.uniform(0.3, 0.8)
                await asyncio.sleep(pause)
            else:
                # Standard scroll
                await self.page.mouse.wheel(0, self.scroll_step)
                await asyncio.sleep(self.scroll_delay)
            
            last_height = current_height
            scrolls_performed += 1
            
        # Scroll back to top smoothly
        if self.human_like:
            await self._smooth_scroll_to_top()
        else:
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
        
        return True
    
    async def _smooth_scroll_to_top(self):
        """Smooth scroll back to top like a human."""
        current_pos = await self.page.evaluate("window.scrollY")
        scroll_distance = 200
        
        while current_pos > 0:
            current_pos = max(0, current_pos - scroll_distance)
            await self.page.evaluate(f"window.scrollTo(0, {current_pos})")
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def can_apply(self) -> bool:
        """Check if page has scrollable content."""
        scroll_height = await self.page.evaluate("document.body.scrollHeight")
        client_height = await self.page.evaluate("document.documentElement.clientHeight")
        return scroll_height > client_height
