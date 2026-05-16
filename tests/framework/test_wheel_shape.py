"""PACK-04: wheel-content regression gate.

Builds the project wheel into a tmp dir via `uv build --wheel`, then walks
the resulting .whl (which is a zip) to assert the Phase 26 invariants:

  - mcp_test_framework/py.typed present (root PEP 561 marker)
  - mcp_test_framework/test_code/py.typed present (subpackage PEP 561 marker)
  - mcp_test_framework/contracts/__init__.py present (subpackage stub)
  - mcp_test_framework/contracts/py.typed present (subpackage PEP 561 marker)
  - mcp_test_framework/_plugin.py present (pytest11 entry-point target)
  - mcp_test_framework/_deprecated_script.py present (console-script shim)
  - No `tests/` directory leakage into the wheel
  - dist-info entry_points.txt declares the pytest11 plugin entry
  - dist-info entry_points.txt declares BOTH `mcp-contracts` and
    `mcp-test-framework` console scripts (D-05/D-06)

Hatchling auto-includes non-`.py` files (including PEP 561 markers) under
`packages = ["src/mcp_test_framework"]` (RESEARCH.md key finding); this
test verifies the maintainer-confirmed behavior holds for our layout.

Performance: the wheel build takes 3-8s cold. The fixture is module-scoped
so the build runs once for all assertions.
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the project wheel into a tmp dir; return the wheel path.

    Skipped (not failed) when `uv` is not on PATH so contributors in
    non-uv environments can still run the rest of the framework's tests.
    """
    if shutil.which("uv") is None:
        pytest.skip("uv not on PATH; cannot build wheel for introspection")
    out_dir = tmp_path_factory.mktemp("wheel_build")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"uv build failed (exit {result.returncode}):\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return wheels[0]


def _wheel_names(wheel_path: Path) -> set[str]:
    with zipfile.ZipFile(wheel_path) as zf:
        return set(zf.namelist())


def _entry_points_txt(wheel_path: Path) -> str:
    with zipfile.ZipFile(wheel_path) as zf:
        ep_path = next(
            (n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")),
            None,
        )
        assert ep_path is not None, "wheel is missing dist-info/entry_points.txt"
        return zf.read(ep_path).decode("utf-8")


def test_wheel_filename_uses_new_dist_name(built_wheel: Path) -> None:
    """Wheel filename normalizes the dist name (`mcp-contracts` -> `mcp_contracts`)."""
    # PEP 427: wheel filename is `{name}-{version}-...whl` with name-normalized.
    assert built_wheel.name.startswith("mcp_contracts-"), (
        f"wheel filename should start with `mcp_contracts-`, got {built_wheel.name}"
    )
    assert "mvp_test_framework" not in built_wheel.name, (
        f"legacy dist name leaked into wheel filename: {built_wheel.name}"
    )


def test_wheel_ships_root_py_typed(built_wheel: Path) -> None:
    assert "mcp_test_framework/py.typed" in _wheel_names(built_wheel)


def test_wheel_ships_test_code_py_typed(built_wheel: Path) -> None:
    assert "mcp_test_framework/test_code/py.typed" in _wheel_names(built_wheel)


def test_wheel_ships_contracts_subpackage(built_wheel: Path) -> None:
    names = _wheel_names(built_wheel)
    assert "mcp_test_framework/contracts/__init__.py" in names
    assert "mcp_test_framework/contracts/py.typed" in names


def test_wheel_ships_plugin_module(built_wheel: Path) -> None:
    """pytest11 entry-point target must be present in the wheel."""
    assert "mcp_test_framework/_plugin.py" in _wheel_names(built_wheel)


def test_wheel_ships_deprecated_script_module(built_wheel: Path) -> None:
    """Console-script shim target must be present in the wheel (D-06)."""
    assert "mcp_test_framework/_deprecated_script.py" in _wheel_names(built_wheel)


def test_wheel_excludes_tests_directory(built_wheel: Path) -> None:
    """No accidental `tests/` leakage -- PACK-04 explicit invariant."""
    names = _wheel_names(built_wheel)
    leaks = sorted(n for n in names if n.startswith("tests/"))
    assert leaks == [], f"tests/ leaked into wheel: {leaks}"


def test_wheel_declares_pytest11_entry_point(built_wheel: Path) -> None:
    """PACK-01 / SC2: [pytest11] mcp_test_framework = mcp_test_framework._plugin."""
    ep_txt = _entry_points_txt(built_wheel)
    assert "[pytest11]" in ep_txt
    assert "mcp_test_framework = mcp_test_framework._plugin" in ep_txt


def test_wheel_declares_primary_console_script(built_wheel: Path) -> None:
    """D-05: `mcp-contracts` is the primary console-script."""
    ep_txt = _entry_points_txt(built_wheel)
    assert "mcp-contracts = mcp_test_framework.cli:app" in ep_txt


def test_wheel_declares_legacy_console_script_shim(built_wheel: Path) -> None:
    """D-06: `mcp-test-framework` is retained as a deprecation shim in v1.4."""
    ep_txt = _entry_points_txt(built_wheel)
    assert (
        "mcp-test-framework = mcp_test_framework._deprecated_script:main" in ep_txt
    )


def test_wheel_source_has_no_homelab_mcp_imports(built_wheel: Path) -> None:
    """Framework-primitives principle: NO SUT-aware logic in the wheel.

    Scans every .py source file inside the wheel for actual import
    statements (`import homelab_mcp` or `from homelab_mcp ...`) -- must
    return zero matches. This catches both accidental imports and the
    case where the existing ruff banned-imports table is silenced.

    Line-prefix check (not substring) so docstrings/comments that mention
    the principle by name don't false-positive.
    """
    with zipfile.ZipFile(built_wheel) as zf:
        py_sources = [n for n in zf.namelist() if n.endswith(".py")]
        for source in py_sources:
            text = zf.read(source).decode("utf-8", errors="replace")
            for line in text.splitlines():
                stripped = line.strip()
                if (
                    stripped.startswith("import homelab_mcp")
                    or stripped.startswith("from homelab_mcp ")
                    or stripped.startswith("from homelab_mcp.")
                ):
                    pytest.fail(
                        f"framework-primitives violation: `{stripped}` in {source}"
                    )
