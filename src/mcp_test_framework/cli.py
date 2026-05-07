"""Typer CLI surface (`run` / `list-tools` / `version`).

Implements the CLI from docs/mcp_test_framework_mvp_spec.md §CLI:

    run [--config PATH] [-- pytest args]   -- D-cli-flags-1..3
    list-tools [--config PATH] [--json]    -- D-list-1..4 / D-teardown-1..3
    version                                -- CLI-03

Per Phase 5 CONTEXT.md decisions:
- `_load_config(path)` helper sets MCPTF_CONFIG_FILE env var if --config given,
  then instantiates Config() (Pydantic ValidationError propagates).
- `run` (Plan 02) forwards everything after `--` to pytest.main(["tests", *forwarded]).
  D-cli-flags-3: NO try/except wrap -- pytest's own SIGINT + Phase 04.1's
  AsyncExitStack-owned mcp_client fixture cover OPS-03 for the run path.
- `list-tools` (Plan 03) body uses asyncio.Runner + AsyncExitStack-owned
  McpTestClient (Phase 04.1 same-task lifecycle -- avoids the cancel-scope
  teardown bug; Pitfall 1 mitigation reused).
- `version` reads importlib.metadata.version("mvp-test-framework"), falls back
  to the package __version__ constant on PackageNotFoundError.

Distribution-name vs package-name discrepancy:
    pyproject.toml [project] name = "mvp-test-framework"   <-- metadata.version() arg
    importable package          = "mcp_test_framework"
    console-script name         = "mcp-test-framework"
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import textwrap
from contextlib import AsyncExitStack
from importlib import metadata
from pathlib import Path

import typer
from mcp.types import Tool

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient

app = typer.Typer(
    name="mcp-test-framework",
    no_args_is_help=True,
    add_completion=False,
    help="Pytest framework for testing MCP servers end-to-end.",
)


@app.callback()
def _main() -> None:
    """Force Typer multi-command mode (subcommands instead of single-callback).

    Without an explicit callback, Typer collapses an app with exactly one
    `@app.command()` into a single-command app -- `mcp-test-framework version`
    would then be parsed as an unexpected positional arg. This empty callback
    keeps the subcommand surface stable across Plan 05-01 (one command),
    Plan 05-02 (two commands), and Plan 05-03 (three commands).
    """
    return None


def _load_config(path: Path | None) -> Config:
    """Shared config loader for `run` and `list-tools` commands.

    If `path` is provided, sets MCPTF_CONFIG_FILE so Config()'s
    settings_customise_sources picks up the YAML overlay. Pydantic
    ValidationError propagates uncaught -- Pydantic's own message is
    the diagnostic (CONTEXT.md Discretion bullet 2).

    Note: on success, MCPTF_CONFIG_FILE is intentionally left set in
    os.environ so the `run` path's pytest.main() plugin chain (and
    fixtures) can observe the same overlay. On Config() failure the
    var is popped to avoid leaking a bad path into subsequent calls
    in the same process (e.g., test harnesses that invoke the CLI
    multiple times).
    """
    if path is not None:
        if not path.is_file():
            typer.echo(f"error: --config path not found: {path}", err=True)
            raise typer.Exit(code=2)
        os.environ["MCPTF_CONFIG_FILE"] = str(path)
        try:
            return Config()
        except Exception:
            os.environ.pop("MCPTF_CONFIG_FILE", None)
            raise
    return Config()


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def run(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    pytest_args: list[str] | None = typer.Argument(
        None,
        help="Args after `--` are forwarded to pytest.main([\"tests\", *args]).",
    ),
) -> None:
    """Run the test suite (CLI-01).

    Loads Config() at the CLI level so config errors surface as a clean
    diagnostic BEFORE pytest's plugin chain produces an opaque
    INTERNALERROR (D-discretion bullet 4). Then delegates entirely to
    pytest.main() -- D-cli-flags-3: NO try/except wrap. pytest's own
    SIGINT handling + Phase 04.1's AsyncExitStack-owned `mcp_client`
    fixture cover OPS-03 for this path.

    The `addopts = "-m 'not live_homelab and not live_ollama'"` contract
    from pyproject.toml stays in effect -- `run` MUST NOT pass an explicit
    `-m` flag (D-markers-3 / Phase 4 contract).

    `import pytest` is function-local: pytest is in `[dependency-groups] dev`
    only, not `[project.dependencies]`. Module-scope import would break
    `version` and `list-tools` for users installing the wheel without dev
    extras.
    """
    import pytest  # function-local: pytest is dev-only, not a runtime dep

    _load_config(config)  # raises typer.Exit(2) on bad path; ValidationError propagates
    forwarded = list(pytest_args or [])
    raise typer.Exit(code=pytest.main(["tests", *forwarded]))


@app.command("list-tools")
def list_tools(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit tools as a JSON array of full MCP tool records.",
    ),
) -> None:
    """List all tools exposed by the configured MCP server (CLI-02).

    Connects via stdio (no pytest, no Ollama). Default output is indented
    blocks: name on its own line, full wrapped description indented beneath
    (D-list-1, D-list-3). `--json` emits a JSON array of full MCP tool
    records (D-list-2). Output sorted alphabetically by name (D-list-4).

    Body uses asyncio.Runner + AsyncExitStack-owned McpTestClient
    (D-teardown-1). KeyboardInterrupt propagates through the runner,
    __aexit__ runs in the same task that did __aenter__,
    stdio_client._terminate_process_tree kills the subprocess, exit code
    130 with no message printed (D-teardown-3). This is the SAME pattern
    Phase 04.1 hardened for the test path -- reused at the CLI surface.
    """
    cfg = _load_config(config)
    with asyncio.Runner() as runner:
        tools = runner.run(_list_tools_async(cfg))
    if as_json:
        typer.echo(_format_tools_json(tools), nl=False)
    else:
        typer.echo(_format_tools_text(tools))


@app.command()
def version() -> None:
    """Print the package version (CLI-03)."""
    try:
        v = metadata.version("mvp-test-framework")  # distribution name, NOT importable package
    except metadata.PackageNotFoundError:
        from mcp_test_framework import __version__ as v
    typer.echo(v)


async def _list_tools_async(cfg: Config) -> list[Tool]:
    """Drive the MCP client lifecycle on a single task.

    AsyncExitStack is technically redundant with the single-context
    `async with McpTestClient(...)` form, but it is used anyway to:
    (1) future-proof against adding a second resource (e.g., a logger handle),
    (2) explicitly mirror the Phase 04.1 ownership lesson,
    (3) keep __aexit__ semantics identical regardless of how many resources land.
    """
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            McpTestClient(
                cfg.mcp_server.command,
                cfg.mcp_server.args,
                cfg.mcp_server.timeout_seconds,
            )
        )
        return await client.list_tools()


def _format_tools_text(tools: list[Tool]) -> str:
    """Indented-block text format: name on its own line, full wrapped description beneath.

    Width comes from shutil.get_terminal_size with an 80-col fallback
    (D-list-3 / Discretion). Stdlib textwrap.fill handles wrapping --
    no `rich` dependency.
    """
    width = max(40, shutil.get_terminal_size((80, 20)).columns)
    sorted_tools = sorted(tools, key=lambda t: t.name)
    if not sorted_tools:
        return "(no tools registered on the server)"
    blocks: list[str] = []
    for t in sorted_tools:
        desc = t.description or "(no description)"
        wrapped = textwrap.fill(
            desc,
            width=max(20, width - 2),
            initial_indent="  ",
            subsequent_indent="  ",
        )
        blocks.append(f"{t.name}\n{wrapped}")
    return "\n\n".join(blocks)


def _format_tools_json(tools: list[Tool]) -> str:
    """Full MCP tool record per tool: {name, description, inputSchema, outputSchema}.

    Sorted alphabetically by name (D-list-4). Trailing newline so the
    output composes with shell pipelines. `default=str` is a defensive
    fallback for any non-serializable annotation values inside schemas.
    """
    sorted_tools = sorted(tools, key=lambda t: t.name)
    payload = [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema,
            "outputSchema": t.outputSchema,
        }
        for t in sorted_tools
    ]
    return json.dumps(payload, indent=2, default=str) + "\n"


if __name__ == "__main__":  # pragma: no cover
    app()
