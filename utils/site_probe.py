"""Backward-compatible wrappers for catalog discovery helpers."""

from __future__ import annotations

from utils.catalog_discovery import (
    discover_catalog_site as probe_catalog_site,
    discover_catalog_site_sync as probe_catalog_site_sync,
    summarize_catalog_discovery as summarize_catalog_probe,
)
