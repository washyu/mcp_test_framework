"""Regression test for SHIM-06: warn-on-presence detector fires when
tests/sdet/ contains live test_*.py files; silent when empty/absent."""
from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]


def test_warns_when_tests_sdet_contains_live_tests(
    pytester: pytest.Pytester,
) -> None:
    """SHIM-06: a tests/sdet/test_*.py file under the rootpath triggers
    a DeprecationWarning naming tests/test_code/ as the new location."""
    # Synthesize the legacy directory with a live test file.
    legacy = pytester.path / "tests" / "sdet"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    # The plugin auto-loads via the project's pytest11 entry point, so no
    # explicit `-p mcp_test_framework._plugin` is needed (and doing so under
    # the entry-point load triggers a "Plugin already registered" conflict).
    pytester.makefile(
        ".toml",
        pyproject=(
            "[tool.pytest.ini_options]\n"
            'addopts = "-W default"\n'
        ),
    )
    # Provide a no-op test under tests/test_code/ so pytest has something
    # to collect (otherwise the run errors with "no tests ran"). The
    # tests/ directory was already created above by pytester.mkdir; use
    # pathlib's parents=True+exist_ok=True for idempotent re-creation.
    (pytester.path / "tests" / "test_code").mkdir(parents=True, exist_ok=True)
    (pytester.path / "tests" / "test_code" / "test_y.py").write_text(
        "def test_y(): pass\n", encoding="utf-8"
    )
    result = pytester.runpytest_subprocess("-W", "always::DeprecationWarning")
    combined = "\n".join(result.outlines + result.errlines)
    assert "tests/sdet/ is no longer auto-discovered as of v1.5" in combined, combined
    assert "tests/test_code/" in combined, combined
    assert "next:" in combined, combined
    # NOTE: the `[mcp-contracts]` prefix is rendered by the plugin's
    # scoped `_mcptf_formatwarning` swap, but pytest captures
    # `WarningMessage` objects via `warnings.catch_warnings()` and re-
    # renders them with its own summary formatter -- the prefix bytes
    # never reach the subprocess's stdout/stderr. The ERROR-STYLE
    # registry pin in test_error_style.py asserts the prefix's presence
    # in the plugin source instead.


def test_no_warn_when_tests_sdet_absent(
    pytester: pytest.Pytester,
) -> None:
    """SHIM-06: clean tree (no tests/sdet/ directory) fires no warning."""
    # The plugin auto-loads via the project's pytest11 entry point, so no
    # explicit `-p mcp_test_framework._plugin` is needed (and doing so under
    # the entry-point load triggers a "Plugin already registered" conflict).
    pytester.makefile(
        ".toml",
        pyproject=(
            "[tool.pytest.ini_options]\n"
            'addopts = "-W default"\n'
        ),
    )
    # Provide a tests/test_code/ tree so pytest has something to collect.
    (pytester.path / "tests" / "test_code").mkdir(parents=True, exist_ok=True)
    (pytester.path / "tests" / "test_code" / "test_y.py").write_text(
        "def test_y(): pass\n", encoding="utf-8"
    )
    result = pytester.runpytest_subprocess("-W", "always::DeprecationWarning")
    combined = "\n".join(result.outlines + result.errlines)
    # Detector must be silent on clean trees -- no false-positive noise.
    assert "tests/sdet/ is no longer auto-discovered" not in combined, combined


def test_no_warn_when_tests_sdet_has_no_test_files(
    pytester: pytest.Pytester,
) -> None:
    """SHIM-06: tests/sdet/ exists but contains only non-test files
    (e.g. _generated/ scaffolds) -- detector must be silent."""
    legacy = pytester.path / "tests" / "sdet"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "README.md").write_text("legacy directory\n", encoding="utf-8")
    (legacy / "_generated").mkdir()
    (legacy / "_generated" / "scaffold.py").write_text(
        "# not a test file\n", encoding="utf-8"
    )
    # The plugin auto-loads via the project's pytest11 entry point, so no
    # explicit `-p mcp_test_framework._plugin` is needed (and doing so under
    # the entry-point load triggers a "Plugin already registered" conflict).
    pytester.makefile(
        ".toml",
        pyproject=(
            "[tool.pytest.ini_options]\n"
            'addopts = "-W default"\n'
        ),
    )
    (pytester.path / "tests" / "test_code").mkdir(parents=True, exist_ok=True)
    (pytester.path / "tests" / "test_code" / "test_y.py").write_text(
        "def test_y(): pass\n", encoding="utf-8"
    )
    result = pytester.runpytest_subprocess("-W", "always::DeprecationWarning")
    combined = "\n".join(result.outlines + result.errlines)
    assert "tests/sdet/ is no longer auto-discovered" not in combined, combined
