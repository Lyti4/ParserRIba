# ParserRiba SKILL.md - Архитектурный план

## Цель
Трансформировать ParserRiba из текущей структуры в архитектуру по образцу browser-act/skills.

---

## 📋 Текущая структура ParserRiba

```
ParserRiba/
├── knowledge_base/       # ✅ Уже есть (Markdown конфиги)
│   ├── pyaterochka.md
│   ├── magnit.md
│   └── ...
├── strategies/           # ✅ Уже есть
│   ├── base_strategy.py
│   ├── scroll_strategy.py
│   └── ...
├── policies/             # ✅ Уже есть (engine.py)
│   └── engine.py
├── parsers/              # ✅ Уже есть
│   ├── base_parser.py
│   └── ...
├── models/               # ✅ Уже есть
└── utils/                # ✅ Уже есть
```

---

## 🎯 Целевая структура (как browser-act)

```
ParserRiba/
├── SKILL.md                          # ⭐ НОВЫЙ: Главный манифест
├── parser-skill/                     # ⭐ НОВАЯ папка для skill-файлов
│   ├── SKILL.md                      # Основной файл навыка
│   └── references/                   # ⭐ Переместить из knowledge_base
│       ├── commands.md               # ⭐ НОВЫЙ: Справка по командам CLI
│       ├── policies.md               # ⭐ НОВЫЙ: Политики в формате browser-act
│       ├── anti-bot.md               # ⭐ НОВЫЙ: Методы обхода защит
│       ├── proxy-config.md           # ⭐ НОВЫЙ: Конфигурация прокси
│       └── site-notes/               # ⭐ Переместить из knowledge_base
│           ├── pyaterochka.md
│           ├── magnit.md
│           └── ...
├── cli/                              # ⭐ НОВАЯ папка для CLI команд
│   ├── __init__.py
│   ├── main.py                       # Точка входа CLI
│   ├── commands/                     # ⭐ НОВЫЕ: Отдельные команды
│   │   ├── navigate.py
│   │   ├── extract.py
│   │   ├── state.py
│   │   └── ...
│   └── session_manager.py
├── core/                             # ⭐ Переименовать из parsers/
│   ├── engine.py
│   ├── extractor.py
│   └── browser_manager.py
├── strategies/                       # ✅ Оставить
├── policies/                         # ✅ Оставить (обновить формат)
├── models/                           # ✅ Оставить
└── utils/                            # ✅ Оставить
```

---

## 📝 Шаг 1: Создать SKILL.md (главный манифест)

**Расположение:** `/workspace/SKILL.md`

**Содержание по образцу browser-act:**

```markdown
---
name: parser-riba
description: "Professional fish products price parser for Russian retail chains. 
              MUST trigger when: (1) user needs to scrape prices from 
              Pyaterochka, Magnit, Lenta, Auchan, O'Key, Perekrestok, 
              (2) extract product data with anti-bot protection handling,
              (3) handle regional pricing, (4) export to JSON/CSV/Excel"
allowed-tools: Bash(parser-riba:*)
metadata:
  author: Lyti4
  version: "2.0.0"
  install: "pip install -r requirements.txt && playwright install chromium"
  homepage: "https://github.com/Lyti4/ParserRIba"
  requires:
    runtime: "Python 3.8+, Playwright"
    binaries: "Chromium (installed via Playwright)"
  permissions:
    - "Network access — required for scraping"
    - "Filesystem read/write — required for output files and logs"
  data-privacy:
    local-only: "All scraped data stored locally only"
---

# ParserRiba - Fish Products Price Parser

Professional parsing system for Russian retail chains with advanced anti-bot protection.

## Quick Start

```bash
# Extract prices from a category
python main.py --shop pyaterochka --category fish --limit 50

# With region support
python main.py --shop lenta --region msk --output json

# Docker run
docker-compose up --build
```

## Supported Stores

| Store | Tool | Region Header | CAPTCHA | Status |
|-------|------|---------------|---------|--------|
| Пятерочка | Playwright | X-Region-Id | Minimal | ✅ |
| Магнит | Playwright | X-City-Id | reCAPTCHA v2 | ✅ |
| Лента | Playwright | X-Region | Turnstile | ✅ |
| Ашан | Playwright | X-Region | Turnstile | ✅ |
| О'Кей | Playwright | X-Store-Id | Minimal | ✅ |
| Перекресток | Playwright only | X-Client-Id | Behavioral | ✅ |

## Core Workflow

1. **Load Knowledge Base**: `utils/kb_loader.py` loads store config from Markdown
2. **Create Session**: `utils/session_manager.py` sets up proxy/cookies/headers
3. **Apply Strategies**: Scroll, pagination, lazy-load, captcha handling
4. **Parse & Validate**: Extract data using selectors, validate with Pydantic
5. **Export**: JSON, CSV, Excel output

## Policies

Read `parser-skill/references/policies.md` at the start of every task.

**Default Policies:**
- HTTP 403 → Change proxy + UA + retry (max 5)
- HTTP 429 → Increase delay + retry (max 3)
- CAPTCHA → Solve/handle + retry (max 2)
- Timeout → Change proxy + retry (max 3)

## Human Assist

When stuck (captcha unsolvable, login required), request user help:

```bash
# Save current state and notify user
python main.py --assist "Need login credentials for Lenta"
```

## Site Notes

Operational experience stored per store in `parser-skill/references/site-notes/`.

Before parsing a store, read its note file for:
- Effective selectors
- Anti-scraping behavior
- Regional quirks
- Known pitfalls

## References

| Path | Description |
|------|-------------|
| `parser-skill/references/commands.md` | Full CLI reference |
| `parser-skill/references/policies.md` | Automation policies |
| `parser-skill/references/anti-bot.md` | Anti-bot strategies |
| `parser-skill/references/proxy-config.md` | Proxy setup |
| `parser-skill/references/site-notes/{store}.md` | Per-store notes |
```

