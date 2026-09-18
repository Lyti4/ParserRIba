"""Observable protected-store surface waits without blind fixed sleeps."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from utils.protected_store_manual_gate import (
    ProtectedStoreManualGateProfile,
    manual_gate_snapshot,
    manual_gate_snapshot_ready,
)


async def wait_for_observable_store_surface(
    page: Any,
    *,
    max_wait_seconds: int,
    profile: ProtectedStoreManualGateProfile,
    collect_diagnostics: Callable[[Any], Awaitable[Any]],
) -> Any:
    """Return as soon as a page is ready, blocked, or the upper wait limit ends."""
    last_snapshot = await manual_gate_snapshot(
        page,
        collect_diagnostics=collect_diagnostics,
    )
    last_diagnostics = last_snapshot.diagnostics if last_snapshot is not None else None
    if last_snapshot is not None and manual_gate_snapshot_ready(last_snapshot, profile=profile):
        return last_diagnostics

    for _ in range(max(1, int(max_wait_seconds))):
        if last_diagnostics is not None and bool(getattr(last_diagnostics, "blocked", False)):
            return last_diagnostics
        await page.wait_for_timeout(1_000)
        last_snapshot = await manual_gate_snapshot(
            page,
            collect_diagnostics=collect_diagnostics,
        )
        if last_snapshot is None:
            continue
        last_diagnostics = last_snapshot.diagnostics
        if manual_gate_snapshot_ready(last_snapshot, profile=profile):
            return last_diagnostics
    return last_diagnostics
