"""Public controller methods for favorites."""

from __future__ import annotations

from typing import Any

from launcher import desktop_controller_favorites as favorites


class DesktopControllerFavoritesMixin:
    """Thin public actions over favorites helper functions."""

    def hydrate_workspace_favorites(self) -> list[Any]:
        return favorites.load_workspace_favorites(self)

    def load_workspace_favorites(self) -> list[Any]:
        items = favorites.load_workspace_favorites(self); self.save_state(); return items

    def add_current_profile_favorite(self) -> list[Any]:
        items = favorites.add_current_profile_favorite(self); self.save_state(); return items

    def add_selected_catalog_favorites(self) -> list[Any]:
        items = favorites.add_selected_catalog_favorites(self); self.save_state(); return items

    def add_selected_product_favorites(self) -> list[Any]:
        items = favorites.add_selected_product_favorites(self); self.save_state(); return items

    def remove_workspace_favorites(self, favorite_ids: list[str]) -> list[Any]:
        items = favorites.remove_workspace_favorites(self, favorite_ids); self.save_state(); return items

    def refresh_selected_workspace_favorites(self) -> list[Any]:
        items = favorites.refresh_workspace_favorites(self, favorite_ids=self.state.favorites.selected_favorite_ids); self.save_state(); return items

    def refresh_all_workspace_favorites(self) -> list[Any]:
        items = favorites.refresh_workspace_favorites(self, all_refreshable=True); self.save_state(); return items
