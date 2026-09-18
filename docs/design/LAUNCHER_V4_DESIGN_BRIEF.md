# ParserRIba Launcher V4 Design Brief

Date: 2026-06-04

## Goal

Build a modern, calm and scalable ParserRIba desktop launcher that still feels like a practical Windows work tool. The launcher must keep the current product path clear:

`Исследование -> Каталог -> Товары -> Отчёт -> Профиль/История`

The design should support future modules without forcing another layout rewrite: profile history, price comparison, proxy diagnostics, store adapters, scheduled refreshes and richer reports.

## Design Direction

Visual theme: historical counterintelligence archive room, USSR-era industrial restraint, no symbols.

Allowed mood:
- dark green enamel desks;
- graphite metal;
- aged paper;
- brass instrument labels;
- red pencil marks as tiny alerts only;
- strict grids, tabs, ledgers, dossier-like panels.

Forbidden motifs:
- no Soviet coat of arms;
- no stars, sickle, hammer, flags, medals or propaganda poster treatment;
- no military ranks, badges or secret-police insignia;
- no decorative slogans.

The launcher should feel like a serious analysis console, not a game, not a landing page and not a retro costume.

## Audience

Primary user: local operator collecting store catalog/product data, solving captcha manually when needed, checking proxy health and exporting Excel reports.

The interface must optimize:
- repeated use;
- readable tables;
- fast diagnosis after failed tasks;
- confidence that data in each tab belongs to the current workspace;
- low visual fatigue.

## Product Principles

1. Current workspace is always visible.
   The user should see active store, profile, selected catalog nodes, product count, filter count and last artifact without switching context.

2. Actions are stage-bound.
   Research actions live in `Исследование`; catalog selection actions live in `Каталог`; product filtering and final product selection live in `Товары`; report columns and export actions live in `Отчёт`.

3. Diagnostics are first-class.
   Errors, proxy status, captcha/protection reasons and latest task details should be copyable from a dedicated diagnostics surface.

4. Future features get reserved space.
   Do not add dormant buttons everywhere. Reserve layout regions and navigation slots that can later host `История цен`, `Планировщик`, `Магазины`, `Настройки`.

5. PySide6 implementation must stay modular.
   `launcher/desktop_launcher.py` is already near the 300-line guideline. New design implementation must use focused modules.

## Layout Model

### Global Shell

Use a three-zone shell:

1. Left navigation rail, fixed width 180-220 px.
2. Main workspace, flexible.
3. Right inspector, fixed width 320-380 px, collapsible later.

Desktop minimum target: 1280 x 760.
Useful target: 1440 x 900.

### Left Navigation Rail

Purpose: persistent workflow map and future modules.

Visible items:
- `Исследование`
- `Каталог`
- `Товары`
- `Отчёт`
- `Профиль`
- `Диагностика`
- `Прокси`

Future disabled/reserved items:
- `История цен`
- `Планировщик`
- `Магазины`

Navigation item states:
- idle;
- active;
- completed;
- warning;
- disabled.

Do not use icons that imply military symbols. Use neutral functional icons later if an icon library is introduced: search, tree, package, file spreadsheet, database, alert, shield/network.

### Top Command Strip

Purpose: show current task and primary action for the active stage.

Fields:
- active store/site;
- profile id/version short label;
- current task status;
- current phase;
- progress counter;
- last result count.

Examples:
- `Пятёрочка | profile pyaterochka:https---5ka-ru | Сбор товаров | 2/4 раздела`
- `Защита сайта: требуется ручная капча`
- `Товары: 60 | Фильтры: 4 | Выбрано для отчёта: 12`

### Main Workspace

Use dense but organized work surfaces. Avoid nested cards. Use full-width bands and splitter-based panels.

Tabs can remain internally while migrating, but target V4 should prefer left navigation with one active workspace at a time.

### Right Inspector

Persistent inspector with stacked sections:
- `Карточка товара` when a product is selected;
- `Магазин и сохранения`;
- `Последняя задача`;
- `Быстрые действия`.

If no product is selected, show profile/session/task details instead of empty text.

### Diagnostics Workspace

Dedicated page/panel for copyable operational details:
- latest error;
- task name/status/phase;
- captcha/protection reason;
- proxy route and masked credentials;
- artifact paths;
- last command/task payload summary;
- "what to do next" user-facing hint.

Copy buttons:
- `Скопировать ошибку`;
- `Скопировать диагностику`;
- `Открыть папку логов` later.

## Screen Structure

### 1. Исследование

Purpose: configure store URL and run site/catalog research.

Main zones:
- store URL input;
- store selector;
- research mode;
- attempts/listen seconds/manual wait/headless;
- primary action `Исследовать магазин`;
- live status panel.

Right inspector:
- current profile;
- browser profile path;
- proxy status summary;
- last research diagnostics.

### 2. Каталог

Purpose: browse discovered catalog tree and choose nodes for product collection.

Main zones:
- catalog search;
- catalog tree with checkboxes;
- selected nodes summary;
- action `Собрать товары по выбранным разделам`.

Required behavior:
- selected nodes stay visible in a compact summary;
- count selected leaf/category URLs;
- if collection is blocked, show exact reason and diagnostics link.

### 3. Товары

Purpose: review collected products, filter them and make final product selection.

Main zones:
- left filter rail inside workspace;
- result table;
- product detail inspector;
- select all shown / clear selection.

Fixed filters:
- price range;
- stock state;
- only filled fields toggle;
- supplier only.

Dynamic filters:
- product type/category-like values from current workspace;
- discovered raw fields such as volume, weight, fat, country, packaging;
- site facets only when mapped and locally applicable.

