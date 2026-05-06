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

import os
from importlib import metadata
from pathlib import Path

import typer

from mcp_test_framework.config import Config

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
    """
    if path is not None:
        if not path.is_file():
            typer.echo(f"error: --config path not found: {path}", err=True)
            raise typer.Exit(code=2)
        os.environ["MCPTF_CONFIG_FILE"] = str(path)
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
    pytest_args: list[str] = typer.Argument(
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


@app.command()
def version() -> None:
    """Print the package version (CLI-03)."""
    try:
        v = metadata.version("mvp-test-framework")  # distribution name, NOT importable package
    except metadata.PackageNotFoundError:
        from mcp_test_framework import __version__ as v
    typer.echo(v)


if __name__ == "__main__":  # pragma: no cover
    app()
