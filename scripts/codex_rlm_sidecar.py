"""Codex-only RLM sidecar controls for ParserRIba agent work."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.local_agent_os import DEFAULT_AGENT_ROOT, assert_safe_for_obsidian

DEFAULT_RUNTIME_ROOT = ROOT / "tools" / "rlm-runtime"
DEFAULT_RLM_REPO = Path(os.environ.get("PARSERRIBA_RLM_REPO", r"C:\tmp\rlm-study"))
DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
SAFE_ENVIRONMENTS = {"local", "ipython"}
CLOUD_ENVIRONMENTS = {"modal", "prime", "daytona", "e2b"}
LOCAL_BACKENDS = {"vllm"}
EXTERNAL_BACKENDS = {"openai", "anthropic", "openrouter", "portkey"}


@dataclass(frozen=True)
class RLMPolicy:
    """Resolved execution policy for one RLM sidecar request."""

    backend: str
    environment: str
    base_url: str | None
    allow_external_provider: bool = False
    allow_cloud_environment: bool = False


@dataclass(frozen=True)
class RLMStatus:
    """Installed sidecar runtime status."""

    runtime_python: str
    runtime_exists: bool
    upstream_repo: str
    upstream_exists: bool
    rlms_importable: bool
    optional_imports: dict[str, bool]
    detail: str


def runtime_python(runtime_root: Path = DEFAULT_RUNTIME_ROOT) -> Path:
    return runtime_root / ".venv" / "Scripts" / "python.exe"


def validate_policy(policy: RLMPolicy) -> None:
    """Fail closed unless a request is local-first or explicitly allowed."""
    if policy.environment in CLOUD_ENVIRONMENTS and not policy.allow_cloud_environment:
        raise ValueError(
            f"Cloud RLM environment '{policy.environment}' requires explicit approval."
        )
    if policy.environment not in SAFE_ENVIRONMENTS | CLOUD_ENVIRONMENTS:
        raise ValueError(f"Unknown RLM environment: {policy.environment}")

    if policy.backend in LOCAL_BACKENDS:
        if not policy.base_url or not _is_loopback_url(policy.base_url):
            raise ValueError("Local RLM backend must use a localhost-compatible base URL.")
    elif policy.backend in EXTERNAL_BACKENDS:
        if not policy.allow_external_provider:
            raise ValueError(
                f"External RLM backend '{policy.backend}' requires explicit approval."
            )
    else:
        raise ValueError(f"Unknown RLM backend: {policy.backend}")


def collect_status(
    *,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    upstream_repo: Path = DEFAULT_RLM_REPO,
) -> RLMStatus:
    """Return whether the isolated RLM runtime is ready."""
    python_path = runtime_python(runtime_root)
    if not python_path.exists():
        return RLMStatus(
            runtime_python=str(python_path),
            runtime_exists=False,
            upstream_repo=str(upstream_repo),
            upstream_exists=upstream_repo.exists(),
            rlms_importable=False,
            optional_imports={},
            detail="Runtime venv is missing.",
        )

    probe = (
        "import importlib, importlib.metadata as m, json\n"
        "import rlm\n"
        "optional = {}\n"
        "for name in ['IPython', 'modal', 'e2b_code_interpreter', 'daytona', 'prime_sandboxes']:\n"
        "    try:\n"
        "        importlib.import_module(name)\n"
        "        optional[name] = True\n"
        "    except Exception:\n"
        "        optional[name] = False\n"
        "sys_path = getattr(rlm, '__file__', '')\n"
        "json.dump({'version': m.version('rlms'), 'file': sys_path, 'optional': optional}, __import__('sys').stdout)\n"
    )
    result = subprocess.run(
        [str(python_path), "-c", probe],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return RLMStatus(
        runtime_python=str(python_path),
        runtime_exists=True,
        upstream_repo=str(upstream_repo),
        upstream_exists=upstream_repo.exists(),
        rlms_importable=result.returncode == 0,
        optional_imports=_optional_imports_from_probe(result.stdout),
        detail=(result.stdout or result.stderr).strip(),
    )


def write_default_config(
    *,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    base_url: str = DEFAULT_BASE_URL,
) -> Path:
    """Write a secret-free default sidecar config under ignored agent-os."""
    config_path = agent_root / "RLM" / "sidecar_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "version": 1,
        "mode": "codex-sidecar",
        "default_backend": "vllm",
        "default_environment": "ipython",
        "default_base_url": base_url,
        "installed_optional_extras": ["ipython", "modal", "e2b", "daytona", "prime"],
        "external_providers_default": "disabled",
        "cloud_environments_default": "disabled",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def run_completion(
    *,
    prompt: str,
    model: str,
    policy: RLMPolicy,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    max_depth: int = 1,
    max_iterations: int = 3,
    timeout: int = 120,
    dry_run: bool = False,
) -> dict[str, object]:
    """Run or validate one bounded RLM completion through the isolated venv."""
    assert_safe_for_obsidian(prompt)
    validate_policy(policy)
    python_path = runtime_python(runtime_root)
    if not python_path.exists():
        raise ValueError(f"RLM runtime Python is missing: {python_path}")

    run_root = agent_root / "RLM_RUNS"
    run_root.mkdir(parents=True, exist_ok=True)
    log_dir = run_root / datetime.now().strftime("%Y%m%d-%H%M%S")

    payload = {
        "prompt": prompt,
        "model": model,
        "backend": policy.backend,
        "base_url": policy.base_url,
        "environment": policy.environment,
        "max_depth": max_depth,
        "max_iterations": max_iterations,
        "max_timeout": timeout,
        "log_dir": str(log_dir),
    }
    if dry_run:
        return {"dry_run": True, "payload": payload}

    result = subprocess.run(
        [str(python_path), "-c", _runner_code()],
        cwd=ROOT,
        check=False,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout + 15,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "RLM sidecar run failed.")
    return json.loads(result.stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show RLM sidecar status")
    status.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    status.add_argument("--upstream-repo", default=str(DEFAULT_RLM_REPO))

    init = subparsers.add_parser("init-config", help="write default sidecar config")
    init.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    init.add_argument("--base-url", default=DEFAULT_BASE_URL)

    run = subparsers.add_parser("run", help="run a bounded RLM completion")
    run.add_argument("--prompt", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--backend", default="vllm")
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.add_argument("--environment", default="ipython")
    run.add_argument("--max-depth", type=int, default=1)
    run.add_argument("--max-iterations", type=int, default=3)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    run.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    run.add_argument("--allow-external-provider", action="store_true")
    run.add_argument("--allow-cloud-environment", action="store_true")
    run.add_argument("--dry-run", action="store_true")

    visualizer = subparsers.add_parser(
        "visualizer-info", help="show local upstream visualizer commands"
    )
    visualizer.add_argument("--upstream-repo", default=str(DEFAULT_RLM_REPO))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            status = collect_status(
                runtime_root=Path(args.runtime_root),
                upstream_repo=Path(args.upstream_repo),
            )
            _write_json(asdict(status))
        elif args.command == "init-config":
            path = write_default_config(
                agent_root=Path(args.agent_root),
                base_url=args.base_url,
            )
            _write_json({"config": str(path)})
        elif args.command == "run":
            output = run_completion(
                prompt=args.prompt,
                model=args.model,
                policy=RLMPolicy(
                    backend=args.backend,
                    environment=args.environment,
                    base_url=args.base_url,
                    allow_external_provider=args.allow_external_provider,
                    allow_cloud_environment=args.allow_cloud_environment,
                ),
                runtime_root=Path(args.runtime_root),
                agent_root=Path(args.agent_root),
                max_depth=args.max_depth,
                max_iterations=args.max_iterations,
                timeout=args.timeout,
                dry_run=args.dry_run,
            )
            _write_json(output)
        elif args.command == "visualizer-info":
            root = Path(args.upstream_repo) / "visualizer"
            _write_json(
                {
                    "path": str(root),
                    "install": "npm.cmd install",
                    "run": "npm.cmd run dev",
                    "default_url": "http://localhost:3001",
                }
            )
    except (ValueError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return 0


def _is_loopback_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _optional_imports_from_probe(stdout: str) -> dict[str, bool]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    optional = data.get("optional")
    if not isinstance(optional, dict):
        return {}
    return {str(key): bool(value) for key, value in optional.items()}


def _write_json(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _runner_code() -> str:
    return r"""
import json
import sys
from rlm import RLM
from rlm.logger import RLMLogger

payload = json.loads(sys.stdin.read())
kwargs = {"model_name": payload["model"]}
if payload.get("base_url"):
    kwargs["base_url"] = payload["base_url"]
logger = RLMLogger(log_dir=payload["log_dir"])
client = RLM(
    backend=payload["backend"],
    backend_kwargs=kwargs,
    environment=payload["environment"],
    max_depth=payload["max_depth"],
    max_iterations=payload["max_iterations"],
    max_timeout=payload["max_timeout"],
    logger=logger,
    verbose=False,
)
result = client.completion(payload["prompt"])
json.dump(
    {
        "response": result.response,
        "execution_time": result.execution_time,
        "log_file": logger.log_file_path,
        "metadata": result.metadata,
    },
    sys.stdout,
)
"""


if __name__ == "__main__":
    raise SystemExit(main())
