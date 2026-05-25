"""Phase 29 Plan 03 tests: CLI reporter rewire.

Pins Phase 29 D-05 + REPORTER-01:
  - Default mcp-contracts run path passes --mcp-domain-ui=force to pytest.
  - -q / --quiet (without --debug) passes --mcp-domain-ui=off (reporter
    silent; CLI parses JUnit and renders summary).
  - --debug path passes --mcp-domain-ui=force (reporter renders default
    UI; CLI appends appendix after subprocess returns).
  - REVISION Rule A: -q --debug passes --mcp-domain-ui=force (--debug
    wins over -q for reporter-mode resolution).
  - --raw path unaffected (raw bypasses the wrapped pytest entirely;
    the kwarg still threads but the reporter is never relevant).
  - render_domain_ui() and _render_pre_run_digest() are NO LONGER called
    from cli.py at runtime (REVISION Edit 6: reporter owns the contract-
    path digest; CLI keeps the test-code scenario digest and --explain
    expansion).
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from mcp_test_framework import _runner
from mcp_test_framework.cli import app


# ---------------------------------------------------------------------------
# argv-composition tests (no CLI wiring; pure _build_pytest_args input/output)
# ---------------------------------------------------------------------------


def test_build_pytest_args_appends_force() -> None:
    """domain_ui_mode='force' appends --mcp-domain-ui=force to argv."""
    argv = _runner._build_pytest_args(
        None,
        [],
        with_framework=False,
        test_code=False,
        mcp_config_path=None,
        domain_ui_mode="force",
    )
    assert "--mcp-domain-ui=force" in argv, argv


def test_build_pytest_args_omits_when_off() -> None:
    """domain_ui_mode='off' (default) omits the flag entirely.

    Off means the kwarg does not contribute any argv element -- the
    reporter's own default is off, so silence is equivalent to no flag.
    """
    argv = _runner._build_pytest_args(
        None,
        [],
        with_framework=False,
        test_code=False,
        mcp_config_path=None,
    )
    assert not any(a.startswith("--mcp-domain-ui") for a in argv), argv

    # Same when 'off' is passed explicitly.
    argv2 = _runner._build_pytest_args(
        None,
        [],
        with_framework=False,
        test_code=False,
        mcp_config_path=None,
        domain_ui_mode="off",
    )
    assert not any(a.startswith("--mcp-domain-ui") for a in argv2), argv2


def test_build_pytest_args_appends_auto() -> None:
    """domain_ui_mode='auto' appends --mcp-domain-ui=auto."""
    argv = _runner._build_pytest_args(
        None,
        [],
        with_framework=False,
        test_code=False,
        mcp_config_path=None,
        domain_ui_mode="auto",
    )
    assert "--mcp-domain-ui=auto" in argv, argv


def test_build_pytest_args_rejects_invalid_mode() -> None:
    """Defensive validation: bogus mode raises ValueError at the top of the
    function so the bad value never reaches argv."""
    with pytest.raises(ValueError, match="domain_ui_mode must be one of"):
        _runner._build_pytest_args(
            None,
            [],
            with_framework=False,
            test_code=False,
            mcp_config_path=None,
            domain_ui_mode="bogus",
        )


def test_build_pytest_args_flag_appended_after_forwarded() -> None:
    """The CLI's --mcp-domain-ui choice must appear AFTER any operator-
    forwarded --mcp-domain-ui so pytest's last-occurrence argparse rule
    yields the CLI's value."""
    argv = _runner._build_pytest_args(
        None,
        ["--mcp-domain-ui=off"],  # operator-supplied earlier
        with_framework=False,
        test_code=False,
        mcp_config_path=None,
        domain_ui_mode="force",
    )
    # Both should be present, but the CLI's "force" must be LAST.
    indices = [i for i, a in enumerate(argv) if a.startswith("--mcp-domain-ui")]
    assert len(indices) == 2, argv
    assert argv[indices[-1]] == "--mcp-domain-ui=force", argv


# ---------------------------------------------------------------------------
# CliRunner tests: verify the flag-to-mode wiring inside cli.run
# ---------------------------------------------------------------------------


_MINIMAL_CONFIG_YAML = textwrap.dedent("""\
    version: 2
    mcp_server:
      command: "true"
      args: []
    test_code:
      generated_root: "generated"
    tools: {}
""")


def _stub_cli_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Wire up the stubs needed to invoke cli.run without spawning pytest or
    talking to a live MCP server.

    Returns a dict that the fake run_pytest_subprocess populates with its
    kwargs so assertions can inspect what cli.run computed.
    """
    captured: dict[str, Any] = {}

    def _fake_subprocess(**kwargs: Any) -> tuple[int, Path, str, str]:
        captured.update(kwargs)
        # Write a minimal-but-valid JUnit XML so the CLI's post-subprocess
        # parse_junit_xml call (preserved for -q-no-debug and --debug paths)
        # does NOT raise ET.ParseError. The CLI allocates the tempfile path
        # itself in default mode; we need to write to it from inside our
        # stub. The CLI passes junit_xml=<operator path or None> and the
        # actual tempfile is allocated by run_pytest_subprocess. Since we
        # are REPLACING run_pytest_subprocess, we allocate our own tmp.
        junit_path = tmp_path / "captured_junit.xml"
        junit_path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<testsuites><testsuite name="pytest" tests="0" failures="0" '
            'errors="0" skipped="0" time="0.01"/></testsuites>',
            encoding="utf-8",
        )
        return (0, junit_path, "", "")

    monkeypatch.setattr(_runner, "run_pytest_subprocess", _fake_subprocess)

    # Stub discovery so we don't spawn an MCP server. discovered_tools is
    # only consumed by the pre-run digest + RenderContext; the empty list
    # is acceptable here because we aren't asserting on rendered output.
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda cfg: [],
    )

    return captured


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_MINIMAL_CONFIG_YAML)
    return config_path


def test_cli_default_passes_force_to_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default `mcp-contracts run` -> domain_ui_mode='force' (reporter on)."""
    captured = _stub_cli_run(monkeypatch, tmp_path)
    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(app, ["run", "--config", str(config_path)])
    assert "domain_ui_mode" in captured, (captured, result.output)
    assert captured["domain_ui_mode"] == "force", (captured, result.output)