---

## 📝 Шаг 2: Создать parser-skill/references/policies.md

**Формат как в browser-act** (trigger-action правила):

```markdown
---
description: Trigger-action rules for ParserRiba automation
---

## Policy Structure

| Field | Description |
|-------|-------------|
| `enabled` | `true` = active, `false` = skip |
| `trigger` | Condition to evaluate |
| `action` | What to do when triggered |
| `note` | Extra context |

## Available Actions

| Action | Behavior |
|--------|----------|
| `retry` | Retry the last operation |
| `change_proxy` | Switch to next proxy in pool |
| `change_user_agent` | Rotate User-Agent |
| `increase_delay` | Multiply delay by 1.5x |
| `switch_to_playwright` | Fallback from curl-cffi to Playwright |
| `skip_category` | Skip current category, continue with next |
| `abort_session` | Stop entire parsing session |
| `request_human_assist` | Pause and ask user for help |

---

## http-403-blocked

- enabled: true
- trigger: HTTP 403 response received
- action: change_proxy, change_user_agent, retry
- max_retries: 5
- note: Likely IP blocked or missing required headers

## http-429-rate-limited

- enabled: true
- trigger: HTTP 429 response received
- action: increase_delay, retry
- max_retries: 3
- note: Rate limiting detected, slow down

## captcha-detected

- enabled: true
- trigger: CAPTCHA challenge detected (Cloudflare, reCAPTCHA)
- action: switch_to_playwright, retry
- max_retries: 2
- note: If still fails after 2 attempts, request human assist

## timeout-exceeded

- enabled: true
- trigger: Request timeout (>30s)
- action: change_proxy, retry
- max_retries: 3
- note: Proxy may be slow or unresponsive

## selector-not-found

- enabled: true
- trigger: CSS/XPath selector returns empty results
- action: switch_to_playwright, retry
- max_retries: 2
- note: Site structure may have changed, check site-notes

## empty-response

- enabled: true
- trigger: Response body is empty or contains no products
- action: clear_cookies, change_proxy, retry
- max_retries: 3
- note: May indicate stale session or blocking

## login-required

- enabled: true
- trigger: Redirected to login page or auth wall detected
- action: request_human_assist
- note: Do NOT attempt to bypass - wait for user credentials

## payment-page-detected

- enabled: false  # Not applicable for price scraping
- trigger: Reached checkout/payment page
- action: request_human_assist
- note: Out of scope for price scraping
```

---

## 📝 Шаг 3: Создать parser-skill/references/commands.md

**Полная справка по CLI командам:**

```markdown
# ParserRiba Command Reference

## Basic Usage

```bash
# Parse a store category
python main.py --shop <store> --category <category> [options]

# Available stores: pyaterochka, magnit, lenta, auchan, okey, perekrestok
# Available categories: fish, meat, dairy, etc.
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--shop` | string | required | Store name |
| `--category` | string | fish | Category to parse |
| `--limit` | int | 0 (unlimited) | Max products to extract |
| `--region` | string | auto | Region code (for Lenta, Auchan) |
| `--output` | string | json | Output format: json, csv, excel |
| `--proxy` | string | none | Proxy URL (http://host:port) |
| `--headless` | bool | true | Run browser in headless mode |
| `--timeout` | int | 30 | Request timeout in seconds |
| `--retry` | int | 3 | Max retry attempts |
| `--assist` | string | none | Request human assist with message |

## Examples

```bash
# Basic extraction
python main.py --shop pyaterochka --category fish --limit 100

# With region and proxy
python main.py --shop lenta --region msk --proxy http://proxy:8080 --limit 50

# Export to Excel
python main.py --shop magnit --output excel

# Headful mode for debugging
python main.py --shop auchan --headless false

# With custom retry policy
python main.py --shop perekrestok --retry 5 --timeout 60
```

## Output Formats

### JSON (default)
```json
{
  "store": "pyaterochka",
  "category": "fish",
  "timestamp": "2024-01-15T10:30:00Z",
  "products": [
    {
      "name": "Лосось филе",
      "price": 899.99,
      "currency": "RUB",
      "unit": "кг",
      "url": "https://5post.ru/product/123"
    }
  ]
}
```

### CSV
Columns: name, price, currency, unit, url, timestamp

### Excel
Same as CSV with formatted columns and filters

## Session Management

```bash
# List active sessions
python main.py --session list

