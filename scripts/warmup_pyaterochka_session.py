"""Open a quiet Pyaterochka Camoufox session for manual challenge warmup."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from camoufox.async_api import AsyncCamoufox

from scripts.discover_pyaterochka_api import PROFILE_DIR
from utils.antibot import collect_page_diagnostics
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.proxy import choose_proxy_for_attempt, load_proxy_config_from_env, mask_proxy_url


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm up the persistent Pyaterochka browser session manually.")
    parser.add_argument("--url", default="https://5ka.ru/catalog/")
    parser.add_argument("--no-proxy", action="store_true", dest="no_proxy")
    parser.add_argument("--headless", action="store_true", dest="headless")
    return parser.parse_args(argv)


async def _main(argv: list[str] | None = None) -> int:
    configure_windows_console()
    args = _parse_args(argv)
    load_dotenv_file(ROOT_DIR / ".env")
    proxy_url = "" if args.no_proxy else _first_proxy()
    geoip_enabled = bool(proxy_url) and os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    launch_options = build_camoufox_options(
        headless=bool(args.headless),
        proxy_url=proxy_url or None,
        geoip=geoip_enabled,
        user_data_dir=PROFILE_DIR,
        use_fingerprint_profile=False,
    )
    result: dict[str, Any] = {
        "url": args.url,
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "profile_dir": str(PROFILE_DIR),
        "identity_exists": (PROFILE_DIR / "camoufox_identity.pkl").exists(),
    }
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
        _write_stdout("Camoufox открыт. Пройди проверку вручную, дождись обычной страницы и нажми Enter здесь.\n")
        await asyncio.to_thread(input)
        diagnostics = await collect_page_diagnostics(page)
        result.update(
            {
                "final_url": diagnostics.final_url,
                "blocked": diagnostics.blocked,
                "reason": diagnostics.reason,
                "title": diagnostics.title,
                "html_size": diagnostics.html_size,
            }
        )
    result["cookies"] = _safe_cookie_names()
    _write_stdout(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if not result.get("blocked") else 2


def _first_proxy() -> str:
    proxies = load_proxy_config_from_env(os.environ).urls
    return choose_proxy_for_attempt(proxies, 1) if proxies else ""


def _safe_cookie_names() -> list[str]:
    cookies_path = PROFILE_DIR / "cookies.sqlite"
    if not cookies_path.exists():
        return []
    connection = sqlite3.connect(f"file:{cookies_path}?mode=ro", uri=True)
    rows = connection.execute(
        "select distinct name from moz_cookies where host like ? order by name",
        ("%5ka.ru%",),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _write_stdout(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
