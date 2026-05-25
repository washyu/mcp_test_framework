"""mcp_test_framework pytest plugin — entry-point target.

Registered via [project.entry-points.pytest11] in pyproject.toml so pytest
auto-discovers the framework's fixtures and hooks WITHOUT any
`pytest_plugins=[...]` declaration in the operator's conftest.

Current skeleton:
  - Hook signatures (`pytest_configure`, `pytest_collection_modifyitems`,
    `pytest_addoption`) are pre-declared with no-op bodies.
  - Session-scoped fixtures are re-exported from `mcp_test_framework.fixtures`
    under their renamed `mcp_*` names.
  - Six unprefixed deprecation aliases (`config`, `judge`, `target_tool`,
    `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) are
    declared here as separate `@pytest.fixture` defs that depend on the
    prefixed fixture and emit a one-time DeprecationWarning per process.
    All six aliases drop in v1.5.

A library-mode milestone fills the hook bodies with an ini-driven
entry point: operators set
`[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` and the
plugin auto-injects parametrized contract tests at collection time.
This plugin is intentionally
framework-primitive: NO SUT-aware logic, NO homelab-mcp imports, NO
opinions about what tools exist.

Coexistence note: `tests/conftest.py:30-55` also defines `pytest_configure`
for the framework's own `sys.modules` black-box guard. Pytest invokes both
hooks; this plugin's body is purely additive (marker registration only)
and MUST NOT remove or relocate the guard. The relocated guard now lives in
`src/mcp_test_framework/_black_box_guard.py` and is invoked from this
plugin; a later cleanup plan in this phase removes the duplicate guard in
`tests/conftest.py`.
"""
from __future__ import annotations

import asyncio
import os
import sys
import warnings
from pathlib import Path

import pytest
from _pytest.python import Module as _PytestModule
from pydantic import ValidationError

from mcp_test_framework._black_box_guard import check_black_box
from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient

# Re-export the renamed prefixed fixtures from fixtures.py so the pytest
# auto-discovery surfaces them without the operator needing
# `pytest_plugins=[...]`. Internal fixtures (`_preflight`,
# `_isolated_home`) and the function-scoped `tool_config` are re-exported
# too so the framework's own test suite continues to see them via the
# entry-point load path. The `noqa: F401` markers signal that these
# imports are intentionally side-effect-only — pytest discovers fixtures
# by attribute name on the plugin module.
from mcp_test_framework.fixtures import (  # noqa: F401
    _isolated_home,
    _preflight,
    mcp_client,
    mcp_config,
    mcp_judge,
    mcp_rubric_clarity,
    mcp_rubric_disambiguation,
    mcp_rubric_parameters,
    mcp_target_tool,
    tool_config,
)


# ---------------------------------------------------------------------------
# Operator-tone warning renderer.
#
# Module-level so multiple warn sites in this plugin (the legacy
# MCPTF_CONFIG_FILE env-var detector in pytest_configure AND the
# tests/sdet/ presence detector in pytest_collection) share a single
# renderer. Saving the stdlib formatter once at import time lets each
# call site swap in this formatter under a try/finally and restore the
# stdlib formatter afterwards without rebuilding the saver each call.
# ---------------------------------------------------------------------------

_original_formatwarning = warnings.formatwarning


def _mcptf_formatwarning(message, category, filename, lineno, line=None):
    """Operator-tone single-block render. Bypasses pytest's default
    "<file>:<line>: DeprecationWarning: <msg>" shape so the warning
    is unambiguously distinct from pytest's own deprecation chatter."""
    prefix = "[mcp-contracts]"
    try:
        if sys.stderr.isatty():
            prefix = f"\x1b[31m{prefix}\x1b[0m"
    except Exception:
        pass
    return f"\n{prefix} {message}\n\n"