def test_cli_quiet_passes_off_to_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`mcp-contracts run -q` (without --debug) -> domain_ui_mode='off'.

    Reporter stays silent; CLI parses JUnit XML and renders summary-only.
    """
    captured = _stub_cli_run(monkeypatch, tmp_path)
    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(app, ["run", "-q", "--config", str(config_path)])
    assert "domain_ui_mode" in captured, (captured, result.output)
    assert captured["domain_ui_mode"] == "off", (captured, result.output)


def test_cli_debug_passes_force_to_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`mcp-contracts run --debug` -> domain_ui_mode='force'.

    Reporter renders the default UI inside the subprocess; CLI appends the
    --debug appendix on top.
    """
    captured = _stub_cli_run(monkeypatch, tmp_path)
    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(app, ["run", "--debug", "--config", str(config_path)])
    assert "domain_ui_mode" in captured, (captured, result.output)
    assert captured["domain_ui_mode"] == "force", (captured, result.output)


def test_cli_quiet_debug_combination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REVISION Rule A pin: `-q --debug` -> domain_ui_mode='force'.

    --debug WINS over -q for reporter-mode resolution. The operator's
    explicit debug opt-in overrides quiet's summary-only intent. This
    test FAILS under the original `'off' if quiet else 'force'` rule and
    passes under the locked `'force' if debug else ('off' if quiet else
    'force')` expression -- it is the regression pin that prevents drift
    back to the original rule.
    """
    captured = _stub_cli_run(monkeypatch, tmp_path)
    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(
        app, ["run", "-q", "--debug", "--config", str(config_path)]
    )
    assert "domain_ui_mode" in captured, (captured, result.output)
    assert captured["domain_ui_mode"] == "force", (captured, result.output)


def test_cli_raw_bypasses_default_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--raw` bypasses the wrapped pytest entirely.

    The raw branch passes domain_ui_mode through as its default ('off'),
    because the reporter is irrelevant under --raw (no capture, no
    parse, no domain UI render). This test confirms the kwarg is at
    least defaulted; the more interesting behavior (reporter actually
    suppressed) is exercised by the existing run_pytest_subprocess raw
    tests, which still pass.
    """
    captured: dict[str, Any] = {}

    def _fake_subprocess(**kwargs: Any) -> tuple[int, None, str, str]:
        captured.update(kwargs)
        return (0, None, "", "")

    monkeypatch.setattr(_runner, "run_pytest_subprocess", _fake_subprocess)
    # No need to stub _discover_tools_for_run: the raw branch returns early
    # before discovery.

    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(
        app, ["run", "--raw", "--config", str(config_path)]
    )
    assert "raw" in captured, (captured, result.output)
    assert captured["raw"] is True, (captured, result.output)
    # In raw mode, cli.run never computes domain_ui_mode, so the kwarg
    # is NOT passed. The runner-side default kicks in.
    assert "domain_ui_mode" not in captured, (captured, result.output)


# ---------------------------------------------------------------------------
# AST proofs: the deleted callsites stay deleted; the preserved ones stay
# ---------------------------------------------------------------------------


def _cli_call_attrs() -> set[str]:
    """Return the set of method-call attribute names found in cli.py."""
    src = Path(_runner.__file__).parent.joinpath("cli.py").read_text()
    tree = ast.parse(src)
    return {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }


def test_no_render_domain_ui_calls_in_cli_module() -> None:
    """D-05: cli.py default path delegates to reporter; no direct render call."""
    src = Path(_runner.__file__).parent.joinpath("cli.py").read_text()
    tree = ast.parse(src)
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "render_domain_ui"
    ]
    assert calls == [], (
        f"Found unexpected render_domain_ui callsites: {len(calls)}"
    )


def test_no_render_pre_run_digest_calls_in_cli_module() -> None:
    """REVISION Edit 6: contract-path digest moved into reporter; scenario
    digest + --explain expansion stay in CLI."""
    attr_calls = _cli_call_attrs()
    assert "_render_pre_run_digest" not in attr_calls, (
        "REVISION Edit 6: cli.py must not call _render_pre_run_digest "
        "(reporter emits it inside the subprocess)."
    )
    assert "_render_scenario_pre_run_digest" in attr_calls, (
        "REVISION Edit 6: cli.py must still call "
        "_render_scenario_pre_run_digest (reporter does not handle the "
        "test-code scenario variant)."
    )
    assert "_render_skipped_tools_explain" in attr_calls, (
        "REVISION Edit 6: cli.py must still call "
        "_render_skipped_tools_explain (reporter does not handle --explain)."
    )


def test_render_summary_only_and_debug_appendix_still_called_in_cli() -> None:
    """The -q (no --debug) summary path and the --debug appendix path must
    remain wired in cli.py. Rule A: render_summary_only is gated on
    `quiet and not debug`; render_debug_appendix on `debug`."""
    attr_calls = _cli_call_attrs()
    assert "render_summary_only" in attr_calls, (
        "cli.py must still call render_summary_only for the -q (no --debug) path"
    )
    assert "render_debug_appendix" in attr_calls, (
        "cli.py must still call render_debug_appendix for the --debug path"
    )
