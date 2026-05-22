"""Interactive browser preview builder for the desktop launcher layout."""

from __future__ import annotations

import html
import json

from launcher.desktop_filter_panel import FILTER_WIDGET_KEYS
from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts
from launcher.desktop_result_table import build_result_table
from launcher.desktop_view_helpers import build_status_text
from models.launcher_state import LauncherAppState

def build_browser_preview_html(state: LauncherAppState) -> str:
    """Build a static interactive HTML preview from the current launcher state."""
    table = _normalize_preview_table(build_result_table(state))
    filters = {
        key: build_filter_option_labels(extract_filter_counts(state.result.launcher_view, key))
        for key in FILTER_WIDGET_KEYS
    }
    payload = {
        "status": build_status_text(state),
        "summary": _build_preview_summary(state),
        "site_url": "https://5ka.ru",
        "shop": state.selection.shop,
        "intent": state.selection.intent,
        "categories": state.selection.categories,
        "settings": state.settings.model_dump(mode="json"),
        "filters": filters,
        "table": table,
    }
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ParserRIba Launcher Preview</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f3f4f6; color: #111827; }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
    .panel {{ background: #fff; border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    .title {{ font-size: 24px; font-weight: 700; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    label {{ display: block; font-size: 13px; color: #374151; margin-bottom: 6px; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; }}
    .list {{ min-height: 112px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; overflow: auto; }}
    .pill {{ display: inline-block; margin: 4px; padding: 6px 10px; border-radius: 999px; background: #eff6ff; border: 1px solid #bfdbfe; cursor: pointer; user-select: none; }}
    .pill.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    button {{ border: 1px solid #cbd5e1; background: #fff; padding: 10px 14px; border-radius: 6px; cursor: pointer; }}
    button:hover {{ background: #f8fafc; }}
    .muted {{ color: #6b7280; font-size: 13px; }}
    .status {{ font-size: 14px; margin-bottom: 8px; }}
    .summary {{ white-space: pre-wrap; color: #374151; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; text-align: left; padding: 10px 8px; vertical-align: top; }}
    th {{ background: #f9fafb; position: sticky; top: 0; }}
    .table-wrap {{ overflow: auto; max-height: 340px; border: 1px solid #e5e7eb; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="title">ParserRIba Browser Preview</div>
      <div class="grid">
        <div style="grid-column: span 4;">
          <label>Site URL</label>
          <input value="{html.escape(payload["site_url"])}">
        </div>
        <div>
          <label>Store</label>
          <select><option selected>{html.escape(str(payload["shop"]))}</option></select>
        </div>
        <div>
          <label>Export Intent</label>
          <select><option selected>{html.escape(str(payload["intent"]))}</option></select>
        </div>
        <div style="grid-column: span 2;">
          <label>Categories</label>
          <div class="list" id="categories"></div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="grid-2" id="filters"></div>
    </div>
    <div class="panel">
      <div class="actions">
        <button id="action-onboarding">Onboarding</button>
        <button id="action-export">Run Export</button>
        <button id="action-filters">Load Filters</button>
        <button id="action-report">Build Excel</button>
        <button id="action-save">Save Settings</button>
      </div>
    </div>
    <div class="panel">
      <div class="grid">
        <div><label><input id="setting-headless" type="checkbox" {"checked" if payload["settings"]["headless"] else ""}> Headless</label></div>
        <div><label><input id="setting-manual-wait" type="checkbox" {"checked" if payload["settings"]["manual_wait"] else ""}> Manual wait</label></div>
        <div><label>Attempts</label><input value="{payload["settings"]["attempts"]}"></div>
        <div><label>Listen seconds</label><input value="{payload["settings"]["listen_seconds"]}"></div>
      </div>
    </div>
    <div class="panel">
      <div class="status" id="status-text">{html.escape(payload["status"])}</div>
      <div class="summary" id="summary-text">{html.escape(payload["summary"])}</div>
    </div>
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr>{"".join(f"<th>{html.escape(str(h))}</th>" for h in payload["table"]["headers"])}</tr></thead>
          <tbody id="result-rows"></tbody>
        </table>
      </div>
      <div class="actions" style="margin-top: 12px;">
        <button id="action-open-excel">Open Excel</button>
        <button id="action-open-folder">Open Folder</button>
        <button id="action-open-json">Open JSON</button>
      </div>
      <div class="muted" id="action-note">Preview actions update the launcher state text locally in the browser.</div>
    </div>
  </div>
  <script>
    const data = {json.dumps(payload, ensure_ascii=False)};
    const statusRoot = document.getElementById("status-text");
    const summaryRoot = document.getElementById("summary-text");
    const actionNoteRoot = document.getElementById("action-note");
    const categoryRoot = document.getElementById("categories");
    for (const category of data.categories) {{
      const pill = document.createElement("span");
      pill.className = "pill active";
      pill.textContent = category;
      pill.onclick = () => pill.classList.toggle("active");
      categoryRoot.appendChild(pill);
    }}
    const filterRoot = document.getElementById("filters");
    const filterTitles = {{
      suppliers: "Suppliers",
      brands: "Brands",
      wine_styles: "Wine Style",
      alcohol_types: "Alcohol Type",
      sugar_classes: "Sugar Class",
      colors: "Color",
    }};
    for (const [key, values] of Object.entries(data.filters)) {{
      const panel = document.createElement("div");
      panel.dataset.filter = key;
      panel.innerHTML = `<label>${{filterTitles[key]}}</label><div class="list"></div>`;
      const list = panel.querySelector(".list");
      for (const [value, label] of values) {{
        const pill = document.createElement("span");
        pill.className = "pill";
        pill.textContent = label;
        pill.dataset.value = value;
        pill.onclick = () => pill.classList.toggle("active");
        list.appendChild(pill);
      }}
      filterRoot.appendChild(panel);
    }}
    const rowsRoot = document.getElementById("result-rows");
    for (const row of data.table.rows) {{
      const tr = document.createElement("tr");
      for (const cell of row) {{
        const td = document.createElement("td");
        td.textContent = cell;
        tr.appendChild(td);
      }}
      rowsRoot.appendChild(tr);
    }}

    function selectedCount(rootSelector) {{
      return document.querySelectorAll(`${{rootSelector}} .pill.active`).length;
    }}

    function updateStatus(message, lines) {{
      statusRoot.textContent = message;
      summaryRoot.textContent = lines.join("\\n");
    }}

    document.getElementById("action-onboarding").onclick = () => {{
      updateStatus(
        "Store: pyaterochka | Intent: fish_catalog | Task: site_onboarding_discovery | Status: succeeded",
        [
          "Preview onboarding completed.",
          `Selected categories: ${{selectedCount("#categories")}}`,
          "Catalog surface: category_tree",
        ],
      );
      actionNoteRoot.textContent = "Onboarding preview refreshed status and diagnostics.";
    }};

    document.getElementById("action-filters").onclick = () => {{
      const supplierCount = data.filters.suppliers.length;
      const brandCount = data.filters.brands.length;
      updateStatus(
        "Store: pyaterochka | Intent: fish_catalog | Task: store_report_filter_options | Status: succeeded",
        [
          "Filter options loaded from local SQLite preview data.",
          `Suppliers available: ${{supplierCount}}`,
          `Brands available: ${{brandCount}}`,
        ],
      );
      actionNoteRoot.textContent = "Filter facets are interactive. Click pills to simulate selection.";
    }};

    document.getElementById("action-export").onclick = () => {{
      const supplierSelected = selectedCount("[data-filter='suppliers']");
      updateStatus(
        "Store: pyaterochka | Intent: fish_catalog | Task: pyaterochka_fish_export | Status: succeeded",
        [
          "Preview export completed.",
          `Categories selected: ${{selectedCount("#categories")}}`,
          `Supplier filters active: ${{supplierSelected}}`,
          `Rows in result table: ${{data.table.rows.length}}`,
        ],
      );
      actionNoteRoot.textContent = "Export preview uses the current category and filter selections.";
    }};

    document.getElementById("action-report").onclick = () => {{
      updateStatus(
        "Store: pyaterochka | Intent: fish_catalog | Task: store_report_export | Status: succeeded",
        [
          "Excel report built in preview mode.",
          "Output target: data/reports/pyaterochka_fish_report.xlsx",
          `Products in report: ${{data.table.rows.reduce((acc, row) => acc + Number(row[1] || 0), 0)}}`,
        ],
      );
      actionNoteRoot.textContent = "Report action simulates creating the Excel artifact.";
    }};

    document.getElementById("action-save").onclick = () => {{
      updateStatus(
        "Store: pyaterochka | Intent: fish_catalog | Task: launcher_settings_save | Status: succeeded",
        [
          "Launcher settings saved locally in preview mode.",
          `Headless: ${{document.getElementById("setting-headless").checked ? "on" : "off"}}`,
        ],
      );
      actionNoteRoot.textContent = "Settings save is simulated in-browser for this preview.";
    }};

    for (const [id, label] of [
      ["action-open-excel", "Excel artifact would open here."],
      ["action-open-folder", "Report folder would open here."],
      ["action-open-json", "JSON export would open here."],
    ]) {{
      document.getElementById(id).onclick = () => {{
        actionNoteRoot.textContent = label;
      }};
    }}
  </script>
</body>
</html>"""


def _build_preview_summary(state: LauncherAppState) -> str:
    """Build an ASCII-safe summary for the browser preview."""
    view = state.result.launcher_view
    lines = [str(state.task.message or "").strip() or "Preview mode"]
    report_summary = view.get("report_summary")
    if isinstance(report_summary, dict):
        products_count = report_summary.get("products_count")
        categories = report_summary.get("categories")
        if products_count is not None:
            lines.append(f"Report products: {products_count}")
        if isinstance(categories, list) and categories:
            lines.append(f"Categories: {', '.join(str(item) for item in categories)}")
    filter_counts = view.get("available_filter_counts")
    if isinstance(filter_counts, dict):
        suppliers = filter_counts.get("suppliers")
        if isinstance(suppliers, dict) and suppliers:
            lines.append(f"Suppliers available: {len(suppliers)}")
    return "\n".join(line for line in lines if line)


def _normalize_preview_table(table: dict[str, list[list[str]] | list[str]]) -> dict[str, list[list[str]] | list[str]]:
    """Map launcher table shapes to clean browser-preview headers."""
    rows = table.get("rows")
    if not isinstance(rows, list):
        rows = []
    headers = table.get("headers")
    header_count = len(headers) if isinstance(headers, list) else 0
    if header_count == 9:
        normalized_headers = ["Category", "Product", "Brand", "Supplier", "Style", "Alcohol Type", "Price", "In Stock", "Link"]
    elif header_count == 4:
        normalized_headers = ["Category", "Products", "Top Supplier", "Top Brand"]
    else:
        normalized_headers = [str(item) for item in headers] if isinstance(headers, list) else []
    return {"headers": normalized_headers, "rows": rows}
