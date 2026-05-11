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
import re
import shutil
import textwrap
import typing
from contextlib import AsyncExitStack
from importlib import metadata
from pathlib import Path

import typer
from mcp.types import Tool
from pydantic import ValidationError

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


def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Render an operator-grade error and exit (citation: docs/ERROR-STYLE.md).

    This function never returns; it raises typer.Exit internally. Callers
    MUST NOT prefix calls with `raise`.

    Format (per docs/ERROR-STYLE.md):
        <one-line summary>
        <blank>
        <detail line 1>
        <detail line 2>
        ...
        <blank>
        next: <action verb> <command-or-instruction>

    Operator terms only -- no spec IDs, no file:line refs, no internal jargon.
    """
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)


def _emit_operator_error_for_validation(
    exc: ValidationError, *, source: str
) -> typing.NoReturn:
    """Map pydantic.ValidationError -> operator-tone error per docs/ERROR-STYLE.md.

    Mapping rules:
    - version mismatch (config version N not supported by this build, expected 1)
        -> "config file uses an older format" framing (forward-compat with SAFE-06
           reference message in docs/ERROR-STYLE.md, but Phase 12 still accepts v1
           and rejects v2+; the message names the actual mismatch).
    - missing required field -> point at config.example.yaml
    - other validation errors -> generic detail block with the field path

    Function never returns; every branch calls _emit_operator_error which raises.
    """
    errors = exc.errors()
    primary = errors[0] if errors else {}
    loc = ".".join(str(p) for p in primary.get("loc", ()))
    err_type = primary.get("type", "")
    msg = primary.get("msg", "")

    def _scrub_pydantic_jargon(raw: str) -> str:
        # Strip pydantic v2's "Value error, " / "Assertion failed, " prefixes
        # and the v1 "value_error" type-string. ERROR-STYLE.md rule 1 forbids
        # leaking pydantic-internal jargon into operator-facing output.
        cleaned = raw
        for prefix in ("Value error, ", "Assertion failed, "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        return cleaned

    if loc == "version" and "not supported by this build" in msg:
        # Phase 13 D-08: LOCKED SAFE-06 message body, copied verbatim from
        # docs/ERROR-STYLE.md:57-73. Source-text regression at
        # tests/unit/test_error_style.py::test_error_style_safe_06_body_matches_cli_wiring
        # pins the substrings; do not reword.
        _emit_operator_error(
            summary=f"config file uses an older format: {source}",
            detail=[
                "this release of mcp-test-framework expects schema version 2 (opt-in",
                "tool selection); your config is version 1 (opt-out). the difference",
                "matters: in v1 a tool with no entry runs by default, in v2 it skips",
                "by default.",
                "",
                "your existing per-tool settings (`call_arguments`, `judges`,",
                "`skip_reason`) port forward unchanged -- only the implicit default",
                "flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows",
                "the steps.",
            ],
            next_step=(
                "run `mcp-test-framework config-init -o config.yaml.new` to see "
                "the v2 layout, port your tool entries across, then replace your "
                "existing config"
            ),
        )
    if err_type in ("missing", "value_error.missing"):
        _emit_operator_error(
            summary=f"config file is missing a required field: {loc}",
            detail=[
                f"the field `{loc}` is required but was not found in {source}.",
                "",
                "see config.example.yaml for the expected shape, or regenerate "
                "a starter file with config-init.",
            ],
            next_step=(
                "copy the relevant block from config.example.yaml or run "
                "`mcp-test-framework config-init -o config.yaml`"
            ),
        )
    # Generic fallback -- still operator-tone, no pydantic-internal terms.
    field_summary = ", ".join(
        ".".join(str(p) for p in e.get("loc", ())) for e in errors
    ) or "(unknown field)"
    detail_lines = [f"the following config field(s) failed validation: {field_summary}."]
    for e in errors[:3]:
        detail_lines.append(
            f"  - {'.'.join(str(p) for p in e.get('loc', ()))}: "
            f"{_scrub_pydantic_jargon(e.get('msg', ''))}"
        )
    _emit_operator_error(
        summary=f"config file has invalid values: {source}",
        detail=detail_lines,
        next_step=(
            "fix the field(s) above, or run "
            "`mcp-test-framework config-init -o config.yaml` to regenerate"
        ),
    )


def _load_config(path: Path | None, *, allow_missing: bool = False) -> Config | None:
    """Resolve the YAML config path and load Config().

    Precedence (Phase 13 D-01):
        --config PATH > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.

    The resolved path is passed to Config() as a `yaml_file` kwarg
    (Phase 13 D-03); settings_customise_sources reads it from
    init_settings.init_kwargs -- not from os.environ. ValidationError
    is mapped through _emit_operator_error_for_validation per
    docs/ERROR-STYLE.md (PERSONA-03).

    Args:
        path: Value of --config (None when the operator did not pass it).
        allow_missing: When True (used by `config-init` and `list-tools`),
            the "nothing found" branch returns None instead of raising
            SAFE-03. This is the bootstrap path: SAFE-03's recovery
            command (`config-init -o config.yaml`) must itself run from
            an unconfigured directory. An explicit-but-broken --config
            or MCPTF_CONFIG_FILE STILL raises (typo, not bootstrap).
            Defaults to False; only `run` keeps the SAFE-03 surface.

    Returns:
        A Config instance, or None when allow_missing=True and no config
        source was reachable. The caller is responsible for constructing
        a default Config() in the None case.
    """
    resolved: Path | None = None
    source_label: str = ""  # "--config" / "MCPTF_CONFIG_FILE" / "./config.yaml"

    # Branch 1: --config wins.
    if path is not None:
        if not path.is_file():
            _emit_operator_error(
                summary=f"config file not found: {path}",
                detail=[
                    "the path passed to --config does not exist or is not a file.",
                ],
                next_step=(
                    "check the path or run "
                    "`mcp-test-framework config-init -o config.yaml` "
                    "to generate a starter config"
                ),
            )
        resolved = path
        source_label = str(path)
    else:
        # Branch 2: MCPTF_CONFIG_FILE.
        env_path_str = os.environ.get("MCPTF_CONFIG_FILE")
        if env_path_str:
            env_path = Path(env_path_str)
            if not env_path.is_file():
                _emit_operator_error(
                    summary=f"config file not found via MCPTF_CONFIG_FILE: {env_path}",
                    detail=[
                        "the path in MCPTF_CONFIG_FILE does not exist or is not a file.",
                    ],
                    next_step=(
                        "check the path or unset MCPTF_CONFIG_FILE and run "
                        "`mcp-test-framework config-init -o config.yaml` "
                        "to generate a starter config"
                    ),
                )
            resolved = env_path
            source_label = str(env_path)
        else:
            # Branch 3: ./config.yaml autodiscovery.
            cwd_config = Path.cwd() / "config.yaml"
            if cwd_config.is_file():
                resolved = cwd_config
                source_label = str(cwd_config)

    # Branch 4: nothing found.
    if resolved is None:
        if allow_missing:
            # Bootstrap path: config-init / list-tools may run from an
            # unconfigured directory. Caller constructs a default Config().
            return None
        _emit_operator_error(
            summary="no config file found: ./config.yaml",
            detail=[
                "the framework refuses to run without a config file because it would",
                "otherwise call every tool the server advertises -- including any",
                "destructive ones. you must explicitly opt in to which tools run.",
            ],
            next_step=(
                "run `mcp-test-framework config-init -o config.yaml` to generate "
                "a starter config, then edit it to enable the tools you want to test"
            ),
        )

    # Load with the resolved path as an explicit kwarg.
    # Phase 13 review CR-01/CR-02: also export MCPTF_CONFIG_FILE so the
    # in-process pytest session spawned by `run()` -- which constructs a
    # bare `Config()` inside fixtures + conftest + reporter -- picks up
    # the same resolved YAML path via the env-var fallback in
    # `Config.settings_customise_sources`. SAFE-05 is preserved: the env
    # var is a PATH POINTER, not a scalar-value source.
    os.environ["MCPTF_CONFIG_FILE"] = str(resolved)
    try:
        return Config(yaml_file=str(resolved))
    except ValidationError as exc:
        _emit_operator_error_for_validation(exc, source=source_label)


def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
) -> list[str]:
    """Translate `--junit-xml=PATH` (Phase 09 D-01b public spelling) into pytest's
    `--junitxml=PATH` (no-dash internal spelling) and assemble the argv passed to
    ``pytest.main(...)``.

    D-01a precedence: the explicit flag is inserted BEFORE the passthrough
    forwarded args so a later passthrough ``--junitxml=...`` (after ``--``)
    wins under pytest's last-occurrence argparse rule. The helper does NOT
    de-duplicate or validate paths -- pytest's own argument handling is the
    single source of truth.

    L-03 invariant: this helper builds the argv list only; the call site in
    ``run`` keeps the bare ``raise typer.Exit(code=pytest.main(...))`` shape
    with NO try/except wrap (Phase 5 D-cli-flags-3).
    """
    forwarded = list(pytest_args or [])
    args: list[str] = ["tests"]
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    return args


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
    junit_xml: Path | None = typer.Option(
        None,
        "--junit-xml",
        help=(
            "Write JUnit XML to PATH. Translates internally to pytest's "
            "`--junitxml=PATH` (note pytest's no-dash spelling). If a "
            "passthrough `--junitxml=...` is also supplied after `--`, the "
            "passthrough wins via pytest's last-occurrence argparse rule "
            "(D-01a)."
        ),
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

    Phase 09 OUTPUT-01: `--junit-xml=PATH` translates to pytest's `--junitxml=PATH`
    via `_build_pytest_args` (D-01b spelling difference; D-01a passthrough-wins
    precedence). The helper is extracted (CD-06 option 3) so the translation is
    unit-testable without spawning pytest.

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
    raise typer.Exit(code=pytest.main(_build_pytest_args(junit_xml, pytest_args)))


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
    full: bool = typer.Option(
        False,
        "--full",
        help="Include full description and per-parameter descriptions (ignored under --json).",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Substring filter on tool name (case-insensitive).",
    ),
) -> None:
    """List tools exposed by the configured MCP server (CLI-02 / PERSONA-02).

    Default render (per tool):
        <name>(<param>: <type>, *, <kw>: <type> = <default>)
          <one-line truncated description>

    --full adds the wrapped full description + per-parameter descriptions
    (still human-readable, not raw JSON; use --json for machine output).
    --name PATTERN narrows to tools whose name contains PATTERN
    (case-insensitive substring match). --name composes with --full
    and --json. --json output is unchanged from v1.1 except for the
    --name filter applied before serialization. Passing --full alongside
    --json is a no-op (JSON output is already complete).

    Body uses asyncio.Runner + AsyncExitStack-owned McpTestClient
    (D-teardown-1). KeyboardInterrupt propagates through the runner,
    __aexit__ runs in the same task that did __aenter__,
    stdio_client._terminate_process_tree kills the subprocess, exit code
    130 with no message printed (D-teardown-3).

    From a directory with no config (no --config, no MCPTF_CONFIG_FILE, no
    ./config.yaml), `list-tools` uses framework defaults rather than failing
    loud. SAFE-03 fail-loud applies to `run` only -- `list-tools` is
    deliberately bootstrap-friendly so an operator can probe a server
    before opting tools in.
    """
    cfg = _load_config(config, allow_missing=True)
    if cfg is None:
        cfg = Config()
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
    except FileNotFoundError as exc:
        if str(exc).startswith("MCP server command not on PATH:"):
            _emit_operator_error(
                summary=f"MCP server command not found: {cfg.mcp_server.command!r}",
                detail=[
                    f"the framework tried to launch the server with "
                    f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}`",
                    "and the command is not on PATH.",
                ],
                next_step=(
                    "update `mcp_server.command` / `mcp_server.args` in your "
                    "config.yaml so the launch command resolves on PATH"
                ),
            )
        _emit_operator_error(
            summary="MCP server failed to start",
            detail=[f"the launch attempt raised: {exc.__class__.__name__}: {exc}"],
            next_step="verify the launch command runs cleanly in your shell",
        )

    if as_json:
        # JSON path: --name filter applied; --full is ignored (D-07 orthogonality).
        # Output is byte-identical to v1.1 except for the optional name filter.
        if name is not None:
            needle = name.lower()
            filtered = [t for t in tools if needle in t.name.lower()]
        else:
            filtered = tools
        typer.echo(_format_tools_json(filtered), nl=False)
    else:
        typer.echo(_format_tools_text(tools, full=full, name_filter=name))


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
    command: str | None = typer.Option(
        None,
        "--command",
        help=(
            "Override mcp_server.command for this invocation. "
            "Useful when your server is launched via uvx or pipx and the "
            "default command is not on PATH "
            "(e.g. `--command uvx --arg your-mcp-package`)."
        ),
    ),
    arg: list[str] | None = typer.Option(
        None,
        "--arg",
        help=(
            "Append an argument to mcp_server.args. Repeat for each arg "
            "(e.g. `--arg first --arg second`). Combine with --command "
            "to bootstrap config-init without a pre-existing config.yaml."
        ),
    ),
) -> None:
    """Emit a starter YAML config scaffold for the connected MCP server.

    Discovers tools via the same isolation-aware seam used by `run` and
    `list-tools` (`McpTestClient.__aenter__`), then emits a YAML
    document containing `version: 2` and a `tools:` block with one
    commented entry per discovered tool. The scaffold is a no-op
    passthrough by default -- uncomment and edit individual fields to
    opt a tool into skip / judges / args.

    Output:
      - default: stdout
      - --output PATH: write to file (refuses to overwrite without --force)

    Override flags (bootstrap a fresh checkout without a pre-existing config.yaml):
      - --command CMD: override mcp_server.command for this invocation only
      - --arg ARG: append to mcp_server.args; repeat for each arg

    Exit codes (preserves CLI symmetry with `run` / `list-tools`):
      - 0: success
      - 2: --config path not found, refusing-to-overwrite, or discovery failure
      - 130: SIGINT during discovery
    """
    # Refuse-to-overwrite check happens BEFORE discovery so a stale --output
    # path doesn't cost the operator a subprocess spawn.
    if output is not None and output.exists() and not force:
        _emit_operator_error(
            summary=f"refusing to overwrite existing file: {output}",
            detail=[
                "the framework does not overwrite an existing scaffold without --force.",
            ],
            next_step="add `--force` to overwrite, or pick a different `--output` path",
        )

    cfg = _load_config(config, allow_missing=True)
    if cfg is None:
        cfg = Config()

    # Apply --command / --arg overrides via Pydantic v2 model_copy on the
    # frozen Config / McpServerConfig instances. Re-instantiating Config(...)
    # would re-trigger settings_customise_sources and lose the operator's
    # intent; model_copy(update=...) returns a new frozen instance with only
    # the named fields replaced.
    if command is not None or arg is not None:
        overrides: dict[str, object] = {}
        if command is not None:
            overrides["command"] = command
        if arg is not None:
            overrides["args"] = list(arg)
        cfg = cfg.model_copy(
            update={"mcp_server": cfg.mcp_server.model_copy(update=overrides)}
        )

    try:
        with asyncio.Runner() as runner:
            tools = runner.run(_list_tools_async(cfg))
    except KeyboardInterrupt:
        # Mirror `list-tools`: typer.Exit(code=130) so SIGINT is surfaced
        # uniformly across POSIX/Windows console-script wrappers.
        raise typer.Exit(code=130)
    except FileNotFoundError as exc:
        # Fallback scaffold: if --output was given, write a runnable shell
        # so the operator's recovery path is "edit and re-run", not
        # "hand-write a config from scratch". stdout mode skips this --
        # the operator can't edit stdout.
        if output is not None:
            fallback_body = _format_tools_yaml_scaffold([])
            # The mcp_server block in the scaffold below shows the framework
            # DEFAULT values, NOT whatever --command/--arg the operator may
            # have just passed -- propagating overrides into the scaffold is
            # a deferred follow-up. The header acknowledges this so an
            # operator who used `--command pipx --arg my-server` and got the
            # fallback isn't confused why they see uvx / your-mcp-server-package
            # in the file below.
            header = (
                "# mcp-test-framework starter config -- TOOL DISCOVERY FAILED.\n"
                "# The framework could not launch your MCP server, so the\n"
                "# `tools:` block below is empty. Fill in `mcp_server.command`\n"
                "# (and any required `mcp_server.args`) so the launch command\n"
                "# resolves on PATH, then re-run `mcp-test-framework config-init`\n"
                "# to populate the tool list.\n"
                "#\n"
                "# Note: the `mcp_server` block below shows the framework\n"
                "# default values. If you intended `--command X --arg Y`,\n"
                "# edit those lines to substitute your values before re-running.\n"
                "\n"
            )
            output.write_text(header + fallback_body, encoding="utf-8")
        if str(exc).startswith("MCP server command not on PATH:"):
            _emit_operator_error(
                summary=f"MCP server command not found: {cfg.mcp_server.command!r}",
                detail=[
                    f"the framework tried to launch the server with "
                    f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}`",
                    "and the command is not on PATH.",
                    "",
                    "if your server is installed via `uvx` or `pipx`, set "
                    "`mcp_server.command` and `mcp_server.args` in your config.yaml "
                    "(e.g. `command: uvx, args: [your-server-package]`).",
                ],
                next_step=(
                    "verify the launch command works in your shell, then update "
                    "`mcp_server.command` / `mcp_server.args` in your config.yaml"
                ),
            )
        _emit_operator_error(
            summary="MCP server failed to start",
            detail=[
                f"the launch attempt raised: {exc.__class__.__name__}: {exc}",
                "",
                "check that the command in your config.yaml is runnable and any "
                "required dependencies are installed.",
            ],
            next_step="verify the launch command runs cleanly in your shell",
        )

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


def _format_param_signature(tool: Tool) -> str:
    """Render `(name: type, name: type, *, kw: type = default)` for a Tool.

    Required params (per inputSchema.required) come first in the order they
    appear in the `required` list; optional params follow `*,` as kwargs
    sorted alphabetically with their defaults inlined. JSON Schema scalar
    types are mapped to short Python labels; unknown / union types fall
    back to "Any".

    Returns "()" for tools with no inputSchema or no properties.
    """
    schema = tool.inputSchema or {}
    props: dict = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
    required: list[str] = list(schema.get("required") or []) if isinstance(schema, dict) else []
    if not props:
        return "()"

    type_map = {
        "string": "str",
        "integer": "int",
        "boolean": "bool",
        "number": "float",
        "array": "list",
        "object": "dict",
    }

    def _pytype(jtype: object) -> str:
        if isinstance(jtype, str):
            return type_map.get(jtype, "Any")
        return "Any"

    req_parts: list[str] = []
    for name in required:
        if name in props:
            req_parts.append(f"{name}: {_pytype(props[name].get('type'))}")

    kw_parts: list[str] = []
    for name in sorted(p for p in props if p not in required):
        prop = props[name] or {}
        ptype = _pytype(prop.get("type"))
        if "default" in prop:
            kw_parts.append(f"{name}: {ptype} = {prop['default']!r}")
        else:
            kw_parts.append(f"{name}: {ptype} = ...")

    if not kw_parts:
        return f"({', '.join(req_parts)})"
    if not req_parts:
        return f"(*, {', '.join(kw_parts)})"
    return f"({', '.join(req_parts)}, *, {', '.join(kw_parts)})"


def _format_tools_text(
    tools: list[Tool],
    *,
    full: bool = False,
    name_filter: str | None = None,
) -> str:
    """Human-readable render: name + signature + description per tool.

    Default (D-05): name(signature) + 1-line truncated description.
    --full (D-06): name(signature) + wrapped full description +
                   per-parameter descriptions from inputSchema.
    --name PATTERN (D-08): substring filter applied post-sort, pre-render.

    Sort: alphabetical by name (D-09 / preserves D-list-4 contract).
    Width: shutil.get_terminal_size with 80-col fallback.
    """
    width = max(40, shutil.get_terminal_size((80, 20)).columns)
    sorted_tools = sorted(tools, key=lambda t: t.name)

    if name_filter:
        needle = name_filter.lower()
        sorted_tools = [t for t in sorted_tools if needle in t.name.lower()]

    if not sorted_tools:
        if name_filter:
            return (
                f"(no tools matched filter {name_filter!r}; "
                f"server has {len(tools)} tools total)"
            )
        return "(no tools registered on the server)"

    blocks: list[str] = []
    for t in sorted_tools:
        sig = _format_param_signature(t)
        desc = t.description or "(no description)"
        if full:
            wrapped = textwrap.fill(
                desc,
                width=max(20, width - 2),
                initial_indent="  ",
                subsequent_indent="  ",
            )
            block_lines: list[str] = [f"{t.name}{sig}", wrapped]
            schema = t.inputSchema or {}
            props = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
            if props:
                block_lines.append("")
                block_lines.append("  parameters:")
                for name in sorted(props):
                    pdesc = (props[name] or {}).get("description") or "(no description)"
                    pdesc_wrapped = textwrap.fill(
                        pdesc,
                        width=max(20, width - 8),
                        initial_indent="      ",
                        subsequent_indent="      ",
                    )
                    block_lines.append(f"    - {name}:")
                    block_lines.append(pdesc_wrapped)
            blocks.append("\n".join(block_lines))
        else:
            short = textwrap.shorten(desc, width=max(20, width - 4), placeholder="...")
            blocks.append(f"{t.name}{sig}\n  {short}")

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


_YAML_BARE_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _yaml_key(name: str) -> str:
    """Return name as a YAML mapping key, JSON-quoted only if necessary.

    MCP tool names per the spec match `^[A-Za-z_][A-Za-z0-9_]*$`. Names that
    match are emitted as bare identifiers (visually clean). Anything else is
    JSON-quoted via json.dumps (always a valid YAML 1.2 scalar).
    """
    if _YAML_BARE_KEY_RE.fullmatch(name):
        return name
    return json.dumps(name)


def _format_tools_yaml_scaffold(tools: list[Tool]) -> str:
    """Hand-format a complete self-contained YAML scaffold (CLEAN-05).

    Output shape (locked in docs/ERROR-STYLE.md / CLEAN-05 acceptance):
    - Top-level `ollama:`, `mcp_server:`, `judge_timeout_seconds:`, `version:`,
      `tools:` blocks all populated.
    - `version: 2` literal (this release's accepted version).
    - Every discovered tool emitted as `<name>: { skip: true, skip_reason: ... }`
      with the name passed through `_yaml_key` for defensive YAML quoting.
    - No `target:` block (the field is leaving in a future schema bump).
    - All string scalars JSON-quoted via `json.dumps` (avoids YAML scalar
      ambiguity for values containing colons, hashes, or quotes).

    Tools sorted alphabetically (preserves the v1.1 D-list-4 contract).
    """
    sorted_tools = sorted(tools, key=lambda t: t.name)
    skip_reason = "review and remove skip to enable"

    header = (
        "# mcp-test-framework starter config -- generated by `config-init`.\n"
        "# Edit this file in place, or copy to a project-local path and pass --config PATH.\n"
        "\n"
        "# Ollama judge backend.\n"
        "ollama:\n"
        f"  base_url: {json.dumps('http://127.0.0.1:11434')}\n"
        f"  model: {json.dumps('qwen3.6:latest')}\n"
        "  timeout_seconds: 120\n"
        "\n"
        "# MCP server under test.\n"
        "# The launch command MUST be runnable from your shell.\n"
        "mcp_server:\n"
        f"  command: {json.dumps('uvx')}\n"
        f"  args: [{json.dumps('your-mcp-server-package')}]\n"
        "  timeout_seconds: 30\n"
        "\n"
        "# Outer budget cap on each judge HTTP call.\n"
        "judge_timeout_seconds: 120\n"
        "\n"
        "# Schema version. This release accepts version 2.\n"
        "version: 2\n"
        "\n"
        "# Per-tool registry. Every tool the connected server advertises is\n"
        "# listed below as `skip: true` -- the framework will not call any\n"
        "# tool until you review and remove `skip` from the ones you want\n"
        "# to test.\n"
        "#\n"
        "# Read each entry below, decide whether it is safe to call against\n"
        "# your environment, then either:\n"
        "#   - delete the `skip` and `skip_reason` lines to enable the tool, OR\n"
        "#   - leave the entry as-is to keep the tool out of the test surface.\n"
        "tools:\n"
    )

    if not sorted_tools:
        return header + "  {}\n"

    blocks: list[str] = []
    for tool in sorted_tools:
        block = (
            f"  {_yaml_key(tool.name)}:\n"
            f"    skip: true\n"
            f"    skip_reason: {json.dumps(skip_reason)}\n"
        )
        blocks.append(block)

    return header + "\n".join(blocks) + "\n"


if __name__ == "__main__":  # pragma: no cover
    app()
