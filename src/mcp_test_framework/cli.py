"""Typer CLI surface (`run` / `list-tools` / `version` / `gen-test-classes` / `config-init`).

Implements the CLI surface documented in docs/mcp_test_framework_mvp_spec.md §CLI:

    run [--config PATH] [-- pytest args]
    list-tools [--config PATH] [--json]
    version
    gen-test-classes [--config PATH]
    config-init [--output PATH] [--force] [--command CMD] [--arg ARG]...

Behavior contracts encoded in this module:

- `_load_config(path)` resolves the YAML path
  (--config > MCPTF_CONFIG_FILE > ./config.yaml) and passes it as a
  `yaml_file` kwarg to Config(). It also writes the resolved path back
  to MCPTF_CONFIG_FILE so the in-process pytest session's bare Config()
  picks up the same source. ValidationError is mapped to typer.Exit via
  `_emit_operator_error_for_validation` -- it does NOT propagate.
- `run` invokes pytest as a child subprocess via the runner module
  (`mcp_test_framework._runner`). `_load_config` is the pre-flight gate
  on BOTH default and --raw paths. pytest's own SIGINT handling plus
  the AsyncExitStack-owned `mcp_client` fixture cover SIGINT for the
  run path; the wrapper does not catch KeyboardInterrupt.
- `list-tools` uses `asyncio.Runner` + AsyncExitStack-owned
  `McpTestClient` so `__aexit__` runs in the same task that did
  `__aenter__` -- this avoids the cancel-scope teardown bug.
- `version` reads `importlib.metadata.version("mcp-contracts")` and
  falls back to the package `__version__` constant on PackageNotFoundError.

Distribution-name vs package-name discrepancy (Phase 26 D-01/D-04/D-06):
    pyproject.toml [project] name = "mcp-contracts"        <-- metadata.version() arg
    importable package            = "mcp_test_framework"   <-- D-04: unchanged
    console-script name (primary) = "mcp-contracts"        <-- D-05
    console-script name (legacy)  = "mcp-test-framework"   <-- D-06: v1.4 deprecation shim, removed v1.5
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
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
from mcp_test_framework.models import TestCodeConfig

# Bootstrap stub: the paths used by `list-tools` / `config-init` under
# ``allow_missing=True`` fall back to ``Config(test_code=_BOOTSTRAP_TEST_CODE_STUB)``
# so the framework can emit a starter scaffold from an unconfigured
# directory. The stub value matches the convention emitted by
# ``_format_tools_yaml_scaffold`` so an operator who saves the scaffold
# and re-runs gets a self-consistent path. This stub is NEVER reachable
# from operator-supplied YAML: ``test_code.generated_root`` remains a required
# field for any loaded config.
_BOOTSTRAP_TEST_CODE_STUB = TestCodeConfig(generated_root=Path("tests/test_code/_generated"))

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
    keeps the subcommand surface stable as commands are added or removed.
    """
    return None


# Re-exported from _runner.py; cli.py keeps the public symbol so existing
# test imports `from mcp_test_framework.cli import _emit_operator_error`
# continue working. The helper lives in _runner.py to avoid a
# cli.py <-> _runner.py circular import.
from mcp_test_framework._runner import _emit_operator_error  # noqa: E402


