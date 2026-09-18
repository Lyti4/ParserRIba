"""Bounded, no-site selected-Cloak frozen executable probe."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from models.browser_runtime import BrowserRuntimeLaunchRequest
from utils.browser_runtime import check_browser_runtime, launch_research_browser


def run_cloak_probe(result_path: Path) -> int:
    """Start Cloak once, assert local DOM, close, then write a safe receipt."""
    return asyncio.run(_run_cloak_probe(result_path))


async def _run_cloak_probe(result_path: Path) -> int:
    availability = check_browser_runtime("cloak")
    if not availability.is_available:
        raise RuntimeError(availability.message_ru)

    profile_dir = Path(os.environ["PARSERRIBA_CLOAK_PROBE_PROFILE"])
    profile_dir.mkdir(parents=True, exist_ok=True)
    request = BrowserRuntimeLaunchRequest(kind="cloak", headless=True, user_data_dir=profile_dir)
    async with launch_research_browser(request) as browser:
        page = await browser.new_page()
        await page.goto("about:blank")
        dom_title = await page.evaluate("document.title")

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            {
                "runtime": "cloak",
                "started": True,
                "dom_title": dom_title,
                "closed": True,
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0
