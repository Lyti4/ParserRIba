"""Generate a source-file flow map for ParserRIba."""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "PROJECT_FILE_FLOW_MAP.md"
EXCLUDED_DIRS = {
    ".agents", ".build-venv", ".git", ".playwright-mcp", ".pytest_cache",
    ".venv", ".yepcode", "__pycache__", "archive", "build", "data", "dist",
    "generated_scaffolds", "logs", "profiles",
}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    module: str
    imports: tuple[str, ...]
    has_main: bool
    uses_argparse: bool
    uses_qapplication: bool


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if not any(part in EXCLUDED_DIRS for part in rel.parts):
            files.append(rel)
    return sorted(files)


def module_name(path: Path) -> str:
    if path.name == "__init__.py":
        return ".".join(path.parent.parts)
    return ".".join(path.with_suffix("").parts)


def parse_source(path: Path, modules: set[str]) -> SourceFile:
    text = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imports: set[str] = set()
    has_main = False
    uses_argparse = "argparse" in text
    uses_qapplication = "QApplication" in text

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.update(local_imports(alias.name, modules))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.update(local_imports(node.module, modules))
            for alias in node.names:
                imports.update(local_imports(f"{node.module}.{alias.name}", modules))
        elif isinstance(node, ast.If) and is_main_guard(node.test):
            has_main = True

    return SourceFile(
        path=path,
        module=module_name(path),
        imports=tuple(sorted(imports)),
        has_main=has_main,
        uses_argparse=uses_argparse,
        uses_qapplication=uses_qapplication,
    )


def local_imports(name: str, modules: set[str]) -> set[str]:
    parts = name.split(".")
    return {".".join(parts[:idx]) for idx in range(1, len(parts) + 1) if ".".join(parts[:idx]) in modules}


def is_main_guard(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "__name__"
        and any(isinstance(item, ast.Constant) and item.value == "__main__" for item in node.comparators)
    )

def role_for(source: SourceFile) -> str:
    path = source.path.as_posix()
    name = source.path.name
    if path == "main.py":
        return "legacy CLI entrypoint"
    if path.startswith("launcher/"):
        return "desktop launcher UI/controller"
    if path.startswith("models/"):
        return "Pydantic/domain model"
    if path.startswith("tests/"):
        return "test"
    if path.startswith("scripts/"):
        return "manual/CLI script"
    if path.startswith("utils/catalog_tree_discovery/"):
        return "catalog discovery core"
    if name in {"local_task_registry.py", "local_task_adapter.py", "launcher_task_controller.py"}:
        return "local task bridge"
    if "storage" in name or "repository" in name:
        return "storage/repository"
    if "report" in name or "excel" in name:
        return "report/export"
    if "pyaterochka" in name:
        return "Pyaterochka adapter/reference"
    if path.startswith("parsers/"):
        return "parser layer"
    if path.startswith("strategies/"):
        return "browser strategy"
    if path.startswith("policies/"):
        return "policy engine"
    return "support module"


def circumstance_for(source: SourceFile, inbound: dict[str, set[str]]) -> str:
    path = source.path.as_posix()
    if source.has_main and source.uses_qapplication:
        return "manual desktop launch"
    if source.has_main and source.uses_argparse:
        return "manual CLI command"
    if source.has_main:
        return "manual/debug command"
    if path.startswith("tests/"):
        return "pytest only"
    if path.startswith("launcher/"):
        return "when desktop launcher is opened"
    if path.startswith("utils/catalog_tree_discovery/"):
        return "during Research/Catalog discovery"
    if "local_task" in path:
        return "when launcher or CLI runs a local task"
    if "pyaterochka" in path:
        return "during Pyaterochka discovery/export/diagnostics"
    if "report" in path or "excel" in path:
        return "during report/filter/export generation"
    if inbound.get(source.module):
        return "imported by runtime modules"
    return "no direct local importer detected"


def package_of(path: Path) -> str:
    return path.parts[0] if len(path.parts) > 1 else path.name

def safe_id(value: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in value)

def label(path: Path) -> str:
    return path.as_posix().replace("/", "<br/>")

def paths_for(modules: list[str] | tuple[str, ...], sources: dict[str, SourceFile], limit: int) -> str:
    paths = [sources[module].path.as_posix() for module in modules if module in sources]
    shown = [f"`{path}`" for path in paths[:limit]]
    if len(paths) > limit:
        shown.append(f"+{len(paths) - limit} more")
    return ", ".join(shown) or "-"


def mermaid_tree(root: str, sources: dict[str, SourceFile], depth: int = 4) -> str:
    lines = ["```mermaid", "flowchart TD"]
    seen: set[tuple[str, str]] = set()

    def walk(module: str, level: int) -> None:
        if level > depth or module not in sources:
            return
        for imported in sources[module].imports:
            if imported not in sources or (module, imported) in seen:
                continue
            seen.add((module, imported))
            lines.append(f"  {safe_id(module)}[{label(sources[module].path)}] --> {safe_id(imported)}[{label(sources[imported].path)}]")
            walk(imported, level + 1)

    if root in sources:
        lines.append(f"  {safe_id(root)}[{label(sources[root].path)}]")
    walk(root, 1)
    lines.append("```")
    return "\n".join(lines)