def _emit_operator_error_for_validation(
    exc: ValidationError, *, source: str
) -> typing.NoReturn:
    """Map pydantic.ValidationError -> operator-tone error per docs/ERROR-STYLE.md.

    Mapping rules:
    - version mismatch (config version N not supported by this build) ->
        "config file uses an older format" framing. The current build
        accepts version 2 and rejects v1; the message names the actual
        mismatch and points at the migration walkthrough.
    - missing required field -> point at config.example.yaml
    - other validation errors -> generic detail block with the field path

    Function never returns; every branch calls _emit_operator_error which raises.
    """
    errors = exc.errors()
    # With `test_code` required on Config, a v1 YAML missing the `test_code` block
    # produces TWO Pydantic errors -- the v1 version-mismatch AND the
    # missing-test_code field. Order of `errors[0]` is implementation-defined
    # and would silently shift the rendered v1-migration message to the
    # missing-required-field path, breaking the locked migration error
    # text. Scan ALL errors and prefer the version-mismatch first so the
    # v1 -> v2 migration message stays load-bearing for operators upgrading.
    version_err = next(
        (
            e
            for e in errors
            if ".".join(str(p) for p in e.get("loc", ())) == "version"
            and "not supported by this build" in e.get("msg", "")
        ),
        None,
    )
    primary = version_err or (errors[0] if errors else {})
    loc = ".".join(str(p) for p in primary.get("loc", ()))
    err_type = primary.get("type", "")
    msg = primary.get("msg", "")

    def _scrub_pydantic_jargon(raw: str) -> str:
        # Strip pydantic v2's "Value error, " / "Assertion failed, " prefixes.
        # docs/ERROR-STYLE.md rule 1 forbids leaking pydantic-internal jargon
        # into operator-facing output.
        cleaned = raw
        for prefix in ("Value error, ", "Assertion failed, "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        return cleaned

    if loc == "version" and "not supported by this build" in msg:
        # Locked v1 -> v2 migration message -- the canonical text lives in
        # docs/ERROR-STYLE.md and is pinned by a source-text regression test
        # under tests/unit/test_error_style.py. Do not reword: keep this
        # body in sync with the ERROR-STYLE.md spec if you edit it.
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
    # Generic fallback -- operator-tone, no pydantic-internal terms.
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

    Precedence:
        --config PATH > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.

    The resolved path is passed to Config() as a `yaml_file` kwarg;
    settings_customise_sources reads it from init_settings.init_kwargs --
    not from os.environ. ValidationError is mapped through
    `_emit_operator_error_for_validation` per docs/ERROR-STYLE.md.

    Args:
        path: Value of --config (None when the operator did not pass it).
        allow_missing: When True (used by `config-init` and `list-tools`),
            the "nothing found" branch returns None instead of raising
            the no-config-found operator error. This is the bootstrap
            path: the recovery command (`config-init -o config.yaml`)
            must itself run from an unconfigured directory. An
            explicit-but-broken --config or MCPTF_CONFIG_FILE STILL
            raises (typo, not bootstrap). Defaults to False; only `run`
            keeps the strict no-config surface.

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
            # Bootstrap path: config-init and list-tools may run from an
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
    # Also export MCPTF_CONFIG_FILE so the in-process pytest session
    # spawned by `run()` -- which constructs a bare `Config()` inside
    # fixtures, conftest, and the reporter -- picks up the same resolved
    # YAML path via the env-var fallback in
    # `Config.settings_customise_sources`. The env var is a PATH POINTER,
    # not a scalar-value source -- the source-precedence contract in
    # docs/ERROR-STYLE.md is preserved.
    os.environ["MCPTF_CONFIG_FILE"] = str(resolved)
    try:
        return Config(yaml_file=str(resolved))
    except ValidationError as exc:
        _emit_operator_error_for_validation(exc, source=source_label)


# Re-exported from _runner.py; cli.py keeps the public symbol so existing
# test imports `from mcp_test_framework.cli import _build_pytest_args`
# continue working. The helper builds the argv passed to the subprocess
# pytest run.
from mcp_test_framework._runner import _build_pytest_args  # noqa: E402


def _discover_tools_for_run(cfg: Config) -> list[str]:
    """One-shot MCP handshake to learn what tools the server advertises.

    The `run` wrapper executes OUTSIDE pytest, so the in-pytest
    `_DISCOVERED_TOOL_NAMES` cache (hosted on `mcp_test_framework._runner`)
    is unreachable from this process. Instead we re-discover here before
    launching the subprocess.

    Mirrors the AsyncExitStack pattern from `list_tools` -- the same-task
    lifecycle avoids the cancel-scope teardown bug.

    On failure: surface via `_emit_operator_error` so config errors stay
    operator-tone and exit 2. Matches list-tools failure-mode parity.
    """
    async def _do_discover() -> list[str]:
        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(
                McpTestClient(
                    cfg.mcp_server.command,
                    cfg.mcp_server.args,
                    cfg.mcp_server.timeout_seconds,
                )
            )
            tools = await client.list_tools()
            return [t.name for t in tools]

    try:
        with asyncio.Runner() as runner:
            return runner.run(_do_discover())
    except FileNotFoundError as exc:
        _emit_operator_error(
            summary="MCP server command not on PATH",
            detail=[
                f"could not start the MCP server: {exc}",
                "",
                "the runner needs to discover the server's tool list before",
                "executing the test plan. fix the `mcp_server.command` value",
                "in your config, or skip discovery via `--raw` (which forwards",
                "all flags to pytest unchanged).",
            ],
            next_step=(
                "check your config's mcp_server.command, or run with --raw "
                "to bypass"
            ),
        )
    except KeyboardInterrupt:
        # Mirror list_tools: explicit typer.Exit(130) so SIGINT is uniform
        # across POSIX/Windows console-script wrappers.
        raise typer.Exit(code=130)
    except Exception as exc:  # noqa: BLE001 -- defensive catchall
        _emit_operator_error(
            summary="MCP server discovery failed",
            detail=[
                f"could not list tools from the configured MCP server: {exc}",
            ],
            next_step="check your config or run with --raw to bypass the wrapper",
        )


def _warn_sdet_flag(value: bool) -> bool:  # noqa: sdet-rename-shim
    """Eager Typer/Click callback that emits the --sdet -> --test-code  # noqa: sdet-rename-shim
    deprecation warning during option parsing, BEFORE --help short-circuits
    the command body. Fires once per process via Python's default filter.
    """  # noqa: sdet-rename-shim
    if value:
        import warnings
        warnings.warn(  # noqa: sdet-rename-shim
            "--sdet is deprecated since v1.4 and will be removed in v1.5 — "  # noqa: sdet-rename-shim
            "use --test-code instead.",  # noqa: sdet-rename-shim
            DeprecationWarning,  # noqa: sdet-rename-shim
            stacklevel=2,  # noqa: sdet-rename-shim
        )  # noqa: sdet-rename-shim
    return value  # noqa: sdet-rename-shim


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
        help="Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery).",
    ),
    junit_xml: Path | None = typer.Option(
        None,
        "--junit-xml",
        help=(
            "Write JUnit XML to PATH. Translates to pytest's --junitxml=PATH. "
            "In default mode the wrapper consumes its own internal tempfile "
            "for the domain UI; this flag's path is populated independently "
            "via a post-subprocess copy."
        ),
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help=(
            "Bypass the domain UI wrapper and stream pytest's native output. "
            "All flags forward verbatim to pytest. Default scope is "
            "tests/contract; pass --with-framework to also include "
            "tests/framework. The config pre-flight gate still runs."
        ),
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help=(
            "Append raw pytest output and failure tracebacks after the "
            "domain UI. Useful for debugging; does not reshape the default "
            "output."
        ),
    ),
    quiet: bool = typer.Option(
        False,
        "-q",
        "--quiet",
        help=(
            "Print only the summary line (no header, no per-tool rows). "
            "Independent of pytest's -q; pytest still runs at default "
            "verbosity internally so JUnit XML stays complete."
        ),
    ),
    with_framework: bool = typer.Option(
        False,
        "--with-framework",
        help=(
            "Also collect tests/framework/ (the framework's own self-tests) "
            "in addition to the operator-default tests/contract/. Use this for "
            "maintainer runs and CI jobs that need the full suite. The default "
            "(without this flag) collects only the SUT-contract surface."
        ),
    ),
    test_code: bool = typer.Option(
        False,
        "--test-code",
        help=(
            "Swap the operator-surface scope from tests/contract/ to "
            "tests/test_code/. Runs operator-authored test-code scenarios "
            "against the active MCP server. Composes with --with-framework "
            "(adds tests/framework/), --raw (bypass domain UI), --debug "
            "(appendix), -q (summary only), and --explain (per-scenario "
            "skip reasons). Default (without this flag) collects only "
            "tests/contract/."
        ),
    ),
    sdet_legacy: bool = typer.Option(  # noqa: sdet-rename-shim
        False,  # noqa: sdet-rename-shim
        "--sdet",  # noqa: sdet-rename-shim
        hidden=True,  # noqa: sdet-rename-shim
        help="Deprecated alias for --test-code; removed in v1.5.",  # noqa: sdet-rename-shim
        callback=_warn_sdet_flag,  # noqa: sdet-rename-shim
        is_eager=True,  # noqa: sdet-rename-shim
    ),
    explain: bool = typer.Option(
        False,
        "--explain",
        help=(
            "Expand the pre-run digest's 'Skipping (N)' hint into one line "
            "per skipped tool with its skip reason, sorted alphabetically. "
            "Renders inline before the pytest subprocess starts. "
            "Ignored under --raw (no domain UI) and under -q / --quiet "
            "(summary-only output)."
        ),
    ),
    pytest_args: list[str] | None = typer.Argument(
        None,
        help="Args after `--` are forwarded to pytest.",
    ),
) -> None:
    """Run the test suite wrapped around a subprocess pytest.

    pytest runs as a child subprocess via the runner module
    (`mcp_test_framework._runner`); the in-process pytest entry point
    is not used by the wrapper. The config pre-flight gate runs on
    BOTH the default and --raw paths -- the no-config-found error
    cannot be bypassed via --raw.

    Default mode: wrapper-side MCP discovery + subprocess pytest +
    internal tempfile JUnit XML capture + XML parse + domain UI render.

    Raw mode (--raw): subprocess only, no tempfile, no capture, no domain
    UI, no discovery. Operator-supplied --junit-xml=PATH still flows
    through pytest via the runner's `_build_pytest_args`.

    Exit-code mapping:
      - pytest 0 -> exit 0
      - pytest 1 -> exit 1 (test failures)
      - pytest 2 -> exit 2 (collection / usage error)
      - pytest 5 -> exit 0 with "no tests collected" warning on stderr
      - SIGINT propagates naturally to exit 130 (KeyboardInterrupt not caught)

    The marker contract from pyproject.toml
    (`addopts = "-m 'not live_homelab and not live_ollama'"`) stays in
    effect inside the subprocess -- `run` MUST NOT pass an explicit `-m`
    flag.
    """
    if sdet_legacy:  # noqa: sdet-rename-shim
        # Deprecation warning fires from _warn_sdet_flag eager callback during  # noqa: sdet-rename-shim
        # option parsing (so it surfaces even on `--sdet --help`); body only  # noqa: sdet-rename-shim
        # coerces the legacy flag to the new behavior.
        test_code = True  # legacy operators get the same behavior  # noqa: sdet-rename-shim

    # Reconfigure sys.stdout to utf-8 with errors='replace' BEFORE any
    # rendering or any _load_config error path. On Windows the default
    # console code page is cp1252, which cannot encode the renderer's
    # U+2717 (✗) / U+2714 (✓) / U+2013 (–) / U+2014 (—) glyphs --
    # without this reconfigure, _render_per_tool_rows raises
    # UnicodeEncodeError mid-render and the operator never sees the
    # `Result:` summary line.
    #
    # Guarded with hasattr() so test environments that wrap sys.stdout
    # without implementing reconfigure() (e.g. pytest's capsys wrapper)
    # don't crash on the missing method. errors='replace' is the
    # deliberate trade-off: on truly hostile streams (no utf-8 capability
    # AND no reconfigure support) the operator still sees the row with
    # `?` in place of glyphs rather than a crash -- graceful degradation
    # over hard failure.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            # Some streams advertise reconfigure but reject the kwargs (e.g.,
            # already-detached buffer). Swallow -- the renderer's print()
            # calls will then either succeed (utf-8 console) or hit the same
            # crash we were trying to prevent (cp1252 console), at which
            # point the operator gets the same traceback they got pre-fix.
            # Best-effort.
            pass

    from mcp_test_framework import _runner
    import xml.etree.ElementTree as ET

    cfg = _load_config(config)  # raises typer.Exit(2) on any unrecoverable error.
    # _load_config(path, allow_missing=False) returns a non-None Config on
    # success or raises typer.Exit -- safe to treat cfg as Config below.

    if raw:
        # Raw mode: no tempfile, no capture, no render, no discovery.
        # Operator-supplied junit_xml (if any) still flows through
        # `_build_pytest_args` inside the runner. --raw bypasses the
        # domain UI entirely; -q and --debug do not apply.
        rc, _tmp, _stdout, _stderr = _runner.run_pytest_subprocess(
            junit_xml=junit_xml,
            pytest_args=pytest_args,
            raw=True,
            with_framework=with_framework,
            sdet=test_code,  # noqa: sdet-rename-shim
        )
        mapped, warning = _runner._map_exit_code(rc)
        if warning is not None:
            typer.echo(warning, err=True)
        raise typer.Exit(code=mapped)

    # Default mode: discover + parse + render. Discovery runs BEFORE the
    # subprocess so the header's Skipping count includes unlisted tools
    # (which would not appear in the JUnit XML at all).
    discovered_tools = _discover_tools_for_run(cfg)

    # Build RenderContext BEFORE the subprocess so the pre-run digest
    # can render. The pre-run digest computes its "Test plan" line from
    # the running tool set × the cases-per-tool constant; the post-run
    # code below rebuilds ctx with parsed.total_cases for the summary
    # line's count source.
    server_cmd = f"{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}".strip()
    # Judges: derive from the union of every configured tool's `judges`
    # list, de-duplicated and sorted. ToolConfig.judges has a three-way
    # contract (see models.py): None default => run ALL rubrics; []
    # => explicit opt-out; subset => literal. The helper honors this; a
    # prior loop using `or []` silently collapsed None to [] and produced
    # an empty union.
    judges = _runner._compose_judges_from_tool_configs(cfg.tools)

    pre_run_ctx = _runner.RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered_tools,
        tools_config=cfg.tools,
        judges=judges,
        total_planned_cases=0,  # post-parse ctx below carries parsed.total_cases
    )

    # Pre-run digest + --explain expansion BOTH gate on `not quiet`.
    # -q wins over --explain. `with_framework=` flows into the digest so
    # the "+ framework self-tests" continuation line emits inline (no
    # awkward blank gap). `explain=` suppresses the
    # "(use --explain to list)" hint when the list is rendered inline
    # right below.
    if not quiet:
        if test_code:
            # Scenario-aware digest under --test-code. Fresh test-code-only
            # RenderContext -- only server_cmd is consumed by the
            # scenario digest; contract-scope discovered_tools /
            # tools_config / judges fields have no meaning under test-code
            # scope (pytest_generate_tests parametrize does NOT run
            # under --test-code because pytest only discovers tests/test_code, not
            # tests/contract).
            sdet_ctx = _runner.RenderContext(server_cmd=pre_run_ctx.server_cmd)
            scenarios, skipped_scenarios = _runner._collect_test_code_scenarios(sdet_ctx)
            _runner._render_scenario_pre_run_digest(
                sdet_ctx,
                scenarios,
                skipped_scenarios,
                with_framework=with_framework,
                explain=explain,
            )
        else:
            _runner._render_pre_run_digest(
                pre_run_ctx,
                with_framework=with_framework,
                explain=explain,
            )
            if explain:
                _runner._render_skipped_tools_explain(pre_run_ctx)

    rc, tmp_xml, captured_stdout, captured_stderr = _runner.run_pytest_subprocess(
        junit_xml=junit_xml,
        pytest_args=pytest_args,
        raw=False,
        with_framework=with_framework,
        sdet=test_code,  # noqa: sdet-rename-shim
    )
    try:
        # If the subprocess crashed before writing the tempfile, surface a
        # domain-shaped error pointing at --raw for raw pytest output.
        # `_dispatch_default_mode_or_error` returns silently when the
        # tempfile is present, and calls `_emit_operator_error`
        # (typer.Exit) otherwise.
        _runner._dispatch_default_mode_or_error(tmp_xml, rc, captured_stderr)

        # JUnit XML parse error -> exit 2 via operator-tone message.
        try:
            parsed = _runner.parse_junit_xml(tmp_xml)
        except ET.ParseError as exc:
            _emit_operator_error(
                summary="JUnit XML parse failed",
                detail=[
                    f"could not parse the test runner's results file: {exc}",
                    "this usually means pytest crashed mid-run.",
                ],
                next_step=(
                    "re-run with `--raw` to see pytest's native output, or "
                    "check the captured stderr above"
                ),
            )

        # Rebuild ctx with the real total_planned_cases for the post-run
        # summary. discovered_tools / tools_config / judges / server_cmd
        # are unchanged from pre_run_ctx.
        ctx = _runner.RenderContext(
            server_cmd=server_cmd,
            discovered_tools=discovered_tools,
            tools_config=cfg.tools,
            judges=judges,
            total_planned_cases=parsed.total_cases,
        )
        # Verbosity ladder:
        #   -q (quiet) swaps render_domain_ui -> render_summary_only.
        #   --debug appends raw pytest output AFTER whichever rung above
        #     ran.
        # The two flags are orthogonal: `-q --debug` means
        # "summary line, then appendix". Invariant: each rung adds info;
        # none re-shapes the layer below.
        if quiet:
            _runner.render_summary_only(parsed, ctx)
        else:
            _runner.render_domain_ui(parsed, ctx)

        if debug:
            # --debug appends AFTER whatever the lower rung rendered. The
            # default UI shape is unchanged; --debug only adds info.
            # `xml_path` is passed so the appendix can scan for
            # ToolCallError-attached `mcptf_error_*` user_properties and
            # emit a `--- ToolCallError dump ---` block BEFORE raw pytest
            # output. When no such properties are present, the appendix
            # is byte-identical to the no-ToolCallError baseline.
            _runner.render_debug_appendix(
                captured_stdout, captured_stderr, parsed,
                xml_path=tmp_xml,
            )

        mapped, warning = _runner._map_exit_code(rc)
        if warning is not None:
            typer.echo(warning, err=True)
        raise typer.Exit(code=mapped)
    finally:
        if tmp_xml is not None and tmp_xml.exists():
            try:
                tmp_xml.unlink()
            except OSError:
                pass  # tempfile cleanup is best-effort.


