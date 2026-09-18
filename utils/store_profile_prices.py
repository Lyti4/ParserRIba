"""Price-history helpers for StoreProfile repository payloads."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.store_profile_payloads import price_observation_row, utc_timestamp


def record_price_observation(
    connection: sqlite3.Connection,
    *,
    workspace_id: str = "default",
    profile_id: str,
    product_id: str,
    product_url: str,
    category: str,
    price: float,
    old_price: float | None,
    in_stock: bool,
    captured_at: str = "",
    session_id: str = "",
) -> int:
    """Append one price observation row."""
    cursor = connection.execute(
        """
        INSERT INTO price_observations (
            workspace_id, profile_id, product_id, product_url, category, price,
            old_price, in_stock, captured_at, session_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            profile_id,
            product_id,
            product_url,
            category,
            float(price),
            old_price,
            int(in_stock),
            captured_at or utc_timestamp(),
            session_id,
        ),
    )
    return int(cursor.lastrowid)


def list_price_observations(
    connection: sqlite3.Connection,
    profile_id: str,
    product_id: str,
    *,
    workspace_id: str = "",
) -> list[dict[str, Any]]:
    """Return price observations for one product in insertion order."""
    workspace_filter = "AND workspace_id = ?" if workspace_id else ""
    params = (profile_id, product_id, workspace_id) if workspace_id else (profile_id, product_id)
    rows = connection.execute(
        """
        SELECT product_id, product_url, category, price, old_price,
               in_stock, captured_at, session_id
        FROM price_observations
        WHERE profile_id = ? AND product_id = ?
        """ + workspace_filter + """
        ORDER BY id
        """,
        params,
    ).fetchall()
    return [price_observation_row(row) for row in rows]


def save_price_observations_from_payload(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    workspace_id: str,
    profile_id: str,
    version_id: str,
    captured_at: str,
) -> None:
    """Persist price observations from one product workspace snapshot."""
    products = payload.get("products") if isinstance(payload.get("products"), dict) else {}
    items = products.get("items") if isinstance(products, dict) else []
    if not isinstance(items, list):
        return
    connection.execute(
        "DELETE FROM price_observations WHERE workspace_id = ? AND profile_id = ? AND session_id = ?",
        (workspace_id, profile_id, version_id),
    )
    for item in items:
        if not isinstance(item, dict):
            continue
        row = _price_observation(item)
        if row is None:
            continue
        connection.execute(
            """
            INSERT INTO price_observations (
                workspace_id, profile_id, product_id, product_url, category, price,
                old_price, in_stock, captured_at, session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workspace_id,
                profile_id,
                row["product_id"],
                row["product_url"],
                row["category"],
                row["price"],
                row["old_price"],
                int(row["in_stock"]),
                captured_at,
                version_id,
            ),
        )


def compare_latest_price_sessions(
    connection: sqlite3.Connection,
    profile_id: str,
    *,
    workspace_id: str = "",
) -> list[dict[str, Any]]:
    """Compare price observations between two latest saved sessions."""
    sessions = _latest_session_ids(connection, profile_id, workspace_id=workspace_id)
    if len(sessions) < 2:
        return []
    current_session, previous_session = sessions[0], sessions[1]
    current = _session_prices(connection, profile_id, current_session, workspace_id=workspace_id)
    previous = _session_prices(connection, profile_id, previous_session, workspace_id=workspace_id)
    product_ids = sorted(set(current) | set(previous))
    return [
        _comparison_row(
            product_id,
            current.get(product_id),
            previous.get(product_id),
            current_session=current_session,
            previous_session=previous_session,
        )
        for product_id in product_ids
    ]


def _price_observation(item: dict[str, Any]) -> dict[str, Any] | None:
    product_id = str(item.get("id") or item.get("product_id") or "").strip()
    price = _current_price(item.get("price"))
    if not product_id or price is None:
        return None
    return {
        "product_id": product_id,
        "product_url": str(item.get("product_link") or item.get("url") or ""),
        "category": str(item.get("category") or ""),
        "price": price,
        "old_price": _old_price(item.get("price")),
        "in_stock": bool(item.get("in_stock", True)),
    }


def _current_price(value: Any) -> float | None:
    raw = value.get("current") if isinstance(value, dict) else value
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _old_price(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("old")
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _latest_session_ids(connection: sqlite3.Connection, profile_id: str, *, workspace_id: str = "") -> list[str]:
    workspace_filter = "AND workspace_id = ?" if workspace_id else ""
    params = (profile_id, workspace_id) if workspace_id else (profile_id,)
    rows = connection.execute(
        """
        SELECT session_id, MAX(captured_at) AS latest_at
        FROM price_observations
        WHERE profile_id = ? AND session_id != ''
        """ + workspace_filter + """
        GROUP BY session_id
        ORDER BY latest_at DESC
        LIMIT 2
        """,
        params,
    ).fetchall()
    return [str(row["session_id"]) for row in rows]


def _session_prices(
    connection: sqlite3.Connection,
    profile_id: str,
    session_id: str,
    *,
    workspace_id: str = "",
) -> dict[str, sqlite3.Row]:
    workspace_filter = "AND workspace_id = ?" if workspace_id else ""
    params = (profile_id, session_id, workspace_id) if workspace_id else (profile_id, session_id)
    rows = connection.execute(
        """
        SELECT product_id, product_url, category, price, old_price, in_stock
        FROM price_observations
        WHERE profile_id = ? AND session_id = ?
        """ + workspace_filter + """
        """,
        params,
    ).fetchall()
    return {str(row["product_id"]): row for row in rows}


def _comparison_row(
    product_id: str,
    current: sqlite3.Row | None,
    previous: sqlite3.Row | None,
    *,
    current_session: str,
    previous_session: str,
) -> dict[str, Any]:
    current_price = float(current["price"]) if current else None
    previous_price = float(previous["price"]) if previous else None
    return {
        "product_id": product_id,
        "product_url": _row_value(current, previous, "product_url"),
        "category": _row_value(current, previous, "category"),
        "previous_session_id": previous_session,
        "current_session_id": current_session,
        "previous_price": previous_price,
        "current_price": current_price,
        "price_delta": _price_delta(current_price, previous_price),
        "change_status": _change_status(current_price, previous_price),
        "previous_in_stock": bool(previous["in_stock"]) if previous else None,
        "current_in_stock": bool(current["in_stock"]) if current else None,
    }


def _row_value(primary: sqlite3.Row | None, fallback: sqlite3.Row | None, key: str) -> str:
    row = primary or fallback
    return str(row[key]) if row else ""


def _price_delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 2)


def _change_status(current: float | None, previous: float | None) -> str:
    if current is None:
        return "missing"
    if previous is None:
        return "new"
    if current == previous:
        return "unchanged"
    return "changed"
