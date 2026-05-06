import asyncio
import logging
from typing import List, Dict, Any
from parsers.camoufox_parser import CamoufoxParser

logger = logging.getLogger(__name__)

class PyaterochkaParser(CamoufoxParser):
    def __init__(self, region: str = "default", **kwargs):
        super().__init__(store_name="pyaterochka", **kwargs)
        self.region = region
        self.base_url = "https://5ka.ru"
        logger.info(f"PyaterochkaParser initialized for region {region}")

    async def parse_category(self, category_url: str, category_name: str, **kwargs) -> List[Dict]:
        logger.info(f"Parsing category: {category_url}")
        try:
            page = await self.start_browser(headless=kwargs.get("headless", True), geoip=True)
            await page.goto(category_url, wait_until="domcontentloaded", timeout=30000)
            products = []
            logger.info(f"Category {category_name} done")
            return products
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
        finally:
            await self.close_browser()