@app.command("list-tools")
def list_tools(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery).",
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
    """List tools exposed by the configured MCP server.

    Default render (per tool):
        <name>(<param>: <type>, *, <kw>: <type> = <default>)
          <one-line truncated description>

    --full adds the wrapped full description + per-parameter descriptions
    (still human-readable, not raw JSON; use --json for machine output).
    --name PATTERN narrows to tools whose name contains PATTERN
    (case-insensitive substring match). --name composes with --full and
    --json. --json output is the full MCP tool record set, filtered by
    --name when supplied. Passing --full alongside --json is a no-op
    (JSON output is already complete).

    Body uses `asyncio.Runner` + AsyncExitStack-owned `McpTestClient`:
    KeyboardInterrupt propagates through the runner, `__aexit__` runs in
    the same task that did `__aenter__`, the stdio transport kills the
    subprocess on teardown, and the wrapper exits with code 130 (no
    message printed).

    From a directory with no config (no --config, no MCPTF_CONFIG_FILE,
    no ./config.yaml), `list-tools` uses framework defaults rather than
    failing loud. The fail-loud no-config error applies to `run` only --
    `list-tools` is deliberately bootstrap-friendly so an operator can
    probe a server before opting tools in.
    """
    cfg = _load_config(config, allow_missing=True)
    if cfg is None:
        cfg = Config(test_code=_BOOTSTRAP_TEST_CODE_STUB)
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
        # JSON path: --name filter applied; --full is ignored (the two
        # flags are orthogonal -- JSON output is already complete).
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
        help="Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery).",
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
    entry per discovered tool (each marked `skip: true` by default --
    review each entry and remove `skip` to opt a tool into the test
    surface).

    Output:
      - default: stdout
      - --output PATH: write to file (refuses to overwrite without --force)

    Override flags (bootstrap a fresh checkout without a pre-existing
    config.yaml):
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
        cfg = Config(test_code=_BOOTSTRAP_TEST_CODE_STUB)

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
        # Fallback scaffold: if --output was given, write a runnable
        # shell so the operator's recovery path is "edit and re-run",
        # not "hand-write a config from scratch". stdout mode skips this
        # -- the operator can't edit stdout.
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
    """Print the package version."""
    try:
        v = metadata.version("mcp-contracts")  # Phase 26 D-01: distribution name (NOT importable package)
    except metadata.PackageNotFoundError:
        from mcp_test_framework import __version__ as v
    typer.echo(v)


