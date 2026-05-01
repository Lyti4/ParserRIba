"""
Lazy Load Strategy for handling images and content loaded on visibility.
"""

import asyncio
from typing import Optional
from playwright.async_api import Page

from .base_strategy import BaseStrategy


class LazyLoadStrategy(BaseStrategy):
    """
    Strategy for handling lazy-loaded images and content.
    
    Ensures all images and dynamic content are fully loaded
    before extraction by scrolling through the page.
    """

    def __init__(self, page: Page, config: Optional[dict] = None):
        super().__init__(page, config)
        self.image_selector = self.config.get("image_selector", "img")
        self.lazy_attribute = self.config.get("lazy_attribute", "loading='lazy'")
        self.scroll_delay = self.config.get("scroll_delay", 0.5)
        self.check_interval = self.config.get("check_interval", 1.0)

    async def execute(self, **kwargs) -> bool:
        """
        Ensure all lazy-loaded content is visible and loaded.
        
        Returns:
            bool: True if all content loaded successfully.
        """
        # Scroll to bottom to trigger lazy loading
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(self.scroll_delay)
        
        # Scroll back to top in steps
        scroll_height = await self.page.evaluate("document.body.scrollHeight")
        viewport_height = await self.page.evaluate("window.innerHeight")
        
        current_position = scroll_height
        while current_position > 0:
            current_position -= viewport_height
            if current_position < 0:
                current_position = 0
                
            await self.page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(self.scroll_delay)
            
            # Wait for images to load
            await self._wait_for_images()
        
        # Final scroll to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        
        return True

    async def _wait_for_images(self, timeout: int = 5000) -> None:
        """Wait for all images to be fully loaded."""
        try:
            await self.page.wait_for_function(
                """
                () => {
                    const images = document.querySelectorAll('img');
                    return Array.from(images).every(img => img.complete && img.naturalHeight !== 0);
                }
                """,
                timeout=timeout
            )
        except Exception:
            # Timeout is acceptable, some images may fail to load
            pass

    async def can_apply(self) -> bool:
        """Check if page has lazy-loaded images."""
        try:
            lazy_images = await self.page.query_selector_all(f"img[{self.lazy_attribute}]")
            return len(lazy_images) > 0
        except Exception:
            return False

    async def get_unloaded_images_count(self) -> int:
        """Get count of images that haven't loaded yet."""
        try:
            unloaded = await self.page.evaluate(
                """
                () => {
                    const images = document.querySelectorAll('img');
                    return Array.from(images).filter(
                        img => !img.complete || img.naturalHeight === 0
                    ).length;
                }
                """
            )
            return unloaded
        except Exception:
            return 0
