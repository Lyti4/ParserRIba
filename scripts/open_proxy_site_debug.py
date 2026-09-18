"""Open a site in visible Camoufox through ParserRIba proxy settings."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from camoufox.async_api import AsyncCamoufox
from loguru import logger

from utils.camoufox_launcher import build_research_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.proxy import choose_proxy_for_attempt, load_proxy_config_from_env, mask_proxy_url


DEFAULT_URL = "https://5ka.ru/catalog/"
DEFAULT_PROFILE_DIR = Path("profiles") / "pyaterochka_manual_debug"
DEFAULT_LOG_PATH = Path("logs") / "manual_proxy_debug" / "latest.log"


def main() -> None:
    configure_windows_console()
    parser = argparse.ArgumentParser(description="Open a visible browser through configured proxy.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR))
    parser.add_argument("--hold-seconds", type=int, default=1800)
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    args = parser.parse_args()
    asyncio.run(_open_site(args))


async def _open_site(args: argparse.Namespace) -> None:
    load_dotenv_file(".env")
    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(log_path, encoding="utf-8", level="DEBUG")
    proxy_config = load_proxy_config_from_env(os.environ)
    proxy_url = choose_proxy_for_attempt(proxy_config.urls, 1)
    logger.info("started_at={}", datetime.now(timezone.utc).isoformat())
    logger.info("url={}", args.url)
    logger.info("proxy_enabled={}", bool(proxy_url))
    logger.info("proxy={}", mask_proxy_url(proxy_url) if proxy_url else "")
    logger.info("profile_dir={}", args.profile_dir)

    options = build_research_camoufox_options(
        headless=False,
        proxy_url=proxy_url,
        geoip=os.environ.get("PARSER_GEOIP", "").strip().lower() in {"1", "true", "yes"},
        user_data_dir=Path(args.profile_dir),
    )
    async with AsyncCamoufox(**options) as browser:
        page = await browser.new_page()
        _attach_page_logging(page)
        try:
            response = await page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
            logger.info("goto_status={}", _response_status(response))
        except Exception as exc:
            logger.warning("goto_error={}", exc)
        await _hold_for_inspection(page, max(1, int(args.hold_seconds)))


def _attach_page_logging(page: Any) -> None:
    page.on("console", lambda msg: logger.debug("console:{}:{}", msg.type, msg.text))
    page.on("pageerror", lambda exc: logger.warning("pageerror={}", exc))
    page.on("requestfailed", lambda request: logger.warning("requestfailed:{}:{}", request.url, request.failure))
    page.on("response", lambda response: _log_response(response))


def _log_response(response: Any) -> None:
    status = int(getattr(response, "status", 0) or 0)
    if status >= 400:
        logger.warning("response_status:{}:{}", status, getattr(response, "url", ""))


def _response_status(response: Any) -> int:
    return int(getattr(response, "status", 0) or 0) if response is not None else 0


async def _hold_for_inspection(page: Any, hold_seconds: int) -> None:
    for second in range(hold_seconds):
        if second % 5 == 0:
            await _log_page_snapshot(page)
        await page.wait_for_timeout(1_000)


async def _log_page_snapshot(page: Any) -> None:
    try:
        title = await page.title()
    except Exception as exc:
        title = f"<title_error:{exc}>"
    try:
        html_size = len(await page.content())
    except Exception:
        html_size = 0
    logger.info(
        "snapshot url={} title={} html_size={}",
        str(getattr(page, "url", "") or ""),
        title,
        html_size,
    )


if __name__ == "__main__":
    main()
