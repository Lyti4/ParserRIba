from pathlib import Path

from scripts.architecture_check import (
    Finding,
    find_tracked_artifacts,
    render_findings,
    scan_python_file,
)


def test_find_tracked_artifacts_flags_generated_files() -> None:
    findings = find_tracked_artifacts(
        [
            "models/__pycache__/product.cpython-312.pyc",
            "logs/parser_riba.json",
            ".env.example",
            "main.py",
        ]
    )

    assert [item.code for item in findings] == ["tracked-artifact", "tracked-artifact"]
    assert all(item.severity == "error" for item in findings)


def test_scan_python_file_flags_time_sleep(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("import time\n\ndef f():\n    time.sleep(1)\n", encoding="utf-8")

    findings = scan_python_file(sample, root=tmp_path)

    assert any(item.code == "time-sleep" and item.severity == "error" for item in findings)


def test_scan_python_file_flags_parser_hardcoded_url(tmp_path: Path) -> None:
    parser_dir = tmp_path / "parsers"
    parser_dir.mkdir()
    sample = parser_dir / "demo.py"
    sample.write_text('URL = "https://example.com/catalog"\n', encoding="utf-8")

    findings = scan_python_file(sample, root=tmp_path)

    assert any(item.code == "hardcoded-url" for item in findings)


def test_scan_python_file_allows_extended_limit_for_tests(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    sample = tests_dir / "demo_test.py"
    sample.write_text("\n".join(f"line_{index} = {index}" for index in range(400)), encoding="utf-8")

    findings = scan_python_file(sample, root=tmp_path)

    assert not any(item.code == "long-file" for item in findings)


def test_render_findings_groups_by_severity() -> None:
    report = render_findings(
        [
            Finding("error", "tracked-artifact", "logs/x.json", 0, "Tracked log."),
            Finding("warning", "long-file", "scripts/x.py", 0, "Too long."),
        ]
    )

    assert "## Errors" in report
    assert "## Warnings" in report
    assert "`tracked-artifact`" in report
