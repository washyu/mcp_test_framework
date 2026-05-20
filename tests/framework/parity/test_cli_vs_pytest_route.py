"""Phase 30 CLOSE-02: CLI vs pytest-route JUnit XML equivalence gate.

This is the only new production-shape test in Phase 30. It drives BOTH
the CLI Typer entry (`mcp-contracts run`) and raw pytest (`pytest -o
"mcp_config_file=..."`) against the same `config.test.yaml` substrate and
asserts the two JUnit XML outputs produce identical `{nodeid: outcome}` dicts.

Design contract (locked in Phase 30 CONTEXT.md):
- D-01: Equivalence is dict equality on `{nodeid: outcome}` (outcome enum:
        passed | failed | skipped | error). Stricter than counts-only;
        looser than deep-tree equality (tolerates timestamps, durations,
        hostnames, ordering, message-text wording drift).
- D-02: Config substrate is `./config.test.yaml` (same config Phase 27 D-06
        framework dogfood already uses). Zero new fixture infrastructure.
- D-02a: `config.test.yaml` ships with `tools: {}` (Phase 27 D-13/D-16
        intentional empty allowlist). Under that substrate the parity
        comparison is vacuous. The defensive `assert outcomes_a` at the
        top of the comparison block catches the empty case and tells the
        operator to populate `tools:` in `config.test.yaml` before running
        this gate locally. See `docs/LIBRARY-MODE.md` § "Running the parity
        gate locally" for the populate-tools requirement.
- D-03: Two subprocesses, NOT in-process `CliRunner` + `pytester.runpytest`.
        The CLI's subprocess boundary is what operators actually invoke;
        the parity test exercises the same boundary in the same way.

Recursion guard: This test carries `pytest.mark.parity`. Both inner
subprocesses pass `-m "not parity"` so the inner pytest sessions do not
re-collect this test inside themselves (would cause infinite recursion).

Default-skipped: This test additionally carries `pytest.mark.live_homelab`
and `pytest.mark.live_ollama`. The pyproject `addopts = "-m 'not
live_homelab and not live_ollama'"` deselects them by default. Operator
opts in explicitly via `pytest -m "parity and live_homelab and live_ollama"
tests/framework/parity/`.
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.parity,         # D-03 recursion guard — inner subprocesses pass -m "not parity"
    pytest.mark.live_homelab,   # skip-gate (deselected by default via pyproject addopts)
    pytest.mark.live_ollama,
]


def _parse_outcomes(xml_path: Path) -> dict[str, str]:
    """Walk pytest JUnit XML → ``{nodeid: outcome}``.

    Outcome enum: ``passed | failed | skipped | error``.
    Nodeid reconstructed from ``<testcase classname="..." name="...">`` per
    pytest's JUnit XML encoding (classname is the dotted file/class path,
    name is the function — joined with ``::``).

    Any-fail-wins for outcome priority when a single testcase carries
    multiple children: ``failure > error > skipped > passed``.

    Local walker (NOT reusing ``_runner.parse_junit_xml`` which returns
    ``ParsedRun`` aggregated per-tool, NOT per-nodeid — D-01 specifies
    per-nodeid). See Phase 30 RESEARCH §"JUnit parsing trade-off".
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    if suite is None:
        return {}
    PRIORITY: dict[str, int] = {"failed": 0, "error": 1, "skipped": 2, "passed": 3}
    out: dict[str, str] = {}
    for tc in suite.iter("testcase"):
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        nodeid = f"{classname}::{name}" if classname else name
        if tc.find("failure") is not None:
            outcome = "failed"
        elif tc.find("error") is not None:
            outcome = "error"
        elif tc.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "passed"
        # any-fail-wins: only update if new outcome has strictly higher priority
        if nodeid not in out or PRIORITY[outcome] < PRIORITY[out[nodeid]]:
            out[nodeid] = outcome
    return out


