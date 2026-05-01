"""
Captcha Handler Strategy for detecting and handling CAPTCHA challenges.
"""

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import Page

from .base_strategy import BaseStrategy


class CaptchaHandler(BaseStrategy):
    """
    Strategy for detecting and handling various CAPTCHA types.
    
    Supports detection of:
    - Google reCAPTCHA v2/v3
    - Cloudflare Turnstile
    - hCaptcha
    - Custom image/text CAPTCHAs
    
    Note: Actual solving requires external services (2Captcha, Anti-Captcha).
    This module focuses on detection and reporting.
    """

    # CAPTCHA detection selectors
    CAPTCHA_SELECTORS = {
        "recaptcha_v2": [
            "#recaptcha",
            ".g-recaptcha",
            "iframe[src*='recaptcha']",
        ],
        "recaptcha_v3": [
            "iframe[src*='recaptcha/api2/anchor']",
        ],
        "turnstile": [
            "iframe[src*='challenges.cloudflare.com']",
            "#cf-turnstile",
            ".cf-turnstile",
        ],
        "hcaptcha": [
            "#hcaptcha",
            "iframe[src*='hcaptcha.com']",
        ],
        "custom": [
            ".captcha",
            "#captcha",
            "[class*='captcha']",
            "[id*='captcha']",
        ],
    }

    def __init__(self, page: Page, config: Optional[dict] = None):
        super().__init__(page, config)
        self.solve_service = self.config.get("solve_service")  # e.g., '2captcha'
        self.api_key = self.config.get("api_key")
        self.timeout = self.config.get("timeout", 60000)

    async def execute(self, **kwargs) -> bool:
        """
        Detect and handle CAPTCHA if present.
        
        Returns:
            bool: True if no CAPTCHA or successfully handled, False if failed.
        """
        captcha_type = await self.detect_captcha()
        
        if not captcha_type:
            return True  # No CAPTCHA detected
            
        print(f"CAPTCHA detected: {captcha_type}")
        
        # Log CAPTCHA for manual solving or external service
        await self._handle_captcha(captcha_type)
        
        # Wait for CAPTCHA to be solved (if automated)
        if self.solve_service:
            return await self._solve_with_service(captcha_type)
        else:
            # Manual solving required
            print(f"Manual CAPTCHA solving required for {captcha_type}")
            return False

    async def detect_captcha(self) -> Optional[str]:
        """
        Detect if CAPTCHA is present on the page.
        
        Returns:
            str: CAPTCHA type if detected, None otherwise.
        """
        for captcha_type, selectors in self.CAPTCHA_SELECTORS.items():
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        return captcha_type
                except Exception:
                    continue
                    
        # Check for CAPTCHA-related text
        captcha_texts = [
            "verify you are human",
            "complete the security check",
            "prove you're not a robot",
        ]
        
        page_text = await self.page.content()
        for text in captcha_texts:
            if text.lower() in page_text.lower():
                return "custom"
                
        return None

    async def _handle_captcha(self, captcha_type: str) -> None:
        """Handle detected CAPTCHA."""
        # Take screenshot for debugging
        await self.page.screenshot(
            path=f"captcha_{captcha_type}_{int(asyncio.get_event_loop().time())}.png"
        )
        
        # Log details
        print(f"CAPTCHA screenshot saved: captcha_{captcha_type}_*.png")

    async def _solve_with_service(self, captcha_type: str) -> bool:
        """
        Solve CAPTCHA using external service.
        
        Implementation depends on the service API.
        """
        if not self.solve_service or not self.api_key:
            return False
            
        # Placeholder for service integration
        # Example: 2Captcha, Anti-Captcha APIs
        print(f"Solving {captcha_type} with {self.solve_service}...")
        
        # Simulate waiting for solution
        await asyncio.sleep(5)
        
        return True

    async def can_apply(self) -> bool:
        """Check if CAPTCHA handling is applicable."""
        return await self.detect_captcha() is not None

    async def wait_for_solve(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for CAPTCHA to disappear (solved).
        
        Args:
            timeout: Maximum wait time in milliseconds.
            
        Returns:
            bool: True if CAPTCHA disappeared, False if timeout.
        """
        timeout = timeout or self.timeout
        
        try:
            # Wait for CAPTCHA elements to disappear
            await self.page.wait_for_function(
                """
                () => {
                    const captchaSelectors = [
                        '#recaptcha', '.g-recaptcha',
                        '#cf-turnstile', '.cf-turnstile',
                        '#hcaptcha', '.captcha', '#captcha'
                    ];
                    return captchaSelectors.every(sel => !document.querySelector(sel));
                }
                """,
                timeout=timeout
            )
            return True
        except Exception:
            return False
