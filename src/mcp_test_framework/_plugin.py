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

import os
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_test_framework._black_box_guard import check_black_box
from mcp_test_framework.config import Config

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
    if os.environ.get("MCPTF_CONFIG_FILE"):
        warnings.warn(
            "MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be "
            "removed in v1.5 — use `[tool.pytest.ini_options] mcp_config_file = "
            "PATH` in pyproject.toml or pass `--config PATH` to mcp-contracts "
            "run instead.",
            DeprecationWarning,
            stacklevel=2,
        )

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


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Hook slot reserved for a future library-mode milestone's contract-test injection.

    Body is intentionally empty — locking the hook surface so a future
    milestone only adds behavior, never declarations.
    """
    # No-op.


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
