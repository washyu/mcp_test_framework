"""Smoke tests proving the project's ruff TID251 banned-api rule actually fires.

Plan 01-01 declared the rule in pyproject.toml. This module proves the rule is
wired by invoking ruff against deliberately-violating fixture files written
under pytest's tmp_path, and asserting ruff exits non-zero with TID251 in its
output. Without these tests, the rule could be silently disabled or removed
and the entire SETUP-03 black-box enforcement story would rot undetected.

The third test documents the historical submodule-import gap (ruff issue
#1614, RESEARCH Pitfall 4): older ruff versions did NOT catch
`from homelab_mcp.client import X` via a single banned-api entry. Newer ruff
versions (0.15.x verified 2026-05-04 against this codebase) DO catch it.
The test passes either way -- it xfails if ruff misses, passes if ruff
catches. The runtime sys.modules guard in tests/conftest.py is the
belt-and-suspenders that closes the gap regardless of ruff version.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# tests/unit/test_banned_imports.py is two levels under the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_FIXTURE = _REPO_ROOT / "tests" / "_fixtures" / "banned_import_should_fail.py.txt"


def _run_ruff_against(target: Path) -> subprocess.CompletedProcess[str]:
    """Invoke ruff via uv run against `target`, pinned to this repo's pyproject.toml.

    The --no-cache flag prevents stale results from a prior in-test invocation.
    The --config flag pins the configuration to this project's pyproject.toml,
    so a developer's `~/.config/ruff/ruff.toml` cannot interfere with the test.
    """
    return subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(_PYPROJECT),
            str(target),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )


def _output(result: subprocess.CompletedProcess[str]) -> str:
    """Concatenate stdout+stderr for substring assertions."""
    return (result.stdout or "") + (result.stderr or "")


def test_ruff_tid251_fires_on_top_level_import(tmp_path: Path) -> None:
    """`import homelab_mcp` MUST fail ruff (TID251 banned-api).

    Uses the canonical fixture file at tests/_fixtures/banned_import_should_fail.py.txt
    (named .py.txt so it isn't picked up by the repo-wide `ruff check src tests`).
    """
    assert _FIXTURE.is_file(), f"fixture missing: {_FIXTURE}"
    target = tmp_path / "banned.py"
    target.write_text(_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    result = _run_ruff_against(target)
    out = _output(result)

    assert result.returncode != 0, (
        f"ruff was expected to fail on `import homelab_mcp` but exited 0. "
        f"output:\n{out}"
    )
    assert "TID251" in out or "homelab_mcp" in out, (
        f"ruff output did not mention TID251 or homelab_mcp.\n{out}"
    )


def test_ruff_tid251_fires_on_from_import(tmp_path: Path) -> None:
    """`from homelab_mcp import x` MUST fail ruff (TID251 banned-api).

    Inline content; no separate fixture file needed for this case.
    """
    target = tmp_path / "banned_from.py"
    target.write_text("from homelab_mcp import something\n", encoding="utf-8")

    result = _run_ruff_against(target)
    out = _output(result)

    assert result.returncode != 0, (
        f"ruff was expected to fail on `from homelab_mcp import x` "
        f"but exited 0. output:\n{out}"
    )
    assert "TID251" in out or "homelab_mcp" in out, (
        f"ruff output did not mention TID251 or homelab_mcp.\n{out}"
    )


def test_ruff_tid251_misses_submodule_import_documented_gap(tmp_path: Path) -> None:
    """Document the historical submodule-import gap.

    Older ruff versions did not catch `from homelab_mcp.client import X` via a
    single banned-api entry (ruff issue #1614, RESEARCH Pitfall 4). If ruff
    catches it now, this test simply passes -- the submodule gap has been
    closed at the lint layer. If ruff misses it, this test xfails with a
    pointer to the runtime sys.modules guard in tests/conftest.py that
    closes the gap regardless.
    """
    target = tmp_path / "banned_submodule.py"
    target.write_text("from homelab_mcp.client import x\n", encoding="utf-8")

    result = _run_ruff_against(target)
    out = _output(result)

    if result.returncode == 0:
        pytest.xfail(
            "Known gap: TID251 does not cover submodule imports. "
            "Covered at runtime by tests/conftest.py sys.modules guard. "
            "See 01-RESEARCH Pitfall 4 / ruff issue #1614."
        )

    # ruff caught it -- assert it was specifically TID251 (or at least mentions
    # the banned package), not some unrelated lint failure.
    assert "TID251" in out or "homelab_mcp" in out, (
        f"ruff failed but output does not mention TID251 or homelab_mcp.\n{out}"
    )
