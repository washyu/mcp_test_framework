"""Plan 02 integration tests: live domain-UI reporter plugin.

Pins the locked reporter surface via subprocess-pytest:
  - ``--mcp-domain-ui`` option parsing (bare / =force / =off / =bogus).
  - Default OFF -- ``pytest`` (no flag) emits no domain UI.
  - ``--mcp-domain-ui=force`` emits header + rows + summary regardless of TTY.
  - ``--mcp-domain-ui`` (bare) in piped-stdout subprocess -- auto resolves to off.
  - ``-p no:mcp_test_framework_reporter`` makes ``--mcp-domain-ui`` unrecognized.
  - Additive coexistence: pytest-native dots/-v output still appears alongside
    the domain UI (D-02).
  - xdist controller-only emission via worker-input detection (optional smoke
    test gated on pytest_xdist availability).

Each test writes a minimal pyproject.toml + (when asserting banner presence)
a config.yaml + [tool.pytest.ini_options].mcp_config_file pointer + a
parametrized contract-style test, then spawns a pytest subprocess.

# Path chosen: Option A (config.yaml + mcp_config_file ini)
Banner-presence tests load Config end-to-end so the contract plugin
stashes ``_mcp_contracts_config`` and the reporter renders the header.
With ``tools={}`` the contract plugin's ``pytest_collection`` hits the
empty-allowlist short-circuit (no MCP server spawn).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


# Option A: minimal config.yaml that loads cleanly via Config(yaml_file=...).
# Required fields:
#   - test_code.generated_root (TestCodeConfig REQUIRES this; no default)
# mcp_server.command defaults to "homelab-mcp" but is NEVER invoked because
# tools={} triggers the empty-allowlist short-circuit in
# _plugin.py:pytest_collection BEFORE any MCP handshake.
_MINIMAL_CONFIG_YAML = textwrap.dedent("""\
    version: 2
    mcp_server:
      command: "true"
      args: []
    test_code:
      generated_root: "generated"
    tools: {}