Do not bring back fixed `Бренд` or fixed `Алкогольный тип`. Alcohol-related fields may appear only as discovered/report raw fields when real product data contains them.

### 4. Отчёт

Purpose: choose columns, preview report and build Excel.

Main zones:
- column checklist;
- editable Excel column titles;
- report preview table;
- action row: `Собрать Excel`, `Открыть Excel`, `Открыть папку`.

Future:
- report presets from StoreProfile;
- compare with previous session;
- price changes.

### 5. Профиль

Purpose: profile/session management.

V4 target:
- list saved profiles;
- list versions/sessions;
- show saved catalog/product/report snapshots;
- load selected session;
- save current workspace.

Initial implementation can still point to latest session if profile browser is not ready.

### 6. Диагностика

Purpose: copy and understand errors.

Main zones:
- latest task log;
- latest error;
- user-facing next step;
- proxy diagnostics;
- captcha/protection diagnostics;
- artifact paths.

### 7. Прокси

Purpose: proxy setup and verification.

Main zones:
- enable proxy;
- protocol;
- batch input;
- parsed proxy list;
- check first proxy;
- status with masked route.

Future:
- rotation strategy;
- RU endpoint validation;
- per-store proxy policy;
- failure history.

## Visual System

### Color Tokens

Use these as design tokens, not scattered hardcoded values.

| Token | Hex | Usage |
| --- | --- | --- |
| `archive.bg` | `#11160F` | app background |
| `archive.surface` | `#192119` | primary panels |
| `archive.surfaceRaised` | `#222B21` | raised controls |
| `archive.paper` | `#EEE6D2` | input/table background in light areas |
| `archive.paperMuted` | `#D7CCB4` | secondary paper |
| `archive.ink` | `#14120E` | text on paper |
| `archive.text` | `#ECE7DA` | text on dark |
| `archive.textMuted` | `#AFA58F` | secondary text |
| `archive.brass` | `#B08A45` | focus, section accents |
| `archive.green` | `#2F4B36` | active navigation |
| `archive.redPencil` | `#9D2E2E` | errors only |
| `archive.border` | `#3B4638` | dark borders |
| `archive.grid` | `#C8BFA9` | table grid on paper |

Rules:
- red is for errors only;
- brass is for focus and selected state, not decoration everywhere;
- tables can use paper surfaces for readability;
- large gradients are not allowed;
- no one-note green screen: combine dark green, paper, brass, graphite and muted red.

### Typography

Keep native Windows readability.

Suggested:
- base font: Segoe UI;
- monospace diagnostics: Consolas;
- table font: Segoe UI 9-10;
- section title: Segoe UI Semibold 11-12;
- no negative letter spacing;
- no viewport-based font scaling.

### Component Rules

Buttons:
- primary: filled dark green with brass border/focus;
- destructive/error: muted red only for real destructive or failed state;
- secondary: raised graphite/green surface.

Inputs:
- paper background for data entry;
- clear focus border;
- placeholders in muted ink.

Tables:
- stable row height;
- no content-driven column jumping;
- horizontal scroll allowed for wide product URLs;
- selected row should remain readable.

Filters:
- supplier search uses prefix search;
- dynamic filter browser remains compact;
- selected filters summary is always visible.

Diagnostics:
- read-only monospace block;
- copy buttons near the text;
- masked secrets by default.

## Figma Brief

Use this prompt when creating a Figma screen from the local design:

```text
Create a Windows desktop application mockup for ParserRIba Launcher V4.
Style: serious local data-collection console, historical archive-room mood,
dark enamel green, graphite metal, warm paper tables, brass focus accents,
muted red only for errors. No Soviet symbols, no stars, no flags, no medals,
no propaganda motifs.

Canvas: desktop 1440x900.
Layout: left navigation rail 200px, top command strip, main workspace,
right inspector 340px.

Screens to create:
1. Исследование: store URL, settings, primary research action, live status.
2. Каталог: searchable catalog tree with checkboxes, selected node summary,
   collect products action.
3. Товары: supplier fixed filter, dynamic filters, product table, product
   card inspector, select shown checkbox.
4. Отчёт: column selection, editable Excel titles, preview table, Excel actions.
5. Диагностика: copyable error log, proxy/captcha/task diagnostics.

Use Russian labels exactly. Keep layout dense, practical and readable.
No marketing hero, no decorative cards inside cards.
```

## Canva Brief

Use Canva for a short internal presentation if needed:

Title: `ParserRIba Launcher V4 UX Concept`

Slide plan:
1. `Цель V4` - why the launcher needs a structured shell.
2. `Пользовательский поток` - Исследование -> Каталог -> Товары -> Отчёт -> Профиль.
3. `Визуальная система` - archive green, paper, brass, graphite, muted red.
4. `Главный экран` - left rail, top command strip, main workspace, inspector.
5. `Товары и фильтры` - supplier fixed, dynamic filters, product selection.
6. `Диагностика` - copyable errors and next-step hints.
7. `Задел на будущее` - profiles, price history, scheduler, multi-store adapters.

Visual style: calm dark green/graphite background, warm paper screenshots, brass lines, restrained red annotations, no state symbols.

## Implementation Constraints

- Do not implement V4 by adding more code to `launcher/desktop_launcher.py`; it is near the line limit.
- Prefer new modules for layout shell, navigation, theme and diagnostics.
- Keep all user-facing strings in Russian.
- Preserve the current working launcher flow while migrating one workspace at a time.
- Keep PySide6 widgets on the GUI thread.
- Use tests before behavior changes.
