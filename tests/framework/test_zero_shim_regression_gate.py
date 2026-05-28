"""SHIM-09 cross-surface zero-shim regression gate.

"Zero shims" means "zero FUNCTIONAL shims — every surviving surface hard-rejects" (D-01).
This gate probes five retired v1.5 shim surfaces and fails loudly when a *functional* shim
is reintroduced. Behavioral assertions only — no operator-tone message-text strings are
re-pinned here; Phase 31/32 per-surface tests own those (D-02/D-07).

The grandfathered intercepts (sdet/__init__.py raise, --sdet/gen-sdet-classes Typer
intercepts, six pytest.fail fixture stubs, mcp-test-framework console-script,
tests/sdet/ warn-detector) survive through v1.5 and are clean-deleted in v1.6. This gate
asserts they hard-reject; it does NOT flag them as reintroductions.

No shared fixtures. No subprocess. No network. Runtime <1s. (D-08)
"""
from __future__ import annotations

import ast
import importlib
import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_import_surface_shim_absent() -> None:
    """SHIM-01: importing mcp_test_framework.sdet must raise ModuleNotFoundError.

    A functional reintroduction (sdet/__init__.py re-exporting symbols instead of
    raising) is exactly what flips this red — the pytest.raises block does not raise,
    and pytest itself fails the test.
    """
    sys.modules.pop("mcp_test_framework.sdet", None)  # Pitfall 5: ensure fresh load
    with pytest.raises((ModuleNotFoundError, ImportError)):
        importlib.import_module("mcp_test_framework.sdet")


def test_cli_surface_shims_reject() -> None:
    """SHIM-02/SHIM-03/SHIM-08: CLI + console-script surfaces must all hard-reject."""
    from mcp_test_framework.cli import app

    runner = CliRunner()

    r1 = runner.invoke(app, ["run", "--sdet"])
    assert r1.exit_code == 2, (
        "CLI surface (SHIM-02/SHIM-09): `--sdet` no longer exits 2 (got "
        f"exit_code={r1.exit_code!r}). The --sdet hidden Typer intercept must keep "
        "raising (BadParameter -> exit 2), not work as a flag, until the v1.6 "
        "clean-delete. A working --sdet here is a reintroduced shim."
    )

    r2 = runner.invoke(app, ["gen-sdet-classes"])
    assert r2.exit_code == 2, (
        "CLI surface (SHIM-03/SHIM-09): `gen-sdet-classes` no longer exits 2 (got "
        f"exit_code={r2.exit_code!r}). The hidden command must keep hard-rejecting "
        "until the v1.6 clean-delete; running real codegen here is a reintroduced shim."
    )

    from mcp_test_framework import _deprecated_script

    with pytest.raises(SystemExit) as exc:
        _deprecated_script.main()
    assert exc.value.code == 2, (
        "Console-script surface (SHIM-08/SHIM-09): mcp-test-framework hard-reject must "
        f"sys.exit(2); got code={exc.value.code!r}. _deprecated_script.main() must remain "
        "a hard-reject intercept (not a working wrapper) until the v1.6 clean-delete."
    )

    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_bytes().decode())
    scripts = data.get("project", {}).get("scripts", {})
    assert "mcp-test-framework" in scripts, (
        "Console-script surface (SHIM-08/SHIM-09): [project.scripts].mcp-test-framework "
        "missing from pyproject.toml. The entry must stay wired to the hard-reject stub "
        "through v1.5 so operators get a pointer, not shell 'command not found'. "
        "Clean-delete the entry in v1.6, not before."
    )
    assert "_deprecated_script" in scripts["mcp-test-framework"], (
        f"Console-script surface (SHIM-08/SHIM-09): mcp-test-framework wiring "
        f"({scripts['mcp-test-framework']!r}) no longer points at _deprecated_script. "
        "Must remain wired to the hard-reject stub through v1.5; v1.6 removes the entry."
    )


def test_config_surface_shims_absent() -> None:
    """SHIM-04/SHIM-05: config.py must have no Field alias/validation_alias resolving to
    'sdet' and no 'MCPTF_CONFIG_FILE' string literal. AST walk of config.py ONLY.

    Pitfall 1: do NOT walk _plugin.py (grandfathered MCPTF read at line 186 is out of scope).
    Pitfall 2: do NOT text-scan (comment-level references would cause false positives).
    """
    config_src = (REPO_ROOT / "src" / "mcp_test_framework" / "config.py").read_text(encoding="utf-8")
    tree = ast.parse(config_src, filename="config.py")

    # (a) no Field(alias="sdet") / Field(validation_alias=AliasChoices(..., "sdet"))
    alias_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in ("alias", "validation_alias"):
                    for vnode in ast.walk(kw.value):
                        if isinstance(vnode, ast.Constant) and vnode.value == "sdet":
                            alias_hits.append(getattr(node, "lineno", "?"))
    assert not alias_hits, (
        f"Config surface (SHIM-04/SHIM-09): a Field alias/validation_alias resolving to "
        f"'sdet' reappeared in config.py at line(s) {alias_hits!r}. The cfg.sdet.* alias "
        "was FULLY deleted in Phase 31 (no surviving intercept) -- re-adding it is a "
        "reintroduced shim. The config model must stay alias-free through v1.6."
    )

    # (b) no MCPTF_CONFIG_FILE literal in config.py
    # (the _plugin.py grandfathered read is OUT of scope — owned by test_phase_31_mcptf_config_file_scrub.py)
    env_hits = [
        getattr(n, "lineno", "?")
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and n.value == "MCPTF_CONFIG_FILE"
    ]
    assert not env_hits, (
        f"Config surface (SHIM-05/SHIM-09): 'MCPTF_CONFIG_FILE' appears as a literal in "
        f"config.py at line(s) {env_hits!r}. The env-var config route was FULLY deleted "
        "from the config model in Phase 31; the only surviving reference is the "
        "grandfathered warn-detector in _plugin.py (out of scope here, owned by "
        "test_phase_31_mcptf_config_file_scrub.py). Re-adding the read to config.py is a "
        "reintroduced shim."
    )