""")


def _write_payload_with_config(tmp_path: Path) -> Path:
    """Write a FULL payload: config.yaml + pyproject.toml with mcp_config_file
    ini + a parametrized contract-style test that produces ``[<tool>]``
    nodeids so ``_build_parsed_run_from_reports`` renders per-tool rows.

    Use this for banner-presence assertions (``--mcp-domain-ui=force`` tests).
    """
    (tmp_path / "config.yaml").write_text(_MINIMAL_CONFIG_YAML)
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent("""\
        [tool.pytest.ini_options]
        # Route the contract plugin's pytest_configure to the local
        # config.yaml so _mcp_contracts_config is stashed and the reporter
        # renders the header. tools={} short-circuits the collection-time
        # MCP handshake.
        mcp_config_file = "config.yaml"
    """))
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    # Parametrize suffix [mytool] / [othertool] -> _extract_tool_name returns
    # the tool name -> _build_parsed_run_from_reports populates per_tool.
    (tests_dir / "test_param.py").write_text(textwrap.dedent("""\
        import pytest

        @pytest.mark.parametrize("tool", ["mytool", "othertool"])
        def test_x(tool):
            assert tool != "othertool", "othertool intentionally fails"
    """))
    return tmp_path


def _write_payload_no_config(tmp_path: Path) -> Path:
    """Write a MINIMAL payload with NO config.yaml and NO mcp_config_file ini.

    Use this for banner-ABSENCE assertions (default/off/auto-no-tty tests).
    The contract plugin no-ops at pytest_configure; the reporter short-
    circuits at its own pytest_configure (off / auto-no-tty), so the
    absence of the banner is the off-path early-return, not the graceful-
    degrade header skip.
    """
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent("""\
        [tool.pytest.ini_options]
        # No mcp_config_file -> contract plugin no-ops. This payload is for
        # absence-assertions only, not banner-presence.
    """))
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_simple.py").write_text(textwrap.dedent("""\
        def test_pass():
            assert True
        def test_fail():
            assert False, "expected fail"
    """))
    return tmp_path


def _run_pytest(
    cwd: Path,
    *args: str,
    env_override: dict | None = None,
) -> subprocess.CompletedProcess:
    """Spawn pytest subprocess; capture stdout+stderr; return CompletedProcess.

    Uses ``--rootdir=tmp_path`` so the subprocess pytest does NOT walk up
    into the framework's outer pyproject.toml. Sets ``PYTHONIOENCODING=utf-8``
    so Windows console codepages don't trip the renderer's U+2014 em-dash.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--rootdir",
            str(cwd),
            *args,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_mcp_domain_ui_option_appears_in_help(tmp_path: Path) -> None:
    """`pytest --help` shows the new option with the documented choices."""
    _write_payload_no_config(tmp_path)
    res = _run_pytest(tmp_path, "--help")
    assert "--mcp-domain-ui" in res.stdout, (
        f"--mcp-domain-ui not in pytest --help output.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    # Help text should mention TTY (per the docstring we wrote).
    assert "TTY" in res.stdout, (
        f"Help text for --mcp-domain-ui does not mention 'TTY'.\n"
        f"stdout=\n{res.stdout}"
    )


def test_default_off_no_domain_ui(tmp_path: Path) -> None:
    """`pytest` with no flag emits no domain UI banner.

    Reporter's ``pytest_configure`` short-circuits at ``choice == "off"``.
    """
    _write_payload_no_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/")
    combined = res.stdout + res.stderr
    assert "MCP Test Framework" not in combined, (
        f"Default-off path leaked the domain UI banner.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_force_emits_domain_ui_in_piped_stdout(tmp_path: Path) -> None:
    """`--mcp-domain-ui=force` emits the domain UI even in piped (non-TTY) stdout.

    The contract plugin stashes ``_mcp_contracts_config`` (mcp_config_file ini
    set), so the reporter's ``pytest_collection_finish`` renders the header,
    and ``pytest_sessionfinish`` renders the per-tool rows + summary.
    """
    _write_payload_with_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui=force")
    combined = res.stdout + res.stderr
    assert "MCP Test Framework" in combined, (
        f"Force mode did NOT emit the domain UI banner under piped stdout.\n"
        f"exit={res.returncode}\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    assert "Result:" in combined, (
        f"Force mode did NOT emit the summary 'Result:' line.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    assert "mytool" in combined, (
        f"Force mode did NOT render the 'mytool' per-tool row.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_bare_flag_auto_resolves_to_off_when_no_tty(tmp_path: Path) -> None:
    """`pytest --mcp-domain-ui` (bare) in piped stdout auto-resolves to off.

    Subprocess stdout is piped via capture_output=True -> not a TTY ->
    ``_ORIGINAL_STDOUT.isatty()`` returns False -> reporter's
    ``pytest_configure`` short-circuits.
    """
    _write_payload_no_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui")
    combined = res.stdout + res.stderr
    assert "MCP Test Framework" not in combined, (
        f"Bare flag in piped (non-TTY) subprocess leaked the domain UI banner; "
        f"auto-resolution to 'off' failed.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_explicit_off_value(tmp_path: Path) -> None:
    """`pytest --mcp-domain-ui=off` matches default-off behavior."""
    _write_payload_no_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui=off")
    combined = res.stdout + res.stderr
    assert "MCP Test Framework" not in combined, (
        f"Explicit =off leaked the domain UI banner.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_bogus_value_rejected_by_choices(tmp_path: Path) -> None:
    """`pytest --mcp-domain-ui=bogus` is rejected by argparse `choices=`."""
    _write_payload_no_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui=bogus")
    assert res.returncode != 0, (
        f"Bogus value should have been rejected by choices=, but pytest "
        f"returned 0.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    combined = res.stdout + res.stderr
    assert "--mcp-domain-ui" in combined, (
        f"Error message does not mention --mcp-domain-ui.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    # argparse's invalid-choice error mentions either 'choose from' or 'invalid'.
    assert ("invalid choice" in combined) or ("choose from" in combined), (
        f"Error message does not look like an argparse invalid-choice error.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_p_no_disables_reporter_and_removes_option(tmp_path: Path) -> None:
    """`-p no:mcp_test_framework_reporter` removes the option AND the behavior.

    With the reporter plugin disabled, ``--mcp-domain-ui`` becomes an
    unrecognized argument -- exactly the "single disable knob removes
    both surfaces" guarantee.
    """
    _write_payload_no_config(tmp_path)
    res = _run_pytest(
        tmp_path,
        "tests/",
        "-p",
        "no:mcp_test_framework_reporter",
        "--mcp-domain-ui=force",
    )
    assert res.returncode != 0, (
        f"With reporter disabled, --mcp-domain-ui should have been an "
        f"unrecognized argument (non-zero exit), got returncode=0.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    combined = res.stdout + res.stderr
    assert ("unrecognized" in combined) or ("--mcp-domain-ui" in combined), (
        f"Disabled-plugin error did not mention the unrecognized flag.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_additive_coexistence_pytest_native_output_present(tmp_path: Path) -> None:
    """D-02 additive: pytest-native verbose output coexists with the domain UI.

    Reporter does NOT register pytest_terminal_summary and does NOT
    reassign sys.stdout, so pytest's PASSED/FAILED markers and the nodeids
    still print alongside the domain UI banner.
    """
    _write_payload_with_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui=force", "-v")
    combined = res.stdout + res.stderr
    # Pytest-native markers:
    assert "PASSED" in combined, (
        f"D-02 violated: pytest-native PASSED marker missing under "
        f"--mcp-domain-ui=force -v.\nstdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    assert "FAILED" in combined, (
        f"D-02 violated: pytest-native FAILED marker missing under "
        f"--mcp-domain-ui=force -v.\nstdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    assert "test_param.py" in combined, (
        f"D-02 violated: pytest-native nodeid 'test_param.py' missing.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )
    # Reporter additions:
    assert "MCP Test Framework" in combined, (
        f"Reporter banner missing under additive-coexistence verification.\n"
        f"stdout=\n{res.stdout}\n"
        f"stderr=\n{res.stderr}"
    )


def test_force_emits_per_tool_rows_and_summary(tmp_path: Path) -> None:
    """Force mode emits per-tool rows + Result: summary line.

    The parametrized payload produces ``[mytool]`` (PASS) and ``[othertool]``
    (FAIL) nodeids. Both should appear in the rendered per-tool rows.
    """
    _write_payload_with_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "--mcp-domain-ui=force")
    combined = res.stdout + res.stderr
    assert "Result:" in combined, (
        f"'Result:' summary line missing.\n"
        f"stdout=\n{res.stdout}\nstderr=\n{res.stderr}"
    )
    assert "mytool" in combined, (
        f"per-tool row for 'mytool' missing.\n"
        f"stdout=\n{res.stdout}\nstderr=\n{res.stderr}"
    )
    assert "othertool" in combined, (
        f"per-tool row for 'othertool' (FAIL) missing.\n"
        f"stdout=\n{res.stdout}\nstderr=\n{res.stderr}"
    )


def test_xdist_master_only_emission(tmp_path: Path) -> None:
    """Optional smoke test: under -n 2, the header banner emits exactly once.

    Validates Assumption A3 (controller-side ordering of sessionfinish
    relative to worker-forwarded logreport events) and the worker no-op
    contract (workers must not duplicate the banner).
    """
    import pytest  # local import so this test can skip without xdist

    pytest.importorskip("xdist")

    _write_payload_with_config(tmp_path)
    res = _run_pytest(tmp_path, "tests/", "-n", "2", "--mcp-domain-ui=force")
    combined = res.stdout + res.stderr
    banner_count = combined.count("MCP Test Framework")
    assert banner_count == 1, (
        f"Banner should emit exactly once under -n 2 (controller only); "
        f"got count={banner_count}.\n"
        f"stdout=\n{res.stdout}\nstderr=\n{res.stderr}"
    )
