"""Protected-store browser profile constants."""

from __future__ import annotations

from pathlib import Path

from utils.protected_store_manual_gate import ProtectedStoreManualGateProfile

REFERENCE_STORE_RESEARCH_STATE_SETTLE_SECONDS = 10
REFERENCE_STORE_OBSERVABLE_SURFACE_WAIT_SECONDS = 20
REFERENCE_STORE_PROFILE_DIR = Path(__file__).resolve().parents[1] / "profiles" / "pyaterochka"
REFERENCE_STORE_MANUAL_GATE_PROFILE = ProtectedStoreManualGateProfile(
    challenge_paths=("/xpvnsulc/", "/exhkqyad"),
    loading_title_prefix="loading https://5ka.ru/",
    hard_block_reasons=(
        "pyaterochka_antibot_redirect",
        "pyaterochka_antibot_query",
        "pyaterochka_vpn_connection_block",
        "pyaterochka_loading_challenge",
    ),
)
