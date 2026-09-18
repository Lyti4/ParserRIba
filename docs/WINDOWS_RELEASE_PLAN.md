# Windows x64 release plan (v1)

## Scope and release boundary

This plan turns the existing launcher-first product into a **portable Windows x64 candidate**, not a public release. It does not replace the product architecture or promise that a browser, a protected store, or Windows works before that surface is actually exercised.

The active path is:

`Launcher -> Task Orchestrator -> Browser/Discovery -> Store Adapter -> Product/Filter/Report -> Storage/Profile`

Legacy `main.py` and its parser factory are compatibility/history evidence, not the active launcher entry. The candidate entry is `scripts/run_desktop_launcher.py`.

## Capability and evidence matrix

| Capability | Status | Evidence / release requirement | Owner |
| --- | --- | --- | --- |
| Launcher shell, Russian guided routes, themes/settings | implemented-unverified | `launcher/`, `scripts/run_desktop_launcher.py --smoke`; exercise on clean Windows | builder + Windows operator |
| Local task bridge; discovery/onboarding; generic `store_catalog_export`; report/filter support; compatibility Pyaterochka aliases | implemented-unverified | `utils/local_task_*`, registry and launcher controller; validate selected task results/errors on Windows | builder |
| Catalog tree and selected-node product collection | implemented-unverified | documented active flow; requires manual Windows acceptance with a permitted fixture or live gate | Windows operator |
| Pyaterochka protected adapter/manual gate/capture/export | implemented-unverified | adapter and shared gate exist; no R0 live crawl, login, proxy, or captcha test | human-gated operator |
| Browser runtime registry and Camoufox default | implemented-unverified | runtime models/registry; P1 focused Python tests cover selected runtime propagation only | builder + reviewer |
| Experimental CloakBrowser selection | blocked | preserve selected semantics; license, target binary provenance, compatibility, installation and A/B evidence are absent; do not bundle/copy Linux runtime/profile | human + reviewer |
| Product workspace, dynamic filters, selected products, Excel/JSON reports | implemented-unverified | documented launcher/report contracts; verify persistence/export on clean Windows | Windows operator |
| SQLite StoreProfile, sessions, presets, journal, price history | implemented-unverified | documented local storage contracts; verify save/load and cancellation recovery on Windows | Windows operator |
| Error, timeout and cancel recovery | implemented-unverified | task boundary/manual gate documented; perform a bounded manual cancel and restart on Windows | Windows operator |
| Offline focused runtime regression | verified (narrow) | P1 receipt: 24 passed, 0 failed/errors/skips; not full application validation | builder |
| Windows portable build, artifact checksums and executable smoke | blocked | no connected Windows runner or completed Windows build receipt | Windows CI/operator |
| Public release/installer/update delivery | blocked | explicit human gate after clean-machine evidence, review, provenance, changelog and rollback approval | Dmitry |
| Extra stores, remote backend, paid/cloud services, Cloak binary redistribution | optional / out of v1 | excluded unless separately approved | human |

## Finite v1 acceptance matrix

1. **Source and artifact hygiene:** release diff reviewed; no `.env`, credentials, cookies, profiles, `data/`, `logs/`, `build/`, `dist/` or browser binaries in source artifact. A provenance manifest records Python, dependency inputs, build script, workflow revision, artifact SHA256 and external-runtime policy.
2. **Reproducible candidate build:** a manually dispatched Windows job runs `scripts/build_windows.ps1` with its actual `-Python` and `-Clean` parameters on an ephemeral runner, produces the ZIP and matching SHA256, and uploads them only as a CI artifact.
3. **Executable launch:** produced `ParserRIba.exe --smoke` exits successfully. This is launcher-shell evidence only; it is not a live store/browser claim.
4. **Offline quality gate:** current focused tests, compile/architecture guards and explicit failure receipts are attached. Full-suite expansion needs a separate bounded task.
5. **Clean Windows manual acceptance:** a human tests launcher routes, runtime selection availability, settings/theme, save/load profile/session, report export, an intentional cancel/error then recovery, and instructions. Any live Pyaterochka/browser action is separately gated and documented.
6. **Release handoff:** version/changelog, checksum, user instructions, known limitations, rollback artifact location, reviewer acceptance and Dmitry publication approval exist before upload/release/tag.

## Milestones and gates

- **R0 (this packet):** plan, checklist extension and a `workflow_dispatch`-only offline Windows build candidate. No remote run, publish, installer, browser download, live scraping or profile access.
- **R1:** reconcile active launcher CLI with stale `ParserRIba.spec`/legacy checklist commands. Smallest task: decide and document one supported packaged executable contract (`--smoke` is currently evidenced; `--check-env`/`--list-stores` are legacy-main claims) before requiring those commands in release acceptance.
- **R2:** run the candidate on a real Windows runner; retain raw logs, artifact manifest, ZIP and SHA256. Failure returns to a bounded source task.
- **R3:** human clean-machine manual acceptance for settings, persistence, export and cancel/recovery. Browser/crawl/captcha checks require their own explicit gate.
- **R4:** independent review, license/provenance review for browser runtimes, version/changelog/rollback confirmation, then Dmitry decides publication.

## Runtime provenance and limitations

Camoufox is the documented stable default. The Python package, an external browser binary and any GUI-managed server runtime are different assets. R0 neither downloads nor packages a browser binary. CloakBrowser remains experimental: no binary redistribution, auto-update, profile/cookie transfer or licensing claim is allowed without a separate approved review. Linux checks and a Windows-hosted workflow definition do not validate a real Windows artifact until the job runs successfully.