def test_fixture_surface_stubs_present() -> None:
    """SHIM-07: exactly six unprefixed fixture stub-raise functions must remain in _plugin.py.

    AST walk of _plugin.py — do NOT use pytester (Pitfall 4: six subprocess round-trips
    violate the <1s runtime constraint).

    Asserts each of the six expected names is a @pytest.fixture-decorated function whose
    body calls pytest.fail. Reintroduction = a stub body replaced with a real return
    (re-aliasing) -> no pytest.fail in body -> name drops out -> probe FAILS.
    NOTE: the surface is SIX fixtures -- `client` is NOT among them.
    """
    plugin_src = (REPO_ROOT / "src" / "mcp_test_framework" / "_plugin.py").read_text(encoding="utf-8")
    ptree = ast.parse(plugin_src, filename="_plugin.py")

    EXPECTED = frozenset({
        "config", "judge", "target_tool",
        "rubric_clarity", "rubric_disambiguation", "rubric_parameters",
    })

    stubs_with_fail: set[str] = set()
    for node in ast.walk(ptree):
        if not isinstance(node, ast.FunctionDef) or node.name not in EXPECTED:
            continue
        is_fixture = any(
            (isinstance(d, ast.Attribute) and d.attr == "fixture")
            or (isinstance(d, ast.Name) and d.id == "fixture")
            or (
                isinstance(d, ast.Call)
                and (
                    (isinstance(d.func, ast.Attribute) and d.func.attr == "fixture")
                    or (isinstance(d.func, ast.Name) and d.func.id == "fixture")
                )
            )
            for d in node.decorator_list
        )
        if not is_fixture:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                f = child.func
                if (isinstance(f, ast.Attribute) and f.attr == "fail") or (
                    isinstance(f, ast.Name) and f.id == "fail"
                ):
                    stubs_with_fail.add(node.name)
                    break

    missing = EXPECTED - stubs_with_fail
    assert not missing, (
        f"Fixture surface (SHIM-07/SHIM-09): {sorted(missing)!r} unprefixed fixture(s) are no "
        "longer registered in _plugin.py as @pytest.fixture stubs that call pytest.fail. "
        "Each must remain a hard-reject stub pointing at its mcp_*-prefixed name until the "
        "v1.6 clean-delete; replacing a body with a real return (re-aliasing) is a "
        "reintroduced shim. (NOTE: the surface is SIX fixtures -- `client` is NOT among them.)"
    )


def test_discovery_surface_not_auto_collected() -> None:
    """SHIM-06: tests/sdet/ must contain no test_*.py files; warn-detector must survive in _plugin.py.

    Two probes:
    1. No collectible test files in tests/sdet/ (legacy discovery path removed in v1.5).
    2. The warn-on-presence detector string survives in _plugin.py source (if deleted,
       stray legacy files would silently collect without warning).
    """
    sdet_dir = REPO_ROOT / "tests" / "sdet"
    sdet_tests = sorted(sdet_dir.glob("test_*.py")) if sdet_dir.is_dir() else []
    assert not sdet_tests, (
        f"Discovery surface (SHIM-06/SHIM-09): tests/sdet/ contains "
        f"{[str(p.relative_to(REPO_ROOT)) for p in sdet_tests]!r}. Only tests/test_code/ is "
        "auto-discovered as of v1.5; legacy test files must not live under tests/sdet/. "
        "Move them to tests/test_code/ (the warn-detector in _plugin.py fires on their "
        "presence). This stays enforced until the v1.6 clean-delete."
    )

    plugin_src = (REPO_ROOT / "src" / "mcp_test_framework" / "_plugin.py").read_text(encoding="utf-8")
    assert "tests/sdet/ is no longer auto-discovered as of v1.5" in plugin_src, (
        "Discovery surface (SHIM-06/SHIM-09): the tests/sdet/ warn-on-presence detector "
        "string was removed from _plugin.py. The detector must survive through v1.5 so a "
        "stray legacy dir warns instead of silently collecting; clean-delete in v1.6."
    )
