"""Pyaterochka parser powered by Camoufox and Knowledge Base selectors."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from camoufox.async_api import AsyncCamoufox
from loguru import logger

from models.schemas import CategoryInfo, ParseResult, Product, ProductPrice
from utils.antibot import collect_page_diagnostics, wait_for_pyaterochka_challenge
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.human_behavior import (
    HumanBehaviorProfile,
    browse_category_page,
    build_category_behavior_profile,
    hover_product_cards,
)
from utils.kb_loader import KBLoader, SelectorConfig
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url


class PyaterochkaParser:
    """Parse Pyaterochka catalog categories through Camoufox."""

    def __init__(self, store_name: str = "pyaterochka", region: str = "77", **kwargs: Any):
        self.shop_name = store_name
        self.region = region
        self.headless = kwargs.get("headless", True)
        self.kb = KBLoader("knowledge_base").load_shop(store_name)
        self.base_url = self.kb.base_url.rstrip("/")
        logger.info("PyaterochkaParser initialized for region {}", region)

    async def parse_category(self, category_url: str, category_name: str = "Unknown", **kwargs: Any) -> ParseResult:
        """Parse a single Pyaterochka category."""
        configure_windows_console()
        load_dotenv_file(".env")
        start_time = datetime.now()
        errors: list[str] = []
        warnings: list[str] = []
        products: list[Product] = []
        attempts = int(kwargs.get("attempts") or os.environ.get("PARSER_ATTEMPTS", "3"))
        proxy_urls = load_proxy_urls(
            primary=kwargs.get("proxy_url") or os.environ.get("PARSER_PROXY", ""),
            pool=os.environ.get("PARSER_PROXIES", ""),
        )

        for attempt in range(1, attempts + 1):
            proxy_url = choose_proxy_for_attempt(proxy_urls, attempt)
            if proxy_url:
                logger.info("Pyaterochka attempt {} uses proxy {}", attempt, mask_proxy_url(proxy_url))
            else:
                logger.info("Pyaterochka attempt {} runs without proxy", attempt)

            launch_options = build_camoufox_options(
                headless=kwargs.get("headless", self.headless),
                proxy_url=proxy_url,
                geoip=kwargs.get("geoip", False),
                block_images=kwargs.get("block_images", True),
                block_webgl=kwargs.get("block_webgl", False),
                humanize=kwargs.get("humanize", True),
                fingerprint_os=kwargs.get("fingerprint_os", "windows"),
            )

            try:
                products = await self._parse_category_once(
                    category_url=category_url,
                    category_name=category_name,
                    launch_options=launch_options,
                    warnings=warnings,
                )
                if products:
                    break
            except Exception as exc:
                logger.error("Pyaterochka attempt {} failed: {}", attempt, exc)
                errors.append(f"attempt {attempt}: {exc}")
                if attempt >= attempts:
                    break
                continue

        return self._build_result(category_url, category_name, products, start_time, errors, warnings)

    async def close_browser(self) -> None:
        """Compatibility hook: browser is scoped inside parse_category."""
        return None

    async def _parse_category_once(
        self,
        category_url: str,
        category_name: str,
        launch_options: dict[str, Any],
        warnings: list[str],
    ) -> list[Product]:
        """Parse one category with one browser/proxy session."""
        async with AsyncCamoufox(**launch_options) as browser:
            page = await browser.new_page()
            if self.kb.headers.custom:
                await page.set_extra_http_headers(self.kb.headers.custom)

            response = await page.goto(category_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(5_000)
            await wait_for_pyaterochka_challenge(page)
            behavior_profile = build_category_behavior_profile(category_name)
            await browse_category_page(page, behavior_profile)
            await wait_for_pyaterochka_challenge(page)

            diagnostics = await collect_page_diagnostics(page, response)
            if diagnostics.blocked or diagnostics.status == 403:
                message = f"Blocked by anti-bot: {diagnostics.reason}, status={diagnostics.status}"
                logger.warning(message)
                warnings.append(message)
                return []

            return await self._extract_products(page, category_name, behavior_profile)

    async def _extract_products(
        self,
        page: Any,
        category_name: str,
        behavior_profile: HumanBehaviorProfile | None = None,
    ) -> list[Product]:
        """Extract products from the rendered page using KB selectors."""
        card_selectors = self._split_selectors(self.kb.selectors.get("product_card"))
        name_selectors = self._split_selectors(self.kb.selectors.get("product_name"))
        price_selectors = self._split_selectors(self.kb.selectors.get("price_current"))
        link_selectors = self._split_selectors(self.kb.selectors.get("product_link"))

        cards = await self._find_cards(page, card_selectors)
        if behavior_profile:
            await hover_product_cards(page, cards, behavior_profile)
        products: list[Product] = []
        for index, card in enumerate(cards, start=1):
            try:
                name = await self._query_first_text(card, name_selectors)
                price_text = await self._query_first_text(card, price_selectors)
                link = await self._query_first_attribute(card, link_selectors, "href")
                product_link = self._absolute_url(link)
                if not name or not product_link:
                    continue

                products.append(
                    Product(
                        id=f"{self.shop_name}_{index}",
                        name=name,
                        price=ProductPrice(current=self._parse_price(price_text)),
                        product_link=product_link,
                        category=category_name,
                    )
                )
            except Exception as exc:
                logger.warning("Product card skipped: {}", exc)
                continue
        logger.info("Pyaterochka products extracted: {}", len(products))
        return products

    def _build_result(
        self,
        category_url: str,
        category_name: str,
        products: list[Product],
        start_time: datetime,
        errors: list[str],
        warnings: list[str],
    ) -> ParseResult:
        """Build a ParseResult for the category."""
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return ParseResult(
            shop=self.shop_name,
            category=CategoryInfo(name=category_name, url=category_url),
            products=products,
            total_products=len(products),
            errors=errors,
            warnings=warnings,
            parse_duration_ms=duration_ms,
        )

    def _absolute_url(self, link: str) -> str:
        """Normalize product link to an absolute URL."""
        if not link:
            return ""
        if link.startswith("http"):
            return link
        return f"{self.base_url}{link}"

    @staticmethod
    def _split_selectors(config: SelectorConfig | None) -> list[str]:
        """Return individual CSS selectors from KB selector config."""
        if not config or not config.css:
            return []
        return [item.strip() for item in config.css.split("|") if item.strip()]

    @staticmethod
    async def _query_first_text(root: Any, selectors: list[str]) -> str:
        """Return text from the first matching selector."""
        for selector in selectors:
            try:
                element = await root.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text.strip():
                        return text.strip()
            except Exception as exc:
                logger.debug("Selector failed: {} ({})", selector, exc)
        return ""

    @staticmethod
    async def _query_first_attribute(root: Any, selectors: list[str], attr: str) -> str:
        """Return attribute from the first matching selector."""
        for selector in selectors:
            try:
                element = await root.query_selector(selector)
                if element:
                    value = await element.get_attribute(attr)
                    if value:
                        return value
            except Exception as exc:
                logger.debug("Selector failed: {} ({})", selector, exc)
        return ""

    @staticmethod
    async def _find_cards(page: Any, selectors: list[str]) -> list[Any]:
        """Find product cards using KB selectors."""
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.info("Product cards found by selector '{}': {}", selector, len(cards))
                    return cards
            except Exception as exc:
                logger.debug("Card selector failed: {} ({})", selector, exc)
        return []

    @staticmethod
    def _parse_price(price_text: str) -> float:
        """Parse a price string into a float."""
        normalized = price_text.replace(",", ".")
        cleaned = "".join(char for char in normalized if char.isdigit() or char == ".")
        if not cleaned:
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
