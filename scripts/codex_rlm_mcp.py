"""Minimal local MCP server for Codex RLM sidecar tools.

This script intentionally avoids the MCP SDK so it can stay dependency-free.
It implements the small JSON-RPC surface needed by Codex-style MCP clients:
initialize, tools/list and tools/call.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codex_rlm_sidecar import (
    DEFAULT_AGENT_ROOT,
    DEFAULT_BASE_URL,
    DEFAULT_RLM_REPO,
    DEFAULT_RUNTIME_ROOT,
    RLMPolicy,
    collect_status,
    run_completion,
    write_default_config,
)
from scripts.local_agent_os import create_work_item, resolve_obsidian_vault
from scripts.local_agent_rlm import (
    append_step,
    close_trajectory,
    parse_evidence,
    start_trajectory,
)


SERVER_NAME = "parserriba-codex-rlm"
SERVER_VERSION = "1.0.0"
DEFAULT_CONFIG_PATH = DEFAULT_AGENT_ROOT / "MCP" / "codex_rlm_mcp_config.json"


def tool_definitions() -> list[dict[str, Any]]:
    """Return MCP tool declarations for the local-only RLM sidecar."""
    return [
        {
            "name": "rlm_status",
            "description": "Check the isolated local RLM sidecar runtime.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "runtime_root": {"type": "string"},
                    "upstream_repo": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_init_config",
            "description": "Write a secret-free ignored sidecar config.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_root": {"type": "string"},
                    "base_url": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_dry_run",
            "description": "Validate a bounded local RLM request without model calls.",
            "inputSchema": {
                "type": "object",
                "required": ["prompt", "model"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string"},
                    "backend": {"type": "string", "default": "vllm"},
                    "base_url": {"type": "string", "default": DEFAULT_BASE_URL},
                    "environment": {"type": "string", "default": "ipython"},
                    "max_depth": {"type": "integer", "default": 1},
                    "max_iterations": {"type": "integer", "default": 3},
                    "timeout": {"type": "integer", "default": 120},
                    "runtime_root": {"type": "string"},
                    "agent_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_visualizer_info",
            "description": "Return local upstream visualizer path and commands.",
            "inputSchema": {
                "type": "object",
                "properties": {"upstream_repo": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "agent_os_note",
            "description": "Create a local Agent OS ISA note, optionally mirrored to Obsidian.",
            "inputSchema": {
                "type": "object",
                "required": ["title", "objective"],
                "properties": {
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "current_state": {"type": "string"},
                    "ideal_state": {"type": "string"},
                    "agent_root": {"type": "string"},
                    "obsidian_vault": {"type": "string"},
                    "mirror_obsidian": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_trajectory_start",
            "description": "Start a local structured RLM trajectory.",
            "inputSchema": {
                "type": "object",
                "required": ["title", "objective"],
                "properties": {
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "mode": {"type": "string", "default": "manual"},
                    "max_depth": {"type": "integer", "default": 3},
                    "max_iterations": {"type": "integer", "default": 3},
                    "agent_root": {"type": "string"},
                    "obsidian_vault": {"type": "string"},
                    "mirror_obsidian": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_trajectory_step",
            "description": "Append a context-question-result-decision step.",
            "inputSchema": {
                "type": "object",
                "required": ["trajectory", "context", "question", "result", "next_decision"],
                "properties": {
                    "trajectory": {"type": "string"},
                    "context": {"type": "string"},
                    "question": {"type": "string"},
                    "result": {"type": "string"},
                    "next_decision": {"type": "string"},
                    "depth": {"type": "integer", "default": 1},
                    "iteration": {"type": "integer", "default": 1},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "agent_root": {"type": "string"},
                    "obsidian_vault": {"type": "string"},
                    "mirror_obsidian": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "rlm_trajectory_close",
            "description": "Close a local structured RLM trajectory.",
            "inputSchema": {
                "type": "object",
                "required": ["trajectory", "summary", "next_action"],
                "properties": {
                    "trajectory": {"type": "string"},
                    "summary": {"type": "string"},
                    "decision": {"type": "array", "items": {"type": "string"}},
                    "verification": {"type": "array", "items": {"type": "string"}},
                    "risk": {"type": "array", "items": {"type": "string"}},
                    "next_action": {"type": "string"},
                    "agent_root": {"type": "string"},
                    "obsidian_vault": {"type": "string"},
                    "mirror_obsidian": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        },
    ]


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC MCP request."""
    if "id" not in request:
        return None
    method = str(request.get("method") or "")
    request_id = request["id"]
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            }
        elif method == "tools/list":
            result = {"tools": tool_definitions()}
        elif method == "tools/call":
            params = _object(request.get("params"))
            result = call_tool(str(params.get("name") or ""), _object(params.get("arguments")))
        else:
            return _error_response(request_id, -32601, f"Unknown method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except (TypeError, ValueError, OSError) as exc:
        return _error_response(request_id, -32000, str(exc))


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one local RLM sidecar tool and return MCP content."""
    if name == "rlm_status":
        payload = asdict(
            collect_status(
                runtime_root=Path(str(arguments.get("runtime_root") or DEFAULT_RUNTIME_ROOT)),
                upstream_repo=Path(str(arguments.get("upstream_repo") or DEFAULT_RLM_REPO)),
            )
        )
    elif name == "rlm_init_config":
        path = write_default_config(
            agent_root=Path(str(arguments.get("agent_root") or DEFAULT_AGENT_ROOT)),
            base_url=str(arguments.get("base_url") or DEFAULT_BASE_URL),
        )
        payload = {"config": str(path)}
    elif name == "rlm_dry_run":
        payload = run_completion(
            prompt=_required_string(arguments, "prompt"),
            model=_required_string(arguments, "model"),
            policy=RLMPolicy(
                backend=str(arguments.get("backend") or "vllm"),
                environment=str(arguments.get("environment") or "ipython"),
                base_url=str(arguments.get("base_url") or DEFAULT_BASE_URL),
            ),
            runtime_root=Path(str(arguments.get("runtime_root") or DEFAULT_RUNTIME_ROOT)),
            agent_root=Path(str(arguments.get("agent_root") or DEFAULT_AGENT_ROOT)),
            max_depth=int(arguments.get("max_depth") or 1),
            max_iterations=int(arguments.get("max_iterations") or 3),
            timeout=int(arguments.get("timeout") or 120),
            dry_run=True,
        )
    elif name == "rlm_visualizer_info":
        root = Path(str(arguments.get("upstream_repo") or DEFAULT_RLM_REPO)) / "visualizer"
        payload = {
            "path": str(root),
            "install": "npm.cmd install",
            "run": "npm.cmd run dev",
            "default_url": "http://localhost:3001",
        }
    elif name == "agent_os_note":
        result = create_work_item(
            title=_required_string(arguments, "title"),
            objective=_required_string(arguments, "objective"),
            current_state=str(arguments.get("current_state") or "Not captured yet."),
            ideal_state=str(arguments.get("ideal_state") or "Not captured yet."),
            agent_root=_agent_root(arguments),
            obsidian_vault=_obsidian_vault(arguments),
            mirror_obsidian=bool(arguments.get("mirror_obsidian") or False),
        )
        payload = {
            "item_id": result.item_id,
            "local_path": str(result.local_path),
            "obsidian_path": str(result.obsidian_path) if result.obsidian_path else None,
        }
    elif name == "rlm_trajectory_start":
        paths = start_trajectory(
            title=_required_string(arguments, "title"),
            objective=_required_string(arguments, "objective"),
            mode=str(arguments.get("mode") or "manual"),
            max_depth=int(arguments.get("max_depth") or 3),
            max_iterations=int(arguments.get("max_iterations") or 3),
            agent_root=_agent_root(arguments),
            obsidian_vault=_obsidian_vault(arguments),
            mirror_obsidian=bool(arguments.get("mirror_obsidian") or False),
        )
        payload = _paths_payload(paths)
    elif name == "rlm_trajectory_step":
        paths = append_step(
            trajectory_id=_required_string(arguments, "trajectory"),
            context=_required_string(arguments, "context"),
            question=_required_string(arguments, "question"),
            result=_required_string(arguments, "result"),
            next_decision=_required_string(arguments, "next_decision"),
            depth=int(arguments.get("depth") or 1),
            iteration=int(arguments.get("iteration") or 1),
            evidence_refs=parse_evidence(_string_list(arguments.get("evidence"))),
            agent_root=_agent_root(arguments),
            obsidian_vault=_obsidian_vault(arguments),
            mirror_obsidian=bool(arguments.get("mirror_obsidian") or False),
        )
        payload = _paths_payload(paths)
    elif name == "rlm_trajectory_close":
        paths = close_trajectory(
            trajectory_id=_required_string(arguments, "trajectory"),
            summary=_required_string(arguments, "summary"),
            decisions=_string_list(arguments.get("decision")),
            verification=_string_list(arguments.get("verification")),
            risks=_string_list(arguments.get("risk")),
            next_action=_required_string(arguments, "next_action"),
            agent_root=_agent_root(arguments),
            obsidian_vault=_obsidian_vault(arguments),
            mirror_obsidian=bool(arguments.get("mirror_obsidian") or False),
        )
        payload = _paths_payload(paths)
    else:
        raise ValueError(f"Unknown tool: {name}")
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}


def run_stdio() -> int:
    """Run a line-delimited stdio JSON-RPC loop."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                response = _error_response(None, -32600, "Request must be a JSON object.")
            else:
                response = handle_request(request)
        except json.JSONDecodeError as exc:
            response = _error_response(None, -32700, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="run the MCP JSON-RPC stdio server",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="print tool definitions and exit",
    )
    parser.add_argument(
        "--write-client-config",
        action="store_true",
        help="write a local MCP client config snippet under ignored agent-os",
    )
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_tools:
        sys.stdout.write(json.dumps({"tools": tool_definitions()}, ensure_ascii=False, indent=2) + "\n")
        return 0
    if args.write_client_config:
        path = write_client_config(Path(args.config_path))
        sys.stdout.write(json.dumps({"config": str(path)}, ensure_ascii=False, indent=2) + "\n")
        return 0
    if args.stdio:
        return run_stdio()
    sys.stderr.write("Use --stdio for MCP mode or --list-tools for inspection.\n")
    return 2


def _object(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("Expected object parameters.")
    return value


def _required_string(arguments: dict[str, Any], name: str) -> str:
    value = str(arguments.get(name) or "").strip()
    if not value:
        raise ValueError(f"Missing required argument: {name}")
    return value


def write_client_config(path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Write a local MCP client config snippet for this server."""
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "mcpServers": {
            SERVER_NAME: {
                "command": str(ROOT / ".venv" / "Scripts" / "python.exe"),
                "args": [str(ROOT / "scripts" / "codex_rlm_mcp.py"), "--stdio"],
                "cwd": str(ROOT),
                "env": {
                    "PYTHONIOENCODING": "utf-8",
                },
            }
        }
    }
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _agent_root(arguments: dict[str, Any]) -> Path:
    return Path(str(arguments.get("agent_root") or DEFAULT_AGENT_ROOT))


def _obsidian_vault(arguments: dict[str, Any]) -> Path | None:
    value = arguments.get("obsidian_vault")
    return resolve_obsidian_vault(str(value)) if value else resolve_obsidian_vault(None)


def _paths_payload(paths: object) -> dict[str, str | None]:
    return {
        "trajectory_id": str(getattr(paths, "trajectory_id")),
        "json_path": str(getattr(paths, "json_path")),
        "markdown_path": str(getattr(paths, "markdown_path")),
        "obsidian_path": str(getattr(paths, "obsidian_path")) if getattr(paths, "obsidian_path") else None,
    }


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Expected a list of strings.")
    return [str(item) for item in value]


def _error_response(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
