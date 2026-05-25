# ParserRIba Archive

This folder keeps project history that should not stay in active runtime or
current planning paths, but also should not be deleted.

## Layout

- `project_history/root_docs/` - old root-level architecture and implementation
  documents superseded by `docs/ROADMAP_V1.md`, `docs/PROJECT_STATE.md` and
  `docs/NEXT_STEPS.md`.
- `project_history/superpowers/plans/` - completed implementation plans kept as
  history. Current specs stay in `docs/superpowers/specs/`.
- `project_history/research_notes/` - old research reports and diagnostics
  notes superseded by current architecture documents.

## Rules

- Do not import runtime code from `archive/`.
- Do not store secrets, cookies, captcha tokens, proxy credentials, profiles,
  databases, logs or generated reports here.
- If a file is moved here, update every active doc reference in the same change.
