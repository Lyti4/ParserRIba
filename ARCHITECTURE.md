# ParserRiba Architecture

Modern fish products price parser for Russian retail chains with advanced anti-bot protection handling.

## 🏗 Architecture Overview

```
ParserRiba/
├── knowledge_base/          # Markdown configs for each store
│   ├── template.md
│   ├── pyaterochka.md
│   ├── magnit.md
│   ├── lenta.md
│   ├── auchan.md
│   ├── okey.md
│   └── perekrestok.md
├── strategies/              # Browser automation strategies
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── scroll_strategy.py
│   ├── pagination_strategy.py
│   ├── lazy_load_strategy.py
│   └── captcha_handler.py
├── policies/                # Error handling policies
│   ├── __init__.py
│   └── engine.py
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── kb_loader.py        # Knowledge Base loader
│   └── session_manager.py  # Session/proxy management
├── parsers/                 # Store-specific parsers
│   ├── __init__.py
│   └── base_parser.py      # Base parser class
├── models/                  # Pydantic data models
│   ├── __init__.py
│   └── product.py          # Product schema
└── config/                  # Configuration files
    └── settings.py
```

## 📦 Core Modules

### 1. Knowledge Base (`knowledge_base/`)
Structured Markdown files containing:
- CSS/XPath selectors for each store
- Custom headers (X-Region, X-Store, etc.)
- Anti-bot protection details
- API endpoints and URL patterns
- Store-specific quirks and workarounds

**Usage:**
```python
from utils.kb_loader import KBLoader

loader = KBLoader()
kb = loader.load_shop("lenta")
print(kb.selectors.product_card)  # e.g., ".product-card"
print(kb.headers.custom)  # e.g., {"X-Region": "required"}
```

### 2. Strategies (`strategies/`)
Reusable browser automation patterns:

| Strategy | Purpose |
|----------|---------|
| `ScrollStrategy` | Handle infinite scroll, lazy loading |
| `PaginationStrategy` | Navigate multi-page catalogs |
| `LazyLoadStrategy` | Ensure all images/content loaded |
| `CaptchaHandler` | Detect and handle CAPTCHAs |

**Usage:**
```python
from strategies import ScrollStrategy, CaptchaHandler

scroll = ScrollStrategy(page, config={"max_scrolls": 10})
await scroll.execute_with_hooks()

captcha = CaptchaHandler(page)
if await captcha.can_apply():
    await captcha.execute()
```

### 3. Policies Engine (`policies/`)
Automatic error handling with configurable rules:

**Default Policies:**
- **HTTP 403**: Change proxy + UA + retry (max 5)
- **HTTP 429**: Increase delay + retry (max 3)
- **CAPTCHA**: Solve/handle + retry (max 2)
- **Timeout**: Change proxy + retry (max 3)
- **Selector not found**: Switch to Playwright + retry
- **Empty response**: Clear cookies + change proxy + retry
- **Network error**: Change proxy + retry (max 5)
- **HTTP 500**: Wait + retry (max 3)
- **HTTP 404**: Skip category

**Usage:**
```python
from policies import PoliciesEngine, ErrorType, classify_error

engine = PoliciesEngine()

try:
    # ... parsing code ...
except Exception as e:
    error_type = classify_error(e, status_code=403)
    result = await engine.evaluate(error_type, request_id="req_123")
    
    if result.should_retry:
        if result.new_proxy:
            proxy = await session_manager.get_next_proxy()
        await asyncio.sleep(result.delay)
        # Retry...
    elif result.abort:
        raise Exception(result.message)
```

### 4. Session Manager (`utils/session_manager.py`)
Manages proxies, cookies, and header rotation:

**Features:**
- Round-robin and random proxy selection
- Session persistence with age/request limits
- Automatic header randomization (UA, Accept-Language)
- Cookie merging and validation