# ---------------------------------------------------------------------------
# Synthetic contracts-module collector
#
# Subclasses `_pytest.python.Module` so pytest collects from a real on-disk
# file (preserves pytest-asyncio's `pytestmark` discovery on the underlying
# `path`), then overrides the rendered `nodeid` to a synthetic label. The
# Wave 0 spike validated this hybrid pattern under pytest-asyncio strict
# mode with loop_scope="session".
# ---------------------------------------------------------------------------

class _ContractsModule(_PytestModule):
    """Synthesized contracts module collector with overridden nodeid.

    Underlying `path` points at the real `_tests.py` inside the installed
    wheel so pytest-asyncio's `pytestmark = [pytest.mark.asyncio(loop_scope=
    "session")]` discovery works normally. The `nodeid` property is
    overridden to render as the synthetic literal `<mcp-contracts>` in
    pytest's output instead of the wheel-internal filesystem path.
    """

    @property
    def nodeid(self) -> str:  # type: ignore[override]
        return "<mcp-contracts>"


# ---------------------------------------------------------------------------
# Brief MCP handshake for parametrize-time tool discovery
#
# Verbatim relocation of `tests/conftest.py:_discover_tools` (the legacy
# parametrize-site discovery helper). Reuses `McpTestClient.__aenter__`
# so the spawned subprocess inherits the per-instance temp-dir isolation
# contract from the framework's core client.
# ---------------------------------------------------------------------------

async def _discover_tools_live(cfg: Config) -> list[str]:
    """Brief MCP handshake to enumerate the server's tools.

    Used by `pytest_collection` to determine which tools to parametrize
    the synthesized contract tests over. Single short subprocess; the
    isolation contract is inherited from `McpTestClient.__aenter__`.
    """
    async with McpTestClient(
        cfg.mcp_server.command,
        cfg.mcp_server.args,
        cfg.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]