def test_cli_route_equals_pytest_route(tmp_path: Path) -> None:
    """CLOSE-02: `mcp-contracts run --config X` and `pytest -o mcp_config_file=X`
    produce identical `{nodeid: outcome}` dicts under JUnit XML round-trip.
    """
    repo_root = Path(__file__).resolve().parents[3]  # parity → framework → tests → repo_root
    xml_a = tmp_path / "route_a_cli.xml"
    xml_b = tmp_path / "route_b_pytest.xml"

    # Route A — CLI Typer entry → internally subprocesses pytest (Phase 27 D-11)
    proc_a = subprocess.run(
        [
            sys.executable, "-m", "mcp_test_framework.cli", "run",
            "--config", "config.test.yaml",
            f"--junit-xml={xml_a}",
            "--", "-m", "not parity and not live_homelab and not live_ollama",
        ],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )

    # Route B — raw pytest with ini override
    proc_b = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "-o", "mcp_config_file=./config.test.yaml",
            f"--junitxml={xml_b}",
            "-m", "not parity and not live_homelab and not live_ollama",
            "tests/contract",   # match Route A scope
        ],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )

    # Both routes MUST produce XML — missing XML signals the subprocess died before --junitxml fired
    assert xml_a.exists(), (
        f"Route A (CLI) produced no JUnit XML at {xml_a}.\n"
        f"returncode: {proc_a.returncode}\n"
        f"stdout:\n{proc_a.stdout}\n"
        f"stderr:\n{proc_a.stderr}"
    )
    assert xml_b.exists(), (
        f"Route B (pytest) produced no JUnit XML at {xml_b}.\n"
        f"returncode: {proc_b.returncode}\n"
        f"stdout:\n{proc_b.stdout}\n"
        f"stderr:\n{proc_b.stderr}"
    )

    outcomes_a = _parse_outcomes(xml_a)
    outcomes_b = _parse_outcomes(xml_b)

    # D-02a defensive non-vacuous assert. config.test.yaml ships with
    # `tools: {}` by Phase 27 D-13/D-16 design (framework CI exercises plugin
    # wiring without requiring uvx homelab-mcp to launch). Under that
    # substrate both routes produce empty outcome dicts and the equality
    # assert below would trivially pass — vacuous PASS. Populate `tools:`
    # in config.test.yaml (or point at another config) before running this
    # gate locally. See `docs/LIBRARY-MODE.md` § "Running the parity gate".
    assert outcomes_a, (
        "Parity test ran against an empty outcomes dict — Route A produced "
        "zero `<testcase>` entries in its JUnit XML. This usually means "
        "`./config.test.yaml` ships with `tools: {}` (Phase 27 D-13/D-16 "
        "intentional empty allowlist for CI plugin-wiring exercise). "
        "Populate `tools:` in `./config.test.yaml` or run against a config "
        "with at least one enabled tool before invoking the parity gate.\n"
        f"Route A returncode: {proc_a.returncode}\n"
        f"Route A stdout (tail):\n{proc_a.stdout[-2000:]}"
    )

    assert outcomes_b, (
        "Parity test ran against an empty outcomes dict — Route B produced "
        "zero `<testcase>` entries in its JUnit XML. This may mean the "
        "`mcp_config_file` ini override did not resolve correctly, or the "
        "`tests/contract` scope collected no tests. Verify the `-o "
        "`mcp_config_file=` argument and that the contract test suite is "
        "populated before invoking the parity gate.\n"
        f"Route B returncode: {proc_b.returncode}\n"
        f"Route B stdout (tail):\n{proc_b.stdout[-2000:]}"
    )
    assert outcomes_a == outcomes_b, (
        "CLI vs pytest-route outcome divergence (CLOSE-02 parity broken).\n"
        f"Only in Route A: {set(outcomes_a) - set(outcomes_b)}\n"
        f"Only in Route B: {set(outcomes_b) - set(outcomes_a)}\n"
        f"Differing outcomes: "
        f"{ {k: (outcomes_a.get(k), outcomes_b.get(k)) for k in outcomes_a if outcomes_a.get(k) != outcomes_b.get(k)} }\n"
        f"Route A returncode: {proc_a.returncode}\n"
        f"Route B returncode: {proc_b.returncode}\n"
    )