@app.command("gen-test-classes")
def gen_test_classes(
    config: Path | None = typer.Option(
        None,
        "--config",
        help=(
            "Path to a YAML config (overrides MCPTF_CONFIG_FILE and "
            "./config.yaml autodiscovery)."
        ),
    ),
) -> None:
    """Generate typed Pydantic Params/Response classes for every tool.

    Introspects the configured MCP server via list_tools and writes
    `<test_code.generated_root>/<server_slug>/<tool>.py` for every tool the
    server advertises, where `test_code.generated_root` is the required path
    declared in your config.yaml. Wipe-and-write: rerunning replaces
    the directory wholesale. Honors the standard config-source
    precedence: --config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.

    Exit codes:
      0   success
      2   config error, server-start error, empty serverInfo.name,
          invalid tool schema
      130 SIGINT during MCP handshake / list_tools
    """
    cfg = _load_config(config)  # strict; fail-loud on absent config
    assert cfg is not None, "_load_config(strict) must return Config or raise"
    try:
        with asyncio.Runner() as runner:
            server_info, tools = runner.run(_run_codegen_handshake(cfg))
    except KeyboardInterrupt:
        raise typer.Exit(code=130)
    except FileNotFoundError as exc:
        # Mirror cli.list_tools FileNotFoundError branch.
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

    server_name = (getattr(server_info, "name", "") or "").strip()
    if not server_name:
        # Loud-fail with operator-tone error: gen-test-classes needs a
        # non-empty server name to derive the output directory.
        _emit_operator_error(
            summary="gen-test-classes: server identification failed",
            detail=[
                f"the configured MCP server (command "
                f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}`) "
                f"reports an empty serverInfo.name.",
                "gen-test-classes needs a non-empty name to derive the "
                "<test_code.generated_root>/<slug>/ output directory.",
            ],
            next_step=(
                "ask the server author to set a name in their server's "
                "ServerInfo(name=..., version=...) initialization; this "
                "cannot be set framework-side."
            ),
        )

    # Local imports keep cli.py module-load cost minimal (gen-test-classes is
    # a rarely-run command compared to `run` / `list-tools`).
    from mcp_test_framework.test_code import _codegen
    from mcp_test_framework.test_code._slugs import server_slug

    # `out_root` is config-driven; the framework never writes generated
    # Python code inside its own `src/` tree. Relative paths are
    # resolved against CWD (mirrors the MCPTF_CONFIG_FILE convention).
    out_root = cfg.test_code.generated_root
    if not out_root.is_absolute():
        out_root = Path.cwd() / out_root
    server_version = getattr(server_info, "version", "") or ""
    try:
        counts = _codegen.generate(
            server_name=server_name,
            server_version=server_version,
            tools=tools,
            out_root=out_root,
        )
    except _codegen.SchemaValidityError as exc:
        _emit_operator_error(
            summary="gen-test-classes: invalid tool schema",
            detail=[str(exc)],
            next_step=(
                "report the offending tool to the server author; "
                "gen-test-classes refuses to translate non-JSON-Schema input."
            ),
        )

    slug = server_slug(server_name)
    typer.echo(f"gen-test-classes: wrote test-code classes for {server_name}\n")
    typer.echo(f"  server:    {server_name} v{server_version}")
    typer.echo(f"  slug:      {slug}")
    typer.echo(f"  target:    {out_root / slug}/")
    typer.echo(f"  tools:     {counts['tools']} generated")
    typer.echo(
        f"  degraded:  {counts['degraded_fields']} fields "
        f"(grep \"codegen: degraded\" for details)"
    )


@app.command("gen-sdet-classes", hidden=True)  # noqa: sdet-rename-shim
def _gen_sdet_classes_shim(  # noqa: sdet-rename-shim
    config: Path | None = typer.Option(  # noqa: sdet-rename-shim
        None,  # noqa: sdet-rename-shim
        "--config",  # noqa: sdet-rename-shim
        help=(  # noqa: sdet-rename-shim
            "Path to a YAML config (overrides MCPTF_CONFIG_FILE and "  # noqa: sdet-rename-shim
            "./config.yaml autodiscovery)."  # noqa: sdet-rename-shim
        ),  # noqa: sdet-rename-shim
    ),  # noqa: sdet-rename-shim
) -> None:  # noqa: sdet-rename-shim
    """Deprecated alias for `gen-test-classes` -- removed in v1.5."""  # noqa: sdet-rename-shim
    import warnings  # noqa: sdet-rename-shim
    warnings.warn(  # noqa: sdet-rename-shim
        "gen-sdet-classes is deprecated since v1.4 and will be removed in v1.5 — "  # noqa: sdet-rename-shim
        "use gen-test-classes instead.",  # noqa: sdet-rename-shim
        DeprecationWarning,  # noqa: sdet-rename-shim
        stacklevel=2,  # noqa: sdet-rename-shim
    )  # noqa: sdet-rename-shim
    gen_test_classes(config=config)  # noqa: sdet-rename-shim


# Serializes concurrent _run_codegen_handshake calls in the same
# process. The class-level monkey-patch of ClientSession.initialize is
# process-global, so two concurrent handshakes would corrupt each other's
# `holder` capture and race the `finally` restoration. asyncio.Lock is
# safe to construct at module load in Python 3.10+ (no event-loop
# attachment until first acquire).
_codegen_handshake_lock = asyncio.Lock()


async def _run_codegen_handshake(cfg: Config) -> tuple[object, list[Tool]]:
    """Open one-shot McpTestClient; return (serverInfo, tools) for gen-test-classes.

    ``mcp_client.py`` is intentionally not modified by this helper. To
    read serverInfo without touching that file we patch
    ``ClientSession.initialize`` at the class level for the duration of
    ``McpTestClient.__aenter__``: the patched method delegates to the
    real one, then stores the result in a holder dict.
    ``McpTestClient.__aenter__`` calls ``await session.initialize()``
    internally; after entry returns, we read the captured
    InitializeResult and restore the original method.

    Rationale for the class-level monkey-patch over reading
    ``session._initialize_result`` directly:
      - mcp 1.27.0's ClientSession does NOT store the InitializeResult
        as a private attribute (verified via inspect.getsource). Only
        ``_server_capabilities`` is cached; ``serverInfo`` is only
        available via the return value of ``initialize()``.
      - Re-invoking ``session.initialize()`` after McpTestClient has
        already initialized would re-send the protocol handshake, which
        is not spec-compliant.
      - The class-level patch is scoped to a single ``async with`` block
        and is reverted in the ``finally``; it does not leak across
        calls.

    If a future mcp release exposes a public ``server_info`` accessor on
    ClientSession, this helper should switch to it (delete the patch).

    Concurrency: the class-level patch is process-global -- concurrent
    calls in the same process would corrupt each other's ``holder``
    capture and race the ``finally`` restoration. The
    ``_codegen_handshake_lock`` module-level lock serializes the patched
    window so at most one handshake holds the patch at a time.
    Single-CLI-invocation callers are unaffected; future in-process /
    parallel callers get linear queueing instead of silent corruption.
    """
    from mcp import ClientSession

    async with _codegen_handshake_lock:
        holder: dict[str, object] = {}
        original_initialize = ClientSession.initialize

        async def _capturing_initialize(self):  # type: ignore[no-untyped-def]
            result = await original_initialize(self)
            holder["result"] = result
            return result

        ClientSession.initialize = _capturing_initialize  # type: ignore[method-assign]
        try:
            async with AsyncExitStack() as stack:
                client = await stack.enter_async_context(
                    McpTestClient(
                        cfg.mcp_server.command,
                        cfg.mcp_server.args,
                        cfg.mcp_server.timeout_seconds,
                    )
                )
                init_result = holder.get("result")
                if init_result is None:
                    # Defensive: McpTestClient.__aenter__ always calls
                    # session.initialize(); a missing capture means the
                    # mcp SDK contract changed under us.
                    raise RuntimeError(
                        "ClientSession.initialize was not invoked during "
                        "McpTestClient.__aenter__; mcp SDK contract changed "
                        "(see _run_codegen_handshake docstring for the recovery)."
                    )
                server_info = getattr(init_result, "serverInfo", None)
                tools = await client.list_tools()
                return server_info, tools
        finally:
            ClientSession.initialize = original_initialize  # type: ignore[method-assign]


async def _list_tools_async(cfg: Config) -> list[Tool]:
    """Drive the MCP client lifecycle on a single task.

    AsyncExitStack is technically redundant with the single-context
    `async with McpTestClient(...)` form, but it is used anyway to:
    (1) future-proof against adding a second resource (e.g., a logger
        handle),
    (2) keep the same-task __aenter__/__aexit__ ownership pattern
        explicit (avoids the cancel-scope teardown bug if a second
        resource is added later),
    (3) keep __aexit__ semantics identical regardless of how many
        resources land.
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

    Default: name(signature) + 1-line truncated description.
    --full:  name(signature) + wrapped full description + per-parameter
             descriptions from inputSchema.
    --name PATTERN: substring filter applied post-sort, pre-render.

    Sort: alphabetical by name.
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

    Sorted alphabetically by name. Trailing newline so the output
    composes with shell pipelines. No `default=` fallback: MCP tool
    schemas are JSON Schema documents and MUST be JSON-serializable by
    contract. If `json.dumps` raises `TypeError` here, that is the
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
    """Hand-format a complete self-contained YAML scaffold.

    Output shape (the operator-facing scaffold contract -- see
    docs/ERROR-STYLE.md for the surrounding error-message style guide):
    - Top-level `ollama:`, `mcp_server:`, `judge_timeout_seconds:`,
      `version:`, `test_code:`, and `tools:` blocks all populated.
    - `version: 2` literal (this release's accepted schema version).
    - Every discovered tool emitted as
      `<name>: { skip: true, skip_reason: ... }` with the name passed
      through `_yaml_key` for defensive YAML quoting.
    - All string scalars JSON-quoted via `json.dumps` (avoids YAML
      scalar ambiguity for values containing colons, hashes, or quotes).

    Tools sorted alphabetically.
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
        "# test-code codegen + fixture output path. REQUIRED.\n"
        "#\n"
        "# The `mcp-test-framework gen-test-classes` command writes generated\n"
        "# typed classes into <generated_root>/<server_slug>/, and the\n"
        "# `mcp_session` pytest fixture loads them from the same path.\n"
        "# Recommended convention: `tests/test_code/_generated` (colocated\n"
        "# with your tests/test_code/ scenarios; the `_` prefix signals\n"
        "# \"tool-managed, don't hand-edit\"). Pick any path you want --\n"
        "# the framework does not enforce a layout.\n"
        "#\n"
        "# Non-absolute paths are resolved relative to the current working\n"
        "# directory when the config is loaded.\n"
        "test_code:\n"
        f"  generated_root: {json.dumps('tests/test_code/_generated')}\n"
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
