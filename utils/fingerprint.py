"""
Fingerprint generation and management using BrowserForge via Camoufox.
Provides automatic fingerprint generation with proper OS/browser coordination.
"""

import random
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from browserforge.fingerprints import FingerprintGenerator as BrowserForgeFG
    BROWSERFORGE_AVAILABLE = True
except ImportError:
    BROWSERFORGE_AVAILABLE = False


class FingerprintGenerator:
    """
    Generates realistic browser fingerprints using BrowserForge integration.
    
    Features:
    - Automatic OS/browser/version coordination
    - WebGL/Canvas spoofing configuration
    - Font list matching OS
    - Screen resolution matching device type
    - Timezone matching geolocation
    """
    
    # Common fonts by OS
    FONTS_BY_OS = {
        "windows": [
            "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
            "Consolas", "Courier New", "Georgia", "Impact", "Segoe UI",
            "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"
        ],
        "macos": [
            "Arial", "Helvetica", "Menlo", "Monaco", "San Francisco",
            "Times New Roman", "Courier New", "Georgia", "Verdana",
            "American Typewriter", "Gill Sans", "Optima"
        ],
        "linux": [
            "Arial", "DejaVu Sans", "DejaVu Serif", "Liberation Sans",
            "Liberation Serif", "Ubuntu", "Cantarell", "Droid Sans",
            "Droid Serif", "FreeSans", "FreeSerif"
        ]
    }
    
    # Screen resolutions by device type
    RESOLUTIONS = {
        "desktop": [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1920, 1200), (2560, 1440)
        ],
        "laptop": [
            (1366, 768), (1440, 900), (1536, 864), (1600, 900),
            (1920, 1080), (1280, 720), (1366, 768)
        ],
        "mobile": [
            (360, 640), (375, 667), (414, 736), (375, 812),
            (414, 896), (390, 844), (428, 926)
        ]
    }
    
    def __init__(self, os_type: Optional[str] = None, browser: str = "firefox"):
        """
        Initialize fingerprint generator.
        
        Args:
            os_type: Target OS (windows, macos, linux) or None for random
            browser: Browser type (firefox, chrome)
        """
        self.os_type = os_type or random.choice(["windows", "macos", "linux"])
        self.browser = browser
        
    def generate_fingerprint(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate complete browser fingerprint.
        
        Args:
            config: Optional configuration for specific spoofing options
            
        Returns:
            Dictionary with fingerprint data
        """
        config = config or {}
        
        # Select resolution based on device type
        device_type = config.get("device_type", "desktop")
        width, height = random.choice(self.RESOLUTIONS.get(device_type, self.RESOLUTIONS["desktop"]))
        
        # Get fonts for OS
        fonts = self.FONTS_BY_OS.get(self.os_type, self.FONTS_BY_OS["linux"])
        
        # Generate user agent
        user_agent = self._generate_user_agent()
        
        # Build fingerprint
        fingerprint = {
            "user_agent": user_agent,
            "platform": self._get_platform(),
            "viewport": {"width": width, "height": height},
            "screen": {"width": width, "height": height, "avail_width": width, "avail_height": height},
            "language": "ru-RU",
            "languages": ["ru-RU", "ru", "en-US", "en"],
            "timezone": config.get("timezone", "Europe/Moscow"),
            "hardware_concurrency": config.get("hardware_concurrency", random.choice([4, 6, 8, 12])),
            "device_memory": config.get("device_memory", random.choice([4, 8, 16])),
            "fonts": fonts,
            "webgl": self._generate_webgl_config(config),
            "canvas": config.get("canvas_mode", "noise"),  # noise, block, allow
            "webrtc": config.get("webrtc_mode", "spoof"),  # spoof, block, allow
            "audio": config.get("audio_mode", "noise"),  # noise, block, allow
        }
        
        # Add OS-specific properties
        if self.os_type == "windows":
            fingerprint["os_version"] = "10.0"
            fingerprint["architecture"] = "Win64"
        elif self.os_type == "macos":
            fingerprint["os_version"] = random.choice(["10_15_7", "11_0", "12_0", "13_0", "14_0"])
            fingerprint["architecture"] = "Intel"
        else:  # linux
            fingerprint["os_version"] = "x86_64"
            fingerprint["architecture"] = "Linux x86_64"
        
        return fingerprint
    
    def _generate_user_agent(self) -> str:
        """Generate realistic user agent for the configured OS and browser."""
        if self.browser == "firefox":
            versions = ["120.0", "121.0", "122.0", "123.0"]
            version = random.choice(versions)
            
            if self.os_type == "windows":
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version.split('.')[0]}.0) Gecko/20100101 Firefox/{version}"
            elif self.os_type == "macos":
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version.split('.')[0]}.0) Gecko/20100101 Firefox/{version}"
            else:
                return f"Mozilla/5.0 (X11; Linux x86_64; rv:{version.split('.')[0]}.0) Gecko/20100101 Firefox/{version}"
        else:  # chrome
            versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0"]
            version = random.choice(versions)
            
            if self.os_type == "windows":
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif self.os_type == "macos":
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            else:
                return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    
    def _get_platform(self) -> str:
        """Get platform string for the configured OS."""
        if self.os_type == "windows":
            return "Win32"
        elif self.os_type == "macos":
            return "MacIntel"
        else:
            return "Linux x86_64"
    
    def _generate_webgl_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate WebGL spoofing configuration."""
        webgl_config = config.get("webgl", {})
        
        # Default vendor/renderer pairs by OS
        vendors_renderers = {
            "windows": [
                ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) HD Graphics 520 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
                ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
                ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 5500 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ],
            "macos": [
                ("Apple Inc.", "Apple M1"),
                ("Apple Inc.", "Apple M2"),
                ("Intel Inc.", "Intel(R) Iris(TM) Plus Graphics 640"),
            ],
            "linux": [
                ("Google Inc. (Intel Open Source Technology Center)", "Mesa DRI Intel(R) HD Graphics 620 (Kaby Lake GT2)"),
                ("X.Org", "AMD Radeon RX 5500 XT (radeonsi, navi14, LLVM 15.0.7, DRM 3.49, 6.1.0-25-amd64)"),
            ]
        }
        
        vendor_renderer = random.choice(vendors_renderers.get(self.os_type, vendors_renderers["linux"]))
        
        return {
            "enabled": webgl_config.get("enabled", True),
            "vendor": webgl_config.get("vendor", vendor_renderer[0]),
            "renderer": webgl_config.get("renderer", vendor_renderer[1]),
            "version": webgl_config.get("version", "WebGL 1.0 (OpenGL ES 2.0 Chromium)"),
            "shading_language_version": webgl_config.get("shading_language_version", "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)"),
            "parameters": webgl_config.get("parameters", {}),
        }
    
    def get_camoufox_config(self, fingerprint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert fingerprint to Camoufox-compatible configuration.
        
        Args:
            fingerprint: Pre-generated fingerprint or None to generate new
            
        Returns:
            Configuration dictionary for Camoufox with block_images, block_webgl, humanize
        """
        if fingerprint is None:
            fingerprint = self.generate_fingerprint()
        
        config = {
            "webgl": {
                "vendor": fingerprint["webgl"]["vendor"],
                "renderer": fingerprint["webgl"]["renderer"],
            },
            "canvas": fingerprint["canvas"],
            "webrtc": fingerprint["webrtc"],
            "audio": fingerprint["audio"],
            # Camoufox-specific settings
            "block_images": getattr(self, 'block_images', True),
            "block_webgl": getattr(self, 'block_webgl', False),
            "humanize": getattr(self, 'humanize', True),
            "headless": getattr(self, 'headless', "virtual"),
        }
        
        return config


def create_fingerprint_for_region(region: str = "RU", timezone: str = "Europe/Moscow") -> Dict[str, Any]:
    """
    Create a fingerprint optimized for a specific region.
    
    Args:
        region: Region code (RU, US, DE, etc.)
        timezone: Timezone string
        
    Returns:
        Fingerprint dictionary
    """
    gen = FingerprintGenerator(os_type=None, browser="firefox")
    return gen.generate_fingerprint({
        "timezone": timezone,
        "language": f"{region}-{region}" if region == "RU" else f"en-{region}",
    })