**Usage:**
```python
from utils.session_manager import SessionManager, ProxyConfig

proxies = [
    ProxyConfig(host="proxy1.com", port=8080, username="user", password="pass"),
    ProxyConfig(host="proxy2.com", port=8080),
]

manager = SessionManager(
    proxies=proxies,
    max_session_age=timedelta(minutes=30),
    max_requests_per_session=100,
)

proxy = await manager.get_next_proxy()
session = await manager.create_session("session_1")
```

### 5. KB Loader (`utils/kb_loader.py`)
Parses Markdown knowledge base files into validated Pydantic models:

**Extracted Data:**
- Category URLs (6-8 per store)
- 9 selector types (CSS, XPath, regex, fallbacks)
- Custom headers (X-Region, X-Store, X-Client-Id)
- Anti-bot triggers and strategies
- Technical notes and constraints

## 🔄 Data Flow

```
1. Load KB Config → 2. Create Session → 3. Apply Strategies → 4. Parse Data
       ↓                    ↓                  ↓                   ↓
   selectors           proxy/cookies      scroll/pagination    extract
   headers             random UA          captcha check        validate
   anti-bot info       session mgmt       lazy load            Pydantic
```

## 🛡 Anti-Bot Protection

### Multi-Layer Approach:
1. **Knowledge Base**: Store-specific headers and selectors
2. **Session Manager**: Rotating proxies, randomized headers
3. **Strategies**: Human-like behavior (scrolling, delays)
4. **Policies**: Automatic recovery from blocks/CAPTCHAs

### Supported Protections:
- Cloudflare Turnstile (Lenta, Auchan)
- reCAPTCHA v2/v3 (Magnit)
- Custom challenges (Perekrestok)
- Rate limiting (all stores)
- IP blocking (all stores)

## 📊 Supported Stores

| Store | Tool | Region Header | CAPTCHA | Status |
|-------|------|---------------|---------|--------|
| Пятерочка | Playwright | X-Region-Id | Minimal | ✅ |
| Магнит | Playwright | X-City-Id | reCAPTCHA v2 | ✅ |
| Лента | Playwright | X-Region (critical) | Turnstile | ✅ |
| Ашан | Playwright | X-Region (critical) | Turnstile | ✅ |
| О'Кей | Playwright | X-Store-Id | Minimal | ✅ |
| Перекресток | Playwright only | X-Client-Id | Behavioral | ✅ |

## 🚀 Quick Start

```python
import asyncio
from utils.kb_loader import KBLoader
from utils.session_manager import SessionManager
from policies import PoliciesEngine
from strategies import ScrollStrategy

async def parse_store(store_name: str, category_url: str):
    # Load knowledge base
    loader = KBLoader()
    kb = loader.load_shop(store_name)
    
    # Initialize components
    session_mgr = SessionManager(proxies=[])  # Add your proxies
    policies = PoliciesEngine()
    
    # Create session
    session = await session_mgr.create_session(
        f"{store_name}_session",
        headers=kb.headers.to_dict()
    )
    
    # Launch browser (Playwright)
    async with playwright.async_api.chromium.launch() as browser:
        page = await browser.new_page()
        
        # Apply strategies
        scroll = ScrollStrategy(page)
        if await scroll.can_apply():
            await scroll.execute()
        
        # Extract data using KB selectors
        products = []
        for card in await page.query_selector_all(kb.selectors.product_card):
            # ... extraction logic ...
            pass
    
    return products
```

## 📝 Roadmap

- [x] Knowledge Base structure
- [x] KB Loader with Pydantic validation
- [x] Strategies module (scroll, pagination, lazy-load, captcha)
- [x] Session Manager (proxy, cookies, headers)
- [x] Policies Engine (error handling)
- [ ] Base Parser integration
- [ ] Pydantic Product models
- [ ] Full store parser implementation
- [ ] Testing suite
- [ ] Documentation

## 🎯 Inspired By

This architecture takes best practices from:
- **browser-act**: SKILL.md format, strategy patterns, policy-driven automation
- **Scrapy**: Middleware architecture, item pipelines
- **Playwright**: Modern browser automation
- **curl-cffi**: TLS fingerprint spoofing

---

**Status**: Active Development  
**Last Updated**: 2024
