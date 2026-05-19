"""SQLite-backed local product and price-history storage."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.schemas import Product
from utils.onboarding_storage import initialize_onboarding_tables


class ProductStorage:
    """Persist current product state and append-only price history."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create storage tables if they do not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    store TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    product_link TEXT NOT NULL,
                    image_url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    in_stock INTEGER NOT NULL,
                    current_price REAL NOT NULL,
                    old_price REAL,
                    unit_price REAL,
                    currency TEXT NOT NULL,
                    raw_data TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (store, product_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    old_price REAL,
                    unit_price REAL,
                    currency TEXT NOT NULL,
                    in_stock INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_price_history_lookup "
                "ON price_history(store, product_id, captured_at)"
            )
            initialize_onboarding_tables(connection)

    def save_products(self, store: str, products: list[Product]) -> None:
        """Upsert current product state and append price history rows."""
        if not products:
            return
        self.initialize()
        timestamp = datetime.now(UTC).isoformat(timespec="microseconds")
        with self._connect() as connection:
            for product in products:
                product_id = str(product.id or "")
                if not product_id:
                    continue
                connection.execute(
                    """
                    INSERT INTO products (
                        store, product_id, name, product_link, image_url, category,
                        in_stock, current_price, old_price, unit_price, currency,
                        raw_data, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(store, product_id) DO UPDATE SET
                        name=excluded.name,
                        product_link=excluded.product_link,
                        image_url=excluded.image_url,
                        category=excluded.category,
                        in_stock=excluded.in_stock,
                        current_price=excluded.current_price,
                        old_price=excluded.old_price,
                        unit_price=excluded.unit_price,
                        currency=excluded.currency,
                        raw_data=excluded.raw_data,
                        updated_at=excluded.updated_at
                    """,
                    (
                        store,
                        product_id,
                        product.name,
                        str(product.product_link),
                        str(product.image_url or ""),
                        str(product.category or ""),
                        int(product.in_stock),
                        float(product.price.current),
                        product.price.old,
                        product.price.unit,
                        product.price.currency,
                        json.dumps(product.raw_data or {}, ensure_ascii=False, sort_keys=True),
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO price_history (
                        store, product_id, captured_at, current_price, old_price,
                        unit_price, currency, in_stock
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        store,
                        product_id,
                        timestamp,
                        float(product.price.current),
                        product.price.old,
                        product.price.unit,
                        product.price.currency,
                        int(product.in_stock),
                    ),
                )

    def list_products(self, store: str) -> list[dict[str, Any]]:
        """Return current stored products for one store."""
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT store, product_id, name, product_link, image_url, category,
                       in_stock, current_price, old_price, unit_price, currency
                FROM products
                WHERE store = ?
                ORDER BY name
                """,
                (store,),
            ).fetchall()
        return [_row_to_product(row) for row in rows]

    def list_price_history(self, store: str, product_id: str) -> list[dict[str, Any]]:
        """Return price history for one stored product."""
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT captured_at, current_price, old_price, unit_price, currency, in_stock
                FROM price_history
                WHERE store = ? AND product_id = ?
                ORDER BY id
                """,
                (store, product_id),
            ).fetchall()
        return [_row_to_history(row) for row in rows]

    def latest_snapshot_report(self, store: str) -> dict[str, Any]:
        """Compare the two latest snapshot timestamps for one store."""
        if not self.db_path.exists():
            return _empty_snapshot_report()
        with self._connect() as connection:
            snapshot_rows = connection.execute(
                """
                SELECT DISTINCT captured_at
                FROM price_history
                WHERE store = ?
                ORDER BY captured_at DESC
                LIMIT 2
                """,
                (store,),
            ).fetchall()
            current_products = connection.execute(
                "SELECT COUNT(*) AS total FROM products WHERE store = ?",
                (store,),
            ).fetchone()
        if not snapshot_rows:
            return _empty_snapshot_report()
        latest_snapshot_at = str(snapshot_rows[0]["captured_at"])
        previous_snapshot_at = str(snapshot_rows[1]["captured_at"]) if len(snapshot_rows) > 1 else ""
        latest = self._snapshot_rows(store, latest_snapshot_at)
        previous = self._snapshot_rows(store, previous_snapshot_at) if previous_snapshot_at else {}
        changed_prices: list[dict[str, Any]] = []
        changed_availability: list[dict[str, Any]] = []
        for product_id, current in latest.items():
            earlier = previous.get(product_id)
            if not earlier:
                continue
            if float(current["current_price"]) != float(earlier["current_price"]):
                changed_prices.append(
                    {
                        "product_id": product_id,
                        "name": str(current["name"]),
                        "previous_price": float(earlier["current_price"]),
                        "current_price": float(current["current_price"]),
                    }
                )
            if bool(current["in_stock"]) != bool(earlier["in_stock"]):
                changed_availability.append(
                    {
                        "product_id": product_id,
                        "name": str(current["name"]),
                        "previous_in_stock": bool(earlier["in_stock"]),
                        "current_in_stock": bool(current["in_stock"]),
                    }
                )
        return {
            "products_count": int(current_products["total"] if current_products else 0),
            "latest_snapshot_at": latest_snapshot_at,
            "previous_snapshot_at": previous_snapshot_at,
            "changed_prices": changed_prices,
            "changed_availability": changed_availability,
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _snapshot_rows(self, store: str, captured_at: str) -> dict[str, dict[str, Any]]:
        if not captured_at:
            return {}
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT h.product_id, h.current_price, h.in_stock, p.name
                FROM price_history h
                JOIN products p
                  ON p.store = h.store AND p.product_id = h.product_id
                WHERE h.store = ? AND h.captured_at = ?
                """,
                (store, captured_at),
            ).fetchall()
        return {
            str(row["product_id"]): {
                "current_price": float(row["current_price"]),
                "in_stock": bool(row["in_stock"]),
                "name": str(row["name"]),
            }
            for row in rows
        }


def _row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "store": str(row["store"]),
        "product_id": str(row["product_id"]),
        "name": str(row["name"]),
        "product_link": str(row["product_link"]),
        "image_url": str(row["image_url"]),
        "category": str(row["category"]),
        "in_stock": bool(row["in_stock"]),
        "current_price": float(row["current_price"]),
        "old_price": row["old_price"],
        "unit_price": row["unit_price"],
        "currency": str(row["currency"]),
    }


def _row_to_history(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "captured_at": str(row["captured_at"]),
        "current_price": float(row["current_price"]),
        "old_price": row["old_price"],
        "unit_price": row["unit_price"],
        "currency": str(row["currency"]),
        "in_stock": bool(row["in_stock"]),
    }


def _empty_snapshot_report() -> dict[str, Any]:
    return {
        "products_count": 0,
        "latest_snapshot_at": "",
        "previous_snapshot_at": "",
        "changed_prices": [],
        "changed_availability": [],
    }