# Close specific session
python main.py --session close <session_id>

# Close all sessions
python main.py --session close --all
```

## Debugging

```bash
# Enable verbose logging
python main.py --shop pyaterochka --verbose

# Save screenshots on errors
python main.py --shop lenta --debug-screenshots

# Export browser console logs
python main.py --shop magnit --export-logs
```
```

---

## 📝 Шаг 4: Обновить policies/engine.py

**Добавить поддержку формата browser-act:**

```python
# Добавить новый класс для политик в формате browser-act

@dataclass
class BrowserActPolicy:
    """Policy in browser-act format."""
    name: str
    enabled: bool
    trigger: str  # Text description
    action: List[str]  # List of action names
    max_retries: int
    note: str
    
    @classmethod
    def from_markdown(cls, md_content: str) -> List['BrowserActPolicy']:
        """Parse policies from markdown file."""
        # Implementation to parse markdown format
        pass
    
    def to_markdown(self) -> str:
        """Export policy to markdown format."""
        return f"""
## {self.name}

- enabled: {'true' if self.enabled else 'false'}
- trigger: {self.trigger}
- action: {', '.join(self.action)}
- max_retries: {self.max_retries}
- note: {self.note}
"""
```

---

## 📝 Шаг 5: Переместить knowledge_base → parser-skill/references/site-notes

**Структура файлов останется той же**, но обновить формат:

```markdown
---
domain: pyaterochka.ru
updated: 2024-01-15
region_header: X-Region-Id
---

## Platform Characteristics

- Architecture: React SPA with server-side rendering
- Anti-scraping: Cloudflare Turnstile (lightweight)
- Login: Optional for browsing, required for cart
- Content loading: Lazy load on scroll

## Effective Patterns

- Base URL: https://5post.ru/catalog/ryba
- Pagination: Load more button (CSS: `.load-more-btn`)
- Product card: `.product-card`
- Price selector: `.price__current`

## Regional Headers

Required header: `X-Region-Id`
- Moscow: 77
- SPb: 78
- Default: 77

## Known Pitfalls

- Prices may vary by region - always set X-Region-Id
- Some products hidden behind "Show all" button
- Stock status updates every 5 minutes
```

---

## 📝 Шаг 6: Создать CLI интерфейс (опционально)

**Для полного соответствия browser-act** можно создать CLI:

```python
# cli/main.py
import click

@click.group()
def cli():
    """ParserRiba CLI"""
    pass

@cli.command()
@click.argument('shop')
@click.option('--category', default='fish')
@click.option('--limit', default=0)
def parse(shop, category, limit):
    """Parse a store category."""
    # Implementation

@cli.command()
def state():
    """Show current parsing state."""
    # Implementation

@cli.command()
@click.argument('url')
def extract(url):
    """Extract content from URL."""
    # Implementation

if __name__ == '__main__':
    cli()
```

Использование:
```bash
parser-riba parse pyaterochka --category fish --limit 50
parser-riba state
parser-riba extract https://5post.ru/catalog/ryba
```

---

## 🎯 Итоговый чеклист

- [ ] Создать `/workspace/SKILL.md` (главный манифест)
- [ ] Создать папку `/workspace/parser-skill/`
- [ ] Создать `/workspace/parser-skill/SKILL.md`
- [ ] Создать `/workspace/parser-skill/references/`
- [ ] Создать `/workspace/parser-skill/references/policies.md` (формат browser-act)
- [ ] Создать `/workspace/parser-skill/references/commands.md`
- [ ] Создать `/workspace/parser-skill/references/anti-bot.md`
- [ ] Создать `/workspace/parser-skill/references/proxy-config.md`
- [ ] Переместить `knowledge_base/*.md` → `parser-skill/references/site-notes/`
- [ ] Обновить `policies/engine.py` для поддержки нового формата
- [ ] (Опционально) Создать CLI интерфейс в `cli/`
- [ ] Обновить документацию в README.md

---

## 🔑 Ключевые отличия от текущей архитектуры

| Аспект | Текущий ParserRiba | Целевой (browser-act style) |
|--------|-------------------|----------------------------|
| Политики | Python код (engine.py) | Markdown файлы (trigger-action) |
| Знания о сайтах | `knowledge_base/` | `parser-skill/references/site-notes/` |
| Документация | Разрозненная | Единый SKILL.md + references |
| CLI | argparse в main.py | Отдельные команды (navigate, extract, state) |
| Human Assist | Не реализован | Явная команда `--assist` |
| Session mgmt | В коде парсера | Изолированные сессии с именами |

---

## 💡 Преимущества новой архитектуры

1. **Читаемость**: Политики в Markdown легче читать и править
2. **Расширяемость**: Новые сайты = новые site-notes без изменения кода
3. **AI-friendly**: Формат оптимизирован для AI агентов
4. **Policy Discovery**: Автоматическое сохранение новых паттернов
5. **Human-in-the-loop**: Явная поддержка ручной помощи
