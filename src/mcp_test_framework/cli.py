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
    try:
        with asyncio.Runner() as runner:
            tools = runner.run(_list_tools_async(cfg))
    except KeyboardInterrupt:
        # Enforce the docstring's exit-code-130 guarantee. Without this,
        # Click's default standalone_mode catches KeyboardInterrupt and
        # converts it to exit code 1 via Abort. Re-raising as
        # typer.Exit(code=130) makes the SIGINT contract explicit and
        # uniform across POSIX and Windows console-script wrappers.
        raise typer.Exit(code=130)
    if as_json:
        typer.echo(_format_tools_json(tools), nl=False)
    else:
        typer.echo(_format_tools_text(tools))


@app.command("config-init")
def config_init(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Write scaffold to this file instead of stdout. "
            "Refuses to overwrite without --force."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Permit overwrite of an existing --output file.",
    ),
) -> None:
    """Emit a starter YAML config scaffold for the connected MCP server (Phase 08 D-21).

    Discovers tools via the same isolation-aware seam used by `run` and
    `list-tools` (`McpTestClient.__aenter__` -- D-24), then emits a YAML
    document containing `version: 1` and a `tools:` block with one
    commented entry per discovered tool. The scaffold is a no-op
    passthrough by default -- uncomment and edit individual fields to
    opt a tool into skip / judges / args (Phase 08 D-22, CD-06).

    Output:
      - default: stdout
      - --output PATH: write to file (refuses to overwrite without --force)

    Exit codes (preserves CLI symmetry with `run` / `list-tools`):
      - 0: success
      - 2: --config path not found, refusing-to-overwrite, or discovery failure
      - 130: SIGINT during discovery
    """
    # Refuse-to-overwrite check happens BEFORE discovery so a stale --output
    # path doesn't cost the operator a subprocess spawn.
    if output is not None and output.exists() and not force:
        typer.echo(
            f"error: refusing to overwrite existing file: {output} (use --force)",
            err=True,
        )
        raise typer.Exit(code=2)

    cfg = _load_config(config)

    try:
        with asyncio.Runner() as runner:
            tools = runner.run(_list_tools_async(cfg))
    except KeyboardInterrupt:
        # Mirror `list-tools`: typer.Exit(code=130) so SIGINT is surfaced
        # uniformly across POSIX/Windows console-script wrappers.
        raise typer.Exit(code=130)
    except FileNotFoundError as exc:
        # Quick-task 260507-j6i: enrich the cryptic "MCP server command not on
        # PATH" with a hint pointing users at MCPTF_CONFIG_FILE / config.example.yaml.
        # Keep in sync with src/mcp_test_framework/fixtures.py:_preflight (lines
        # 117-123) and tests/conftest.py:_resolve_tool_names (lines 113-119) --
        # THIRD copy of the same string. CONTEXT.md <Shared Patterns> "MCP
        # discovery hint string" flags this as a three-copy hazard;
        # consolidating to a constant is out of scope for this plan.
        msg = (
            f"MCP discovery via {cfg.mcp_server.command!r} failed: "
            f"{exc.__class__.__name__}: {exc}"
        )
        if str(exc).startswith("MCP server command not on PATH:"):
            msg += (
                f"\n\nHint: {cfg.mcp_server.command!r} was not found on PATH. "
                "If you intended to use a different command, point "
                "MCPTF_CONFIG_FILE at a config.yaml that defines "
                "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
                "The repo ships `config.example.yaml` you can copy and edit."
            )
        typer.echo(msg, err=True)
        raise typer.Exit(code=2)

    scaffold = _format_tools_yaml_scaffold(tools)

    if output is None:
        typer.echo(scaffold, nl=False)
    else:
        # Path.write_text overwrites unconditionally -- the refuse-to-overwrite
        # gate above already enforced the --force contract.
        output.write_text(scaffold, encoding="utf-8")


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
    output composes with shell pipelines. No `default=` fallback: MCP
    tool schemas are JSON Schema documents and MUST be JSON-serializable
    by contract. If `json.dumps` raises `TypeError` here, that is the
    correct signal that the SDK or schema is malformed.
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
    return json.dumps(payload, indent=2) + "\n"


def _format_tools_yaml_scaffold(tools: list[Tool]) -> str:
    """Hand-format a YAML scaffold matching Phase 08 D-22 / CD-06.

    Returns a multi-line string ending with a single newline. Tools are sorted
    alphabetically by name (mirrors _format_tools_text / _format_tools_json
    convention -- D-list-4 from Phase 05).

    Each tool block is commented out by default so `mcp-test-framework
    config-init > config.yaml` produces a working passthrough config (no
    behavior change). The user uncomments + edits individual fields to opt
    a tool into skip / judges / args.

    The reserved `setup:` / `depends_on:` fields (TOOLCFG-03 / D-06) are
    intentionally OMITTED from the scaffold per CD-06 -- they are dormant
    in v1.1 and surfacing them risks users assuming they work.

    Rubric IDs in the commented `judges:` line are LOCKED per
    CONTEXT.md <specifics> + TOOLCFG-04: clarity, disambiguation, parameters.
    """
    sorted_tools = sorted(tools, key=lambda t: t.name)

    header = (
        "# mcp-test-framework v1.1 starter config -- generated by "
        "`mcp-test-framework config-init`.\n"
        "# Edit and copy to config.yaml; set MCPTF_CONFIG_FILE=./config.yaml.\n"
        "# See the README \"Per-tool configuration\" section for field semantics.\n"
        "\n"
        "# Phase 08 schema version. Only `1` is accepted by this release.\n"
        "version: 1\n"
        "\n"
        "# Per-tool config registry (TOOLCFG-01..07). Keys MUST match tool\n"
        "# names returned by `mcp-test-framework list-tools`. All entries\n"
        "# below are commented out by default -- this scaffold is a passthrough.\n"
        "# Uncomment and edit individual fields to opt a tool into skip /\n"
        "# judges / args.\n"
        "tools:\n"
    )

    if not sorted_tools:
        return header + "  {}\n"

    blocks: list[str] = []
    for tool in sorted_tools:
        block = (
            f"  # {tool.name}:\n"
            f"  #   skip: false\n"
            f"  #   skip_reason: \"\"\n"
            f"  #   call_arguments: {{}}\n"
            f"  #   judges: [clarity, disambiguation, parameters]\n"
        )
        blocks.append(block)

    return header + "\n".join(blocks) + "\n"


if __name__ == "__main__":  # pragma: no cover
    app()