# ---------------------------------------------------------------------------
# Hook skeletons: bodies are intentionally trivial. A future library-mode
# milestone fills register()-driven behavior here without re-touching
# pyproject.toml or the entry-point declaration.
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """Register the `mcp_contract` marker and (if `mcp_config_file` ini is set)
    load the operator's YAML config, run the black-box guard, and stash the
    Config instance on `config._mcp_contracts_config` for the collection hook
    to consume.

    Responsibilities:
      - Always: register `mcp_contract` marker.
      - Always: if `MCPTF_CONFIG_FILE` env var is set, emit DeprecationWarning
        regardless of mode. Library mode IGNORES the env var's value.
      - If `mcp_config_file` ini set: resolve path, fail-loud on missing-path
        or invalid-YAML, construct Config(yaml_file=path), run black-box guard,
        stash Config on config._mcp_contracts_config.
      - If `mcp_config_file` ini unset/empty: silent no-op.
    """
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test.",
    )

    # Emit DeprecationWarning if MCPTF_CONFIG_FILE is set in env.
    #
    # NOTE for the future EOL planner: this MCPTF_CONFIG_FILE detection is
    # grandfathered in src/ for v1.5; planned removal lands in v1.6
    # alongside the other operator-facing env-var removals.
    if os.environ.get("MCPTF_CONFIG_FILE"):
        warnings.formatwarning = _mcptf_formatwarning
        try:
            warnings.warn(
                # Verbatim operator-tone wording; the literal substring
                # "no longer honored as of v1.5" must remain intact on one
                # source line so source-side regression scans pass.
                "MCPTF_CONFIG_FILE is set in your environment but"
                " no longer honored as of v1.5;"
                " configure via `[tool.pytest.ini_options]"
                " mcp_config_file = PATH` in pyproject.toml or pass"
                " `--config PATH` to `mcp-contracts run`.",
                DeprecationWarning,
                stacklevel=2,
            )
        finally:
            warnings.formatwarning = _original_formatwarning

    # Read ini; empty string = operator opted out, silent no-op.
    raw = (config.getini("mcp_config_file") or "").strip()
    if not raw:
        return

    # Resolve relative to pyproject.toml's directory.
    path = Path(raw)
    if not path.is_absolute():
        path = config.rootpath / path

    # Fail-loud if path doesn't exist or isn't a file.
    if not path.is_file():
        pytest.exit(
            f"mcp_config_file points at {path!s} which does not exist or "
            f"is not a file\n"
            f"\nnext: check the path in [tool.pytest.ini_options] in "
            f"pyproject.toml, or run `mcp-contracts config-init -o config.yaml`",
            returncode=2,
        )

    # Load via existing pydantic-settings yaml_file= kwarg path.
    # On ValidationError, render operator-tone and pytest.exit(2).
    try:
        cfg = Config(yaml_file=str(path))
    except ValidationError as exc:
        # Lazy-import to avoid cli.py <-> _plugin.py circular at module load.
        from mcp_test_framework.cli import _emit_operator_error_for_validation
        try:
            _emit_operator_error_for_validation(exc, source=str(path))
        except SystemExit:
            # _emit_operator_error_for_validation raises typer.Exit (SystemExit
            # subclass) with code=2. Translate to pytest.exit so the convention
            # `returncode=2 = setup error` is preserved end-to-end.
            pytest.exit(
                f"mcp_config_file validation failed: {path!s}\n"
                f"\nnext: check the YAML against config.example.yaml or run "
                f"`mcp-contracts config-init -o config.yaml`",
                returncode=2,
            )

    # Relocated black-box guard. Raises RuntimeError on sys.modules leak;
    # let it propagate (pytest surfaces it as a session-startup error).
    check_black_box()

    # Stash for the collection hook to consume.
    config._mcp_contracts_config = cfg  # type: ignore[attr-defined]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Reserve the --mcp-* CLI option namespace and register the
    `mcp_config_file` ini key.

    The ini key is the operator's library-mode entry point. Set in
    [tool.pytest.ini_options] in pyproject.toml; relative paths resolve
    against the directory containing pyproject.toml. Absent or empty
    string = library mode opted out (silent no-op).
    """
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    parser.addini(
        "mcp_config_file",
        type="string",
        default="",
        help=(
            "Path to MCP test framework YAML config; relative paths are "
            "resolved relative to pyproject.toml's directory. Absent or "
            "empty = library mode opted out (no contract tests injected)."
        ),
    )


def pytest_collection(session: pytest.Session) -> None:
    """Synthesize and stash the `<mcp-contracts>` virtual Module collector.

    Runs once per session. Gated on the `_mcp_contracts_config` stash set
    in `pytest_configure` when `mcp_config_file` ini is present:

      - No stash -> silent no-op (operator opted out of library mode).
      - Empty opt-in allowlist (all tools `skip=True` or `config.tools`
        empty) -> silent no inject.
      - No intersection between discovered server tools and the opt-in
        allowlist -> silent no inject.
      - Otherwise: brief MCP handshake, construct `_ContractsModule`
        pointing at the real on-disk `contracts/_tests.py`, stash the
        parametrize list + sentinel on the module, apply the
        `mcp_contract` marker, append to a session-scoped collector
        stash for `pytest_collection_modifyitems` to descend into.

    The two-hook attachment ritual (stash here, descend +
    re-apply-marker + append-items in `pytest_collection_modifyitems`)
    is the spike-validated mechanism from Plan 27-01: pytest's default
    `Session.collect()` walk does NOT descend into out-of-band-attached
    collectors, and the module-level `add_marker` does NOT auto-propagate
    to `Function` children in this construction path. Both gaps are
    closed in the sibling hook below.
    """
    # tests/sdet/ is no longer auto-discovered as of v1.5; this detector
    # survives the surface removal so operators mid-migration see a loud
    # signal. Planned removal: future EOL pass.
    legacy_dir = session.config.rootpath / "tests" / "sdet"
    if legacy_dir.is_dir() and any(legacy_dir.glob("test_*.py")):
        warnings.formatwarning = _mcptf_formatwarning
        try:
            warnings.warn(
                "tests/sdet/ is no longer auto-discovered as of v1.5\n"
                "\n"
                "the `tests/sdet/` directory contains test_*.py files but is "
                "no longer collected by `mcp-contracts run --test-code`.\n"
                "every scenario should live under `tests/test_code/`; the "
                "two layouts are otherwise identical.\n"
                "\n"
                "next: move your `tests/sdet/test_*.py` files to "
                "`tests/test_code/` and re-run.",
                DeprecationWarning,
                stacklevel=2,
            )
        finally:
            warnings.formatwarning = _original_formatwarning

    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return  # silent no-op carry-forward; operator opted out

    # Opt-in allowlist: only tools explicitly listed with skip=False are
    # eligible. Verbatim semantics from the legacy parametrize-site filter
    # (project hotfix invariant: unselected tools are excluded at
    # parametrize time, never via runtime `pytest.skip()`).
    allowed = sorted(
        name for name, tcfg in cfg.tools.items() if not tcfg.skip
    )
    if not allowed:
        return  # empty allowlist, silent no inject

    # Brief MCP handshake. Operator-tone fail-loud on discovery failure;
    # pytest.exit(returncode=2) preserves the framework's setup-error
    # convention (distinguishes from pass=0 / test-failure=1).
    try:
        discovered = asyncio.run(_discover_tools_live(cfg))
    except FileNotFoundError:
        pytest.exit(
            f"MCP server command not on PATH: {cfg.mcp_server.command!r}\n"
            f"\nnext: install {cfg.mcp_server.command!r} or set "
            f"mcp_server.command in your config.yaml to a runnable binary",
            returncode=2,
        )
    except Exception as exc:  # noqa: BLE001 -- mirrors legacy failure-mode parity
        pytest.exit(
            f"MCP tool discovery failed against {cfg.mcp_server.command!r} "
            f"{cfg.mcp_server.args!r}: {exc!s}\n"
            f"\nnext: verify the MCP server starts on its own via "
            f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}`",
            returncode=2,
        )

    # Intersect: only tools the server advertises AND operator opted into.
    parametrize_names = [n for n in allowed if n in discovered]
    if not parametrize_names:
        return  # nothing survives the intersection, silent no inject

    # Synthesize the Module pointing at the real on-disk _tests.py inside
    # the installed wheel. Lazy import keeps the contracts subpackage out
    # of the plugin's module-load path when library mode is opted out.
    from mcp_test_framework.contracts import _tests as _contracts_tests
    tests_path = Path(_contracts_tests.__file__)

    mod = _ContractsModule.from_parent(parent=session, path=tests_path)
    # Sentinel for pytest_generate_tests to gate on.
    mod._is_mcp_contracts_synthetic = True  # type: ignore[attr-defined]
    # Parametrize list stashed for pytest_generate_tests to read.
    mod._mcp_parametrize_tools = parametrize_names  # type: ignore[attr-defined]
    # Apply marker on the module; the sibling collection-modify hook
    # re-applies it explicitly per Function child (spike finding: the
    # module-level marker does not auto-propagate to Function children
    # in the out-of-band attachment path).
    mod.add_marker(pytest.mark.mcp_contract)

    # Stash on session for pytest_collection_modifyitems to descend into.
    if not hasattr(session, "_mcp_synthetic_collectors"):
        session._mcp_synthetic_collectors = []  # type: ignore[attr-defined]
    session._mcp_synthetic_collectors.append(mod)  # type: ignore[attr-defined]


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Descend into stashed synthetic collectors and append their items.

    Pytest's default `Session.collect()` walk does NOT descend into
    out-of-band-attached collectors stashed in `pytest_collection`. This
    hook closes that gap by using `session.genitems(collector)` (the
    same recursive descent pytest's own collection walk uses), which
    invokes `_collect_one_node` -> `PyCollector._genfunctions` ->
    `pytest_generate_tests` for every test function -- so the plugin's
    `pytest_generate_tests` hook fires and indirect-parametrize on
    `mcp_target_tool` is applied to each item.

    The `mcp_contract` marker is re-applied per item explicitly: the
    module-level `add_marker` on the synthetic collector does not
    auto-propagate to `Function` children in this construction path
    (Wave 0 spike Pitfall 2).
    """
    extra = getattr(session, "_mcp_synthetic_collectors", []) or []
    for collector in extra:
        # session.genitems triggers the full `_genfunctions` chain (firing
        # pytest_generate_tests on each test function) -- distinct from
        # the bare collector.collect() which bypasses parametrize.
        for item in session.genitems(collector):
            item.add_marker(pytest.mark.mcp_contract)
            items.append(item)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Indirect-parametrize `mcp_target_tool` for the synthesized contract tests.

    Gated on the `_is_mcp_contracts_synthetic` sentinel so this hook ONLY
    fires for framework-injected contract tests. Operator tests that
    happen to request an `mcp_target_tool` fixture (unlikely) are
    untouched.

    Opt-in invariant: parametrize list is the pre-filtered
    `_mcp_parametrize_tools` stash; excluded tools were never collected
    in the first place (no runtime `pytest.skip()` for excluded tools).

    Sentinel-reading nuance: `metafunc.module` is the imported Python
    module object (`mcp_test_framework.contracts._tests`), NOT the
    `_ContractsModule` collector instance where the sentinel is stashed.
    We resolve the collector via the metafunc's definition node and walk
    up to find the synthesized collector.
    """
    if "mcp_target_tool" not in metafunc.fixturenames:
        return
    # Walk up from the FunctionDefinition to find the enclosing
    # _ContractsModule collector (which carries the sentinel + parametrize
    # list); the imported `_tests` Python module on metafunc.module does
    # not.
    node = metafunc.definition
    synth_collector = None
    while node is not None:
        if getattr(node, "_is_mcp_contracts_synthetic", False):
            synth_collector = node
            break
        node = getattr(node, "parent", None)
    if synth_collector is None:
        return
    names = getattr(synth_collector, "_mcp_parametrize_tools", [])
    if not names:
        return  # defensive: empty allowlist should not reach here
    metafunc.parametrize(
        "mcp_target_tool",
        names,
        indirect=True,
        ids=names,
    )


# ---------------------------------------------------------------------------
# Deprecation aliases:
#
# Each unprefixed alias is a separate `@pytest.fixture` def that:
#   1. Receives the prefixed fixture as a parameter (DI; no manual lookup).
#   2. Calls `warnings.warn(DeprecationWarning, stacklevel=2)` once per
#      process per alias — the default Python warning filter dedups, so
#      a session-wide use prints exactly one warning per alias.
#   3. Returns the prefixed value unchanged (identity passthrough).
#
# Six aliases drop coherently in v1.5 alongside every other v1.4
# deprecation shim. Hardcoded deprecation copy per call site (no central
# constant).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def config(mcp_config):
    """Deprecated alias for `mcp_config` — removed in v1.5."""
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config


@pytest.fixture(scope="session")
def judge(mcp_judge):
    """Deprecated alias for `mcp_judge` — removed in v1.5."""
    warnings.warn(
        "the `judge` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_judge` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_judge


@pytest.fixture(scope="session")
def target_tool(mcp_target_tool):
    """Deprecated alias for `mcp_target_tool` — removed in v1.5."""
    warnings.warn(
        "the `target_tool` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_target_tool` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_target_tool


@pytest.fixture(scope="session")
def rubric_clarity(mcp_rubric_clarity):
    """Deprecated alias for `mcp_rubric_clarity` — removed in v1.5."""
    warnings.warn(
        "the `rubric_clarity` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_clarity` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_clarity


@pytest.fixture(scope="session")
def rubric_disambiguation(mcp_rubric_disambiguation):
    """Deprecated alias for `mcp_rubric_disambiguation` — removed in v1.5."""
    warnings.warn(
        "the `rubric_disambiguation` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_disambiguation` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_disambiguation


@pytest.fixture(scope="session")
def rubric_parameters(mcp_rubric_parameters):
    """Deprecated alias for `mcp_rubric_parameters` — removed in v1.5."""
    warnings.warn(
        "the `rubric_parameters` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_parameters` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_parameters