def package_graph(sources: dict[str, SourceFile]) -> str:
    edges: dict[tuple[str, str], int] = {}
    for source in sources.values():
        left = package_of(source.path)
        for imported in source.imports:
            if imported in sources:
                right = package_of(sources[imported].path)
                if left != right:
                    edges[(left, right)] = edges.get((left, right), 0) + 1
    lines = ["```mermaid", "flowchart LR"]
    for (left, right), count in sorted(edges.items()):
        lines.append(f"  {safe_id(left)}[{left}] -->|{count}| {safe_id(right)}[{right}]")
    lines.append("```")
    return "\n".join(lines)


def git_status_lines() -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=ROOT, check=False, capture_output=True, text=True)
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def build_indexes(sources: dict[str, SourceFile]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    inbound = {module: set() for module in sources}
    test_inbound = {module: set() for module in sources}
    for source in sources.values():
        for imported in source.imports:
            if imported not in sources:
                continue
            target = test_inbound if source.path.as_posix().startswith("tests/") else inbound
            target[imported].add(source.module)
    return inbound, test_inbound


def inventory_lines(sources: dict[str, SourceFile], inbound: dict[str, set[str]], test_inbound: dict[str, set[str]]) -> list[str]:
    lines: list[str] = []
    packages = sorted({package_of(source.path) for source in sources.values()})
    for package in packages:
        lines.extend([f"### {package}", "", "| File | Role | When it runs | Imports | Imported by | Tests |", "| --- | --- | --- | --- | --- | --- |"])
        package_sources = sorted((item for item in sources.values() if package_of(item.path) == package), key=lambda item: item.path.as_posix())
        for source in package_sources:
            rows = [
                f"`{source.path.as_posix()}`",
                role_for(source),
                circumstance_for(source, inbound),
                paths_for(source.imports, sources, 5),
                paths_for(sorted(inbound.get(source.module, set())), sources, 5),
                paths_for(sorted(test_inbound.get(source.module, set())), sources, 3),
            ]
            lines.append("| " + " | ".join(rows) + " |")
        lines.append("")
    return lines


def cleanup_lines(sources: dict[str, SourceFile], inbound: dict[str, set[str]], test_inbound: dict[str, set[str]]) -> list[str]:
    lines = ["## Cleanup Review Queue", "", "These are review candidates, not deletion instructions.", ""]
    lines.extend(["### No production importer detected"])
    for source in sorted(sources.values(), key=lambda item: item.path.as_posix()):
        path = source.path.as_posix()
        if path.startswith("tests/") or source.has_main or path.startswith(("launcher/", "models/")):
            continue
        if not inbound.get(source.module):
            tests = sorted(test_inbound.get(source.module, set()))
            suffix = f"; tests: {', '.join(tests[:3])}" if tests else ""
            lines.append(f"- `{path}` ({role_for(source)}){suffix}")
    lines.extend(["", "### Known legacy or quarantine files"])
    for source in sorted(sources.values(), key=lambda item: item.path.as_posix()):
        if any(marker in source.path.as_posix() for marker in ("base_parser.py", "session_manager.py", "playwright_parser.py")):
            lines.append(f"- `{source.path.as_posix()}`: keep until replacement path and tests are confirmed.")
    lines.extend(["", "### Current untracked/local artifacts"])
    untracked = [line[3:] for line in git_status_lines() if line.startswith("??")]
    lines.extend(f"- `{item}`" for item in untracked)
    if not untracked:
        lines.append("- none")
    lines.append("")
    return lines


def main() -> None:
    paths = iter_python_files()
    modules = {module_name(path) for path in paths}
    sources = {module_name(path): parse_source(path, modules) for path in paths}
    inbound, test_inbound = build_indexes(sources)
    lines = [
        "# ParserRIba Project File Flow Map",
        "",
        "Generated by `scripts/generate_project_flow_map.py`.",
        "",
        "Scope: tracked project Python sources, tests and scripts. Local runtime artifacts such as",
        "`.venv/`, `archive/`, `data/`, `logs/`, `profiles/`, `build/`,",
        "`dist/` and `generated_scaffolds/` are excluded from the import graph.",
        "",
        "## How To Read This",
        "",
        "- `Imports` means direct local Python imports detected by AST.",
        "- `Imported by` excludes tests, so it approximates production/runtime use.",
        "- `Tests` shows test files that import the source directly.",
        "- Cleanup candidates require manual confirmation before removal.",
        "",
        "## Main Runtime Flows",
        "",
    ]
    for title, root in [
        ("Desktop launcher", "scripts.run_desktop_launcher"),
        ("Local task CLI", "scripts.run_local_task"),
        ("Site research", "utils.site_onboarding"),
        ("Store catalog export", "scripts.export_store_catalog"),
        ("Pyaterochka API discovery", "scripts.discover_pyaterochka_api"),
    ]:
        lines.extend([f"### {title}", mermaid_tree(root, sources), ""])
    lines.extend(["## Package Dependency Graph", "", package_graph(sources), "", "## File Inventory", ""])
    lines.extend(inventory_lines(sources, inbound, test_inbound))
    lines.extend(cleanup_lines(sources, inbound, test_inbound))
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
