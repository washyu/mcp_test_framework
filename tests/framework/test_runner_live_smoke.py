"""Phase 14 Plan 05: live-homelab integration smoke for the new wrapper.

Replaces tests/test_reporter.py's live half (the unit half was wholly
subsumed by tests/test_runner_*.py from Plans 02-04). Asserts that:
  - `mcp-test-framework run` against a real homelab-mcp produces the
    new domain UI (header strings + summary line).
  - `--junit-xml=PATH` still writes a valid JUnit XML at PATH (RUNNER-05).
  - `--raw` still produces pytest's native output.

Skipped by default via the @pytest.mark.live_homelab marker
(pyproject.toml's `addopts = "-m 'not live_homelab and not live_ollama'"`).
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


pytestmark = pytest.mark.live_homelab


def _run_framework_subprocess(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "mcp-test-framework", "run", *args],
        cwd=cwd, capture_output=True, text=True, check=False,
    )


def test_live_run_emits_domain_header_and_summary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = _run_framework_subprocess(cwd=repo_root)
    # Header strings appear.
    assert "MCP Test Framework" in proc.stdout
    assert "MCP server:" in proc.stdout
    assert "Discovered:" in proc.stdout
    assert "Running:" in proc.stdout
    # Summary line appears.
    assert "Result:" in proc.stdout
    # No pytest framing.
    assert "test session starts" not in proc.stdout


def test_live_run_junit_xml_path_preserved(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    target = tmp_path / "live.xml"
    proc = _run_framework_subprocess(f"--junit-xml={target}", cwd=repo_root)
    assert target.exists(), f"--junit-xml=PATH did not populate {target}: {proc.stdout}"
    tree = ET.parse(target)
    root = tree.getroot()
    assert root.tag in {"testsuites", "testsuite"}


def test_live_run_raw_produces_pytest_framing() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = _run_framework_subprocess("--raw", cwd=repo_root)
    # --raw passes pytest's output through; framing IS expected.
    assert "test session starts" in proc.stdout or "test session starts" in (proc.stderr or "")
