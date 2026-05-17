# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite - Research

**Researched:** 2026-05-17
**Domain:** Closeout phase — JUnit XML equivalence test + multi-file docs rewrite + UAT capture protocols
**Confidence:** HIGH (all decisions D-01..D-03 locked; primary unknowns are configuration-substrate facts verifiable in repo)

## Summary

Phase 30 is the v1.4 close. Three of the four threads are mechanically straightforward (dogfood verification re-run, REQUIREMENTS.md amendment, doc rewrites). The one piece of new production-shaped test code — the CLI/library parity test — is fully constrained by `<decisions>` D-01..D-03. Research focused on validating the executable shape of that test against the real codebase: (a) JUnit XML schema and outcome mapping, (b) the framework's existing skip-when-stack-down patterns, (c) cross-platform subprocess invocation on Windows, and (d) marker recursion guard composability.

**Three findings the planner must internalize before writing plans:**

1. **`config.test.yaml` has `tools: {}` — the framework's dogfood config produces ZERO injected contract tests.** [VERIFIED: read of config.test.yaml] This is a deliberate Phase 27 D-06 design choice (the empty allowlist exercises plugin-load wiring without requiring `uvx homelab-mcp` to launch). For the parity test, this means SC2's "same pass/fail signal" reduces to "both routes produce the same empty `{nodeid: outcome}` dict" against `config.test.yaml`. That still asserts the substantive parity property (same collection, same outcomes) but it is **NOT what D-02 in CONTEXT.md describes** ("live homelab-mcp"). The planner must resolve this gap — see Open Questions §1.

2. **The framework's `tests/framework/conftest.py` is a Config-stub shim, NOT a skip-when-down gateway.** [VERIFIED: read of tests/framework/conftest.py] No autouse skip-when-down fixture exists at the framework-self-test scope; live-stack tests gate themselves via the module-level `pytestmark = pytest.mark.live_homelab` marker combined with the pyproject `addopts = "-m 'not live_homelab and not live_ollama'"` default. The parity test should adopt **the same `live_homelab` + `live_ollama` marker pair** rather than inventing a new skip-when-down probe. Operators opt in via `-m live_homelab`.

3. **The existing live-smoke pattern is `subprocess.run(["uv", "run", "mcp-test-framework", "run", ...])` with `cwd=repo_root`.** [VERIFIED: read of tests/framework/test_runner_live_smoke.py:25-29] This is the closest existing pattern. The parity test's subprocess shape diverges only in (a) using `mcp-contracts` instead of the deprecated `mcp-test-framework` alias and (b) running TWO subprocesses instead of one. CONTEXT.md Claude's-discretion default `[sys.executable, "-m", "mcp_test_framework.cli", "run", ...]` is also viable; recommendation below.

**Primary recommendation:** Treat the parity test as a `live_homelab + live_ollama`-marked, opt-in test that runs both Route A and Route B in subprocesses with `cwd=repo_root` and `capture_output=True, check=False`. Parse both JUnit XMLs with a local 30-line `xml.etree.ElementTree` walker (do not reuse `_runner.parse_junit_xml` — it returns `ParsedRun`, which is per-tool aggregated, NOT per-nodeid). Assert dict equality on `{nodeid: outcome}`. Resolve the `config.test.yaml`-empty-tools gap (Open Question §1) before writing plans.

## Project Constraints (from CLAUDE.md)

- **Python 3.14** (pinned `.python-version`, `requires-python>=3.14` in `pyproject.toml`).
- **`uv` for dependency management.** Test invocations may use `uv run` or `sys.executable -m`; both shapes are precedented in this repo.
- **pytest 9** + **pytest-asyncio strict mode** + `asyncio_default_fixture_loop_scope = "session"`.
- **Stdio-only MCP transport.** `mcp.client.stdio.stdio_client` context manager. NO `subprocess.Popen` against the SUT directly. (The parity test invokes pytest/CLI subprocesses, NOT the MCP server — this constraint applies to plugin internals, not test invocation.)
- **Framework treats `homelab-mcp` as a black box.** Never import or read its source. [enforced by `_black_box_guard.py` + ruff TID rules]
- **No emojis** in code or docs unless explicitly requested by user.
- **All commands cross-platform-safe; Windows-first dev environment.**

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLOSE-01 | (STALE — see <downstream_impact>) Framework's `pyproject.toml` already sets `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` (Phase 27 D-06 landed); Phase 30 verifies the dogfood loop is still green at v1.4 close. CLI-mode path continues to subprocess pytest with JUnit XML round-trip. | §"Dogfood verification execution shape" — re-run command + assertion + STATE/VERIFICATION note |
| CLOSE-02 | Operator running `mcp-contracts run --config PATH` sees identical pass/fail signal to operator running `pytest` against the same `[tool.pytest.ini_options] mcp_config_file = PATH` — CLI/library parity gated by a CI test driving both routes against the same fixture config and asserting equivalent JUnit XML output. | §"Parity test design" — D-01 dict equality, D-02 reuse config.test.yaml (with Open Q §1 caveat), D-03 two subprocesses + outer marker exclusion |
| CLOSE-03 | (STALE — see <downstream_impact>) New operator reading the README sees library-mode usage first; CLI usage demotes to an "Appendix: CLI usage" section; `docs/LIBRARY-MODE.md` is the primary reference document for the library API surface. | §"README rewrite — operator-onboarding-first structure" and §"`docs/LIBRARY-MODE.md` outline" |
| CLOSE-04 | Carry-forward live-UAT items from v1.2/v1.3 close as part of the library-mode dogfood pass: (a) README test-code-scenarios PASS-sample re-capture, (b) Phase 17 SC1 live-stack at ~70 tools, (c) v1.2 Phase 13 v2-config UAT, (d) v1.2 Phase 14 live-stack UAT under both CLI + library modes. | §"Live-UAT capture protocol shape" — four sections with paste-evidence blocks |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parity test execution | Framework self-test (tests/framework/) | — | Validates CLI ↔ library equivalence; not a contract test against an SUT |
| JUnit XML parsing | Framework self-test (local helper) | _runner.py (existing parse_junit_xml — NOT reused; see §"JUnit parsing trade-off") | parity test needs `{nodeid: outcome}` per-test, not `ParsedRun` per-tool aggregation |
| Subprocess invocation (Route A) | CLI subprocess (Typer entry) | — | Honors operator-boundary fidelity (D-03) |
| Subprocess invocation (Route B) | Pytest subprocess via `-o` override | — | Honors operator-boundary fidelity (D-03); CLI internally does the same (Phase 27 D-11) |
| Recursion guard | Marker registration in `tests/framework/conftest.py` | — | Framework-internal scope; not part of operator-facing plugin surface |
| Skip-when-stack-down | `@pytest.mark.live_homelab` + `@pytest.mark.live_ollama` (pyproject addopts default-deselects) | — | Matches established pattern in `test_runner_live_smoke.py` and `tests/framework/smoke/test_smoke_homelab_mcp.py` |
| Docs rewrite (operator-facing) | README + `docs/LIBRARY-MODE.md` | `docs/EXTENDING.md` (existing, links from README) | New top-of-funnel doc for library mode; existing reference docs link inward |
| UAT capture protocols | `30-UAT.md`-shape doc | — | User-driven; framework does NOT assert these (per `feedback_uat_must_be_user_driven`) |

## Standard Stack

### Core (already present; no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | 9.0+ (dev dep) | Test runner — inner subprocess for both routes | Project's locked test surface; required to read JUnit XML output |
| `xml.etree.ElementTree` | stdlib | JUnit XML parse for `{nodeid: outcome}` extraction | Already used by `_runner.py:553 parse_junit_xml`; no new dep [VERIFIED: read of _runner.py] |
| `subprocess` (stdlib) | n/a | Spawn pytest + mcp-contracts subprocesses | Existing pattern at `test_runner_live_smoke.py:25-29` |
| `tempfile.TemporaryDirectory` or pytest `tmp_path` | stdlib / pytest fixture | Per-route junit XML output path | `pytest tmp_path` is the in-repo idiom; matches `test_runner_live_smoke.py:46-48` `tmp_path: Path` parameter |
| `sys.executable` | stdlib | Cross-platform Python interpreter resolution | Standard portable pattern for `[sys.executable, "-m", ...]` |

### Supporting (already present)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `Typer` (transitive via `mcp[cli]`) | CLI surface of `mcp-contracts run` | Route A invokes the Typer entry indirectly via console script or `-m` |
| `pytest-asyncio` (strict mode) | Async test loop wiring | Parity test itself is sync; pytest-asyncio not directly involved |
| `pydantic-settings[yaml]` | Config loader (Phase 27 D-02 ini route) | Read by inner pytest sessions; outer parity test doesn't touch config directly |

**No new dependencies required for Phase 30.** [VERIFIED: pyproject.toml audit]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local 30-line ET walker | `_runner.parse_junit_xml` reuse | Couples parity test to `ParsedRun` shape (per-tool aggregation); changes there ripple here. Locally-parsed `{nodeid: outcome}` keeps parity test independent and matches D-01's exact contract verbatim. **Recommend local walker.** |
| `[sys.executable, "-m", "mcp_test_framework.cli", ...]` | `["uv", "run", "mcp-contracts", ...]` | `sys.executable -m` exercises in-tree source under the running interpreter; `uv run mcp-contracts` exercises the entry-point installation (closer to operator invocation). Both pre-existing patterns in the repo. **Recommend `sys.executable -m` for Route A** to remove the `uv run` resolution variable + match Phase 27 D-11 CLI internals. |
| `@pytest.mark.parity` (new marker) | `@pytest.mark.live_homelab` only | The CONTEXT.md-locked `parity` marker is for **recursion guard** (inner `-m "not parity"`), not for opt-in gating. We need BOTH: `parity` (recursion) AND `live_homelab + live_ollama` (skip-when-stack-down) on the same test. |

**Version verification (already in `pyproject.toml`):**
- `pytest>=9.0` — current [VERIFIED]
- `pytest-asyncio>=1.3` — current [VERIFIED]
- `mcp[cli]>=1.27` — current [VERIFIED]

No `npm view` analog needed; all deps locked in lockfile.

## Architecture Patterns

### System Architecture Diagram (parity test flow)

```
Outer pytest session (tests/framework/parity/test_cli_vs_pytest_route.py)
    │
    ├─ @pytest.mark.parity         ← recursion guard marker (registered in tests/framework/conftest.py)
    ├─ @pytest.mark.live_homelab   ← skip gate (deselected by default via addopts)
    └─ @pytest.mark.live_ollama
            │
            ▼
    test_cli_route_equals_pytest_route(tmp_path):
            │
            ├──► Subprocess A: [sys.executable, -m, mcp_test_framework.cli, run,
            │                   --config, config.test.yaml,
            │                   --junit-xml, tmp_path/a.xml,
            │                   --, -m, "not parity"]
            │       │
            │       └─► Inner CLI subprocess
            │           └─► Pytest subprocess (with -o "mcp_config_file=..." -m "not parity")
            │                   └─► writes tmp_path/a.xml
            │
            ├──► Subprocess B: [sys.executable, -m, pytest,
            │                   -o, "mcp_config_file=./config.test.yaml",
            │                   --junitxml, tmp_path/b.xml,
            │                   -m, "not parity",
            │                   tests/]
            │       │
            │       └─► Inner pytest subprocess
            │               └─► writes tmp_path/b.xml
            │
            ├──► _parse_outcomes(tmp_path/a.xml) → dict[str, str]
            ├──► _parse_outcomes(tmp_path/b.xml) → dict[str, str]
            │
            └──► assert dict_a == dict_b  ← D-01 equivalence definition
```

### Recommended File Structure

```
tests/framework/
├── conftest.py                              # MODIFY: register `parity` marker
└── parity/                                  # NEW: single-file subdir, matches established <area>/ layout
    └── test_cli_vs_pytest_route.py          # NEW: the only new production test

.planning/phases/30-.../
├── 30-CONTEXT.md                            # (exists)
├── 30-RESEARCH.md                           # (this file)
├── 30-UAT.md                                # NEW: capture protocols for 4 carry-forward UATs

docs/
├── LIBRARY-MODE.md                          # NEW: primary library-mode reference
├── EXTENDING.md                             # EXISTS — verify ID-leak scrub already done [VERIFIED: clean]
├── ERROR-STYLE.md                           # EXISTS — link target from LIBRARY-MODE.md error examples
└── TEST-CODE-AUTHORING.md                   # EXISTS — link target from LIBRARY-MODE.md test-code section

README.md                                    # REWRITE: library-mode quickstart at top, CLI demoted to Appendix
config.example.yaml                          # SCRUB-VERIFY: no IDs found [VERIFIED]
.env.example                                 # SCRUB-VERIFY: no IDs found [VERIFIED]
```

### Pattern 1: Two-subprocess parity invocation

**What:** Spawn Route A (CLI Typer entry → pytest subprocess) and Route B (raw pytest with `-o` override) as siblings; compare JUnit XML outputs.

**When to use:** D-03 locked — any test asserting CLI/library equivalence at the operator boundary.

**Example:**
```python
# tests/framework/parity/test_cli_vs_pytest_route.py
"""CLI vs pytest-route JUnit XML equivalence — Phase 30 CLOSE-02 gate."""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.parity,         # recursion guard — outer subprocesses pass -m "not parity"
    pytest.mark.live_homelab,   # opt-in gate — skipped under default addopts
    pytest.mark.live_ollama,
]


def _parse_outcomes(xml_path: Path) -> dict[str, str]:
    """Walk pytest JUnit XML → {nodeid: outcome}.

    Outcome enum: passed | failed | skipped | error.
    Nodeid reconstructed from <testcase classname="..." name="..."> per pytest's
    encoding convention (classname is the dotted file/class path, name is the
    function — joined with `::`).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    out: dict[str, str] = {}
    for tc in suite.iter("testcase"):
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        nodeid = f"{classname}::{name}" if classname else name
        # any-fail-wins per child element: failure > error > skipped > passed
        if tc.find("failure") is not None:
            out[nodeid] = "failed"
        elif tc.find("error") is not None:
            out[nodeid] = "error"
        elif tc.find("skipped") is not None:
            out[nodeid] = "skipped"
        else:
            out[nodeid] = "passed"
    return out


def test_cli_route_equals_pytest_route(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    xml_a = tmp_path / "route_a_cli.xml"
    xml_b = tmp_path / "route_b_pytest.xml"

    # Route A — CLI Typer entry → internally subprocesses pytest
    proc_a = subprocess.run(
        [sys.executable, "-m", "mcp_test_framework.cli", "run",
         "--config", "config.test.yaml",
         f"--junit-xml={xml_a}",
         "--", "-m", "not parity"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )

    # Route B — raw pytest with ini override
    proc_b = subprocess.run(
        [sys.executable, "-m", "pytest",
         "-o", "mcp_config_file=./config.test.yaml",
         f"--junitxml={xml_b}",
         "-m", "not parity",
         "tests/"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )

    # Both routes MUST produce XML — empty XML signals neither route ran tests
    assert xml_a.exists(), f"Route A produced no XML.\nstdout:\n{proc_a.stdout}\nstderr:\n{proc_a.stderr}"
    assert xml_b.exists(), f"Route B produced no XML.\nstdout:\n{proc_b.stdout}\nstderr:\n{proc_b.stderr}"

    outcomes_a = _parse_outcomes(xml_a)
    outcomes_b = _parse_outcomes(xml_b)

    assert outcomes_a == outcomes_b, (
        f"CLI vs pytest-route outcome divergence.\n"
        f"Only in Route A: {set(outcomes_a) - set(outcomes_b)}\n"
        f"Only in Route B: {set(outcomes_b) - set(outcomes_a)}\n"
        f"Differing outcomes: "
        f"{ {k: (outcomes_a.get(k), outcomes_b.get(k)) for k in outcomes_a if outcomes_a.get(k) != outcomes_b.get(k)} }"
    )
```
Source: composed from precedented patterns in `tests/framework/test_runner_live_smoke.py` and `tests/framework/test_phase27_spike_synthetic_module.py`; verified against pytest JUnit XML schema documented at https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files [CITED].

### Pattern 2: Marker registration in framework conftest

**What:** Register a marker in `tests/framework/conftest.py` via `markers = [...]` in pyproject is not granular enough — the marker should live at framework-self-test scope (NOT operator-facing). Use `pytest_configure(config)` in `tests/framework/conftest.py`.

**When to use:** Any framework-internal marker that should NOT leak to operators (CONTEXT.md `<decisions>` Claude's Discretion default).

**Example:**
```python
# tests/framework/conftest.py (additive — keep existing _TEST_CODE_STUB fixture)
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "parity: marks parity-route equivalence test "
        "(excluded from inner subprocess runs via -m 'not parity')",
    )
```

**Alternative — register in `pyproject.toml`:** The two existing markers (`live_homelab`, `live_ollama`) live in `pyproject.toml` `[tool.pytest.ini_options] markers`. Adding `parity` there would expose it on operator-facing `pytest --markers` output. The framework-conftest scope is **strictly preferred** per CONTEXT.md.

### Pattern 3: Skip-when-stack-down via existing `live_*` markers (no new probe needed)

**What:** Adopt the existing `pytestmark = pytest.mark.live_homelab` pattern. The pyproject `addopts = "-m 'not live_homelab and not live_ollama'"` filters them out by default. Operators running the parity test explicitly opt in with `-m live_homelab` (which deselects everything that's *not* `live_homelab` — note `-m live_homelab` runs ONLY tests with that marker, see Pitfall §1).

**When to use:** Any test that requires the live homelab-mcp stack and/or Ollama. Existing examples: `test_runner_live_smoke.py:22`, `test_smoke_homelab_mcp.py:34-37`.

**Example:** see Pattern 1 above — `pytestmark = [pytest.mark.parity, pytest.mark.live_homelab, pytest.mark.live_ollama]`.

**No autouse-fixture probe needed.** The skip is declarative via marker + addopts. This is a deliberate divergence from CONTEXT.md `<decisions>` Claude's Discretion suggestion of "an autouse fixture that pings the MCP server" — that pattern does NOT exist in the repo today; inventing one for one new test is gratuitous. The marker-based gate is the established idiom.

### Anti-Patterns to Avoid

- **Reusing `_runner.parse_junit_xml`:** Returns `ParsedRun` keyed by per-tool extracted name, NOT by nodeid. D-01 specifies `{nodeid: outcome}` dict — different shape. Reuse couples parity to renderer-internal aggregation; local walker is ~30 LOC and decoupled.
- **`shell=True` on subprocess calls:** Windows path-quoting hazard. All existing repo patterns use list-form argv. Stick with list-form.
- **Keying parity on exit codes:** Pytest exits 0 (all pass), 1 (failures), 2 (usage error), 5 (no tests collected). Two routes can disagree on exit code (e.g., one collects, one doesn't) while still being equivalent under D-01's dict-equality definition. Or vice versa. **Only assert dict equality**, surface stdout/stderr in the diff message for debugging.
- **Inner subprocess inherits outer `addopts`:** When the inner pytest re-reads `pyproject.toml`, it picks up `addopts = "-m 'not live_homelab and not live_ollama'"`. The parity test itself carries `live_homelab` + `live_ollama` markers — but the OUTER session is what selected it. The inner subprocesses must include their own `-m "not parity"` argument; that selector composes safely with the outer `-m 'not live_homelab'` default because pytest takes the conjunction of all `-m` (last-wins for the same flag — verify; if not last-wins, use `-m "not parity and not live_homelab and not live_ollama"` explicitly). See Pitfall §2.
- **Hardcoded `repo_root` via `Path(__file__).parents[N]`:** Brittle to file moves. The `tests/framework/parity/test_cli_vs_pytest_route.py` path is `parents[3]` (parity → framework → tests → repo_root). `test_runner_live_smoke.py` uses `parents[2]` (framework → tests → repo_root). Pattern is established; just count carefully.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JUnit XML schema discovery | Custom schema validator | Read `<testcase>` + child `<failure>/<error>/<skipped>` per pytest's stable contract | Pytest's JUnit shape is documented and stable across 6.x → 9.x [CITED: pytest docs JUnit XML] |
| MCP server liveness probe | Custom socket-ping or in-process `stdio_client.initialize()` | Existing `live_homelab` + `live_ollama` markers + pyproject `addopts` | Established repo pattern; no probe needed |
| TOML parsing (if Phase 30 doc rewrite quotes pyproject.toml ini values) | Manual string parsing | Python 3.14 stdlib `tomllib` | Phase 28 D-13 already adopts `tomllib` for `gen-test-classes`; same standard applies if any plan needs to verify pyproject contents |
| README rewrite "templates" | Custom doc generator | Just edit by hand | One-time rewrite; no reuse expected |
| UAT capture-protocol generator | Custom protocol DSL | Static markdown template per UAT | One-time write; markdown is the deliverable shape |
| Subprocess output text comparison | Custom diff renderer | f-string with set differences + dict-of-tuples for divergent outcomes | Plain Python is sufficient; failure messages are read by humans not parsers |

**Key insight:** The phase has near-zero domain-specific "build it" surface. Three of four threads (CLOSE-01, CLOSE-03, CLOSE-04) are documentation/verification. The one new test (CLOSE-02) is a glorified subprocess-and-xml-diff — the standard library and existing markers cover everything.

## Runtime State Inventory

> **Phase 30 has no rename/refactor/migration surface.** This is a verification-and-documentation phase. The doc rewrite changes operator-facing copy but introduces no new stored data, no new live-service config, no new OS-registered state, no new secrets/env vars, and no new build artifacts. The empty inventory below is verified explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None | — |
| Live service config | None | — |
| OS-registered state | None | — |
| Secrets/env vars | None new. `MCPTF_CONFIG_FILE` deprecation already landed Phase 27 D-09; Phase 30 only documents the deprecation in LIBRARY-MODE.md (no rename, no value change). | — (doc reference only) |
| Build artifacts | None | — |

**Nothing found in any category — verified by reading Phase 27/28/29 CONTEXT.md and noting Phase 30's scope is verification + docs + UAT capture protocols + one new test file.**

## Common Pitfalls

### Pitfall 1: `pytest -m live_homelab` semantics — selection, not just deselection
**What goes wrong:** Operator runs `pytest -m live_homelab` expecting "everything plus the live tests"; gets ONLY the `live_homelab`-marked tests. The default suite is now invisible.
**Why it happens:** `-m` is a SELECTION expression. `-m live_homelab` selects only tests with that marker. The pyproject `addopts = "-m 'not live_homelab and not live_ollama'"` is overridden when the operator passes their own `-m`.
**How to avoid:** Document in `30-UAT.md`: operators running the parity test should invoke `pytest -m "parity and live_homelab and live_ollama" tests/framework/parity/` (or equivalent) — explicit and visible.
**Warning signs:** Operator reports "I ran the parity test and only it ran, no other framework tests." That's the expected behavior; not a bug.

### Pitfall 2: Marker expression composability under inner subprocess
**What goes wrong:** Inner subprocess A (CLI mode) passes `-m "not parity"` after `--`. The CLI internally constructs its own pytest args and may already include `-m "not live_homelab and not live_ollama"` from pyproject `addopts`. The two `-m` arguments could disagree about precedence.
**Why it happens:** Pytest's `-m` is a single expression. Multiple `-m` flags on one command line do NOT AND together — the last one wins. The pyproject `addopts` runs FIRST, then operator/CLI args append.
**How to avoid:**
- For Route A: rely on the fact that the CLI's pytest invocation already has the pyproject `addopts` baseline, and pass `--` `-m "not parity"` for the recursion guard — verify in `cli.py` whether the CLI's `--` passthrough handles `-m` cleanly OR whether the parity test should construct a combined `-m "not parity and not live_homelab and not live_ollama"` expression and pass it explicitly.
- For Route B: pass the FULL marker expression explicitly: `-m "not parity and not live_homelab and not live_ollama"` (no reliance on pyproject defaults — Route B is sometimes invoked outside the pyproject's dir).
**Warning signs:** Inner subprocess runs the parity test recursively (infinite recursion, OOM or pytest-collect-blowup); or inner subprocess unexpectedly skips/runs live tests that diverge between the two routes.
**Verification:** Manually run `python -m pytest -m "not parity" -o "mcp_config_file=./config.test.yaml" --junitxml=/tmp/check.xml tests/` and confirm no parity test appears in the XML. [ASSUMED behavior; verify during plan]

### Pitfall 3: `config.test.yaml`'s empty `tools: {}` produces empty parity payload
**What goes wrong:** Both routes produce zero `<mcp-contracts>::test_*[*]` testcases — the dict-equality check trivially passes regardless of whether the routes actually agree.
**Why it happens:** Phase 27 D-06 set `mcp_config_file = "./config.test.yaml"` with `tools: {}` — the plugin silently no-injects when the allowlist is empty (D-13/D-16 in Phase 27 CONTEXT.md). This is correct for framework CI (no live-stack required) but wrong for the parity test (the property we want to assert is vacuous).
**How to avoid:** **OPEN QUESTION** — see Open Questions §1. Likely fixes: (a) parity test uses a different config (e.g., the project's `config.yaml` which has ~58 tools opted in), (b) parity test uses a dedicated fixture config with 2-3 tools opted in, (c) parity test asserts non-empty payload as a pre-condition (`assert outcomes_a, "parity test ran against empty config; populate ./config.test.yaml tools: or use a different config"`).
**Warning signs:** Parity test passes with zero outcomes parsed. Add a defensive `assert outcomes_a, "..."` to prevent silent vacuous PASS regardless of which config resolution is chosen.

### Pitfall 4: Windows path quoting in `--junitxml=<path>` and `cwd=`
**What goes wrong:** Spaces or unusual characters in `tmp_path` produce malformed argv on Windows; or `cwd=Path(...)` with mixed slashes confuses pytest's rootdir auto-detection.
**Why it happens:** `subprocess.run([...])` with list-form argv on Windows correctly escapes each element. But pytest's `--junitxml=PATH` parses the value as a single string with `=` delimiter — `--junitxml="C:\Users\...with spaces"` only works if the entire `--junitxml=PATH` is one list element AND pytest's argparse handles the quotes.
**How to avoid:**
- Use `f"--junitxml={xml_path}"` as a single argv element (no manual quoting). [VERIFIED: this is the pattern `_runner.py:151` uses already]
- `tmp_path` from pytest is `C:\Users\...\pytest-of-username\pytest-N\test_name0\` — has no spaces under typical CI runners but DOES under `C:\Users\washy\...` if username contains a space (this user's path has no spaces — verified).
- `cwd=str(repo_root)` is safer than `cwd=Path(repo_root)` on older Python but Python 3.14 accepts `Path` directly. [VERIFIED: `test_runner_live_smoke.py:33-34` uses `cwd=repo_root` as Path; works.]
**Warning signs:** Subprocess returncode is 2 (pytest usage error) with stderr like `usage: pytest [options]` and JUnit file is missing.

### Pitfall 5: Inner pytest re-reads outer pyproject's `mcp_config_file` even when `-o` not passed
**What goes wrong:** Route B's `-o "mcp_config_file=./config.test.yaml"` is redundant — pyproject already has it — but Route A's CLI internally passes `-o "mcp_config_file=PATH"` so its inner pytest's `mcp_config_file` comes from `-o`, not pyproject. If the two paths resolve differently relative to `cwd`, the two routes load different configs.
**Why it happens:** Pytest's `-o key=value` is a RUNTIME ini override; resolution semantics for `mcp_config_file` path values are NOT specified by pytest — they're plugin-defined (Phase 27 D-02 says "Path is resolved relative to `pyproject.toml`'s directory (pytest's standard `inipath`-relative semantics).").
**How to avoid:** Pass the SAME PATH STRING in both routes (`./config.test.yaml`), invoke both with `cwd=repo_root`, and let pytest's `inipath`-relative resolution apply identically. [VERIFIED: Phase 27 D-02 locks this semantic.]
**Warning signs:** Routes disagree on whether they loaded the config at all (e.g., one inner pytest fails with `mcp_config_file points at .../config.test.yaml which does not exist`).

### Pitfall 6: `mcp-contracts run` CLI's `--` passthrough conflicting with `--junit-xml`
**What goes wrong:** Route A's command line `mcp-contracts run --config X --junit-xml a.xml -- -m "not parity"` — pytest's `-m` is forwarded via `--`. But `--junit-xml` is a CLI-owned flag (BEFORE `--`), and `-m` after `--` may collide with the pyproject `addopts`.
**Why it happens:** Per `cli.py:672-676`, `--junit-xml=PATH` is a Typer option translated to `--junitxml=PATH` for pytest. Per `_runner.py:9` "operator-supplied `--junit-xml=PATH` is honored via a post-subprocess `shutil.copy` fan-out (not via a second `pytest --junitxml` argument, so the wrapper owns the location)" — this is important: the CLI runs an internal `--junitxml=<tempfile>` for its own parsing (Phase 29 D-05 will eventually remove that), then COPIES the result to the operator's path.
**How to avoid:** [VERIFIED] The CLI already handles `--junit-xml` correctly. For Route A, use `--junit-xml=<path>` (CLI flag) NOT `-- --junitxml=<path>` (pytest passthrough). Pass `-- -m "not parity"` only for the recursion guard.
**Warning signs:** Route A's XML file doesn't appear at the expected path.

## Code Examples

See Pattern 1 above for the full parity test body. Additional small snippets:

### Skip-when-down assertion idiom (defense-in-depth)

```python
# Inside test_cli_route_equals_pytest_route — first thing after parsing:
assert outcomes_a, (
    f"Route A produced an empty outcomes dict. This usually means the inner "
    f"pytest collected zero contract tests — verify config.test.yaml has at "
    f"least one entry under `tools:`, or invoke this test against a different "
    f"config via env var (see plan-time decision Open Q §1).\n"
    f"Route A stdout (tail):\n{proc_a.stdout[-2000:]}"
)
```

### Marker registration (in `tests/framework/conftest.py`)

```python
# Add to existing conftest.py — does NOT replace the _TEST_CODE_STUB Config fixture.
def pytest_configure(config: pytest.Config) -> None:  # noqa: D401
    config.addinivalue_line(
        "markers",
        "parity: framework-internal recursion guard for the CLI/library "
        "parity test (tests/framework/parity/). Inner subprocesses exclude "
        "this marker with `-m 'not parity'` to prevent infinite recursion.",
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| README leads with MVP-era `homelab-mcp`/`list_keyring_credentials`/Ollama setup | README leads with library-mode quickstart (one line in pyproject.toml, then `pytest`) | Phase 30 (this phase) | Phase 30 deliverable; primary CLOSE-03 work |
| `register(config=Config())` API surface (LIB-01..08 original) | `[tool.pytest.ini_options] mcp_config_file = PATH` ini route | Phase 27 D-01 (already landed) | Phase 30 docs reference the locked ini route; CLOSE-01 STALE text updated |
| `tests/contract/test_mcp_tool_contract.py` as parametrize source | `src/mcp_test_framework/contracts/_tests.py` extracted, injected via plugin | Phase 27 D-04/D-05 (already landed) | Phase 30 parity test consumes the injected nodeids `<mcp-contracts>::test_*[*]` |
| `MCPTF_CONFIG_FILE` env var as the secondary config seam | Deprecated since Phase 27 D-09; one-time `DeprecationWarning`; removed v1.5 | Phase 27 D-09 (already landed) | Phase 30 LIBRARY-MODE.md documents the deprecation; no removal action this phase |
| JUnit XML round-trip rendered the domain UI in CLI mode | Live `pytest_runtest_logreport` reporter plugin (`--mcp-domain-ui=force` in CLI mode) | Phase 29 D-05 (already landed) | Phase 30 LIBRARY-MODE.md documents `--mcp-domain-ui=auto\|force\|off` opt-in |
| README PASS-sample snapshot dated pre-Phase-24 (showed FAIL output) | Live re-capture deferred to Phase 30 UAT (Plan 24-02 GAP) | Phase 24 close (Plan 24-02 GAP, deferred) | Phase 30 30-UAT.md captures the re-snapshot protocol; user runs against live Proxmox |

**Deprecated/outdated (Phase 30 docs should NOT reference as current):**
- `register(...)` Python API — gone per Phase 27 D-01.
- `tests/contract/test_mcp_tool_contract.py` parametrize source — gone per Phase 27 D-05.
- `pytest_plugins=[...]` declaration in operator conftest — Phase 26 PACK-01 entry-point auto-load makes this unnecessary.
- Smart-default `tests/_generated/<server_slug>/` codegen output path — gone per Phase 28 D-01 (operator must set `cfg.test_code.generated_root`).

## Validation Architecture

> Skipped per phase configuration — `nyquist_validation` disabled for Phase 30 per the orchestrator brief ("Validation Architecture section: Skip"). The single new test (parity test) carries its own assertions; no Wave 0 test scaffolding gap.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pytest 9.0's JUnit XML schema is identical to 8.x at the `<testcase>` + child elements level (passed = no child; failure/error/skipped = corresponding child) | Pitfall §1, Pattern 1 | LOW — schema is stable across major versions per public contract; verify by inspecting one real JUnit XML output during planning |
| A2 | Pytest `-m` "last-wins" semantics when multiple `-m` flags appear on one argv | Pitfall §2 | MEDIUM — if pytest actually ANDs them, the inner subprocesses still work correctly (just over-filter); if it last-wins, the explicit-marker-list defense is correct. Verify during planning by running `pytest -m foo -m bar` with sentinel tests. |
| A3 | `tmp_path` Pytest fixture works inside a test that is itself running inside an outer pytest session (no fixture-scope conflict) | Pattern 1 | LOW — `tmp_path` is function-scoped; standard usage; verified by precedent at `test_runner_live_smoke.py:46-49` |
| A4 | `sys.executable -m mcp_test_framework.cli` invokes the Typer `app` correctly without an explicit `--name`/argv-0 dance | Pattern 1 | LOW — `mcp_test_framework/cli.py` declares `app = typer.Typer(name="mcp-test-framework", ...)`. `python -m cli` invokes `if __name__ == "__main__"` block. Verify the cli.py has a `__main__` guard OR uses `app()` at module load (read shows no `__main__` guard at top — VERIFY before locking pattern, possibly need `[sys.executable, "-m", "mcp_test_framework.cli"]` won't fire `app()`; may need `cli.py:app` direct entry). **HIGH-impact assumption — must verify before plan.** |
| A5 | `live_homelab` + `live_ollama` markers compose correctly when both are present on one test (test runs only if BOTH stacks are intended) | Pattern 3 | LOW — markers are independent; default addopts deselects either being present; opt-in `-m "live_homelab and live_ollama"` runs only tests with both. Established pattern in `smoke/test_smoke_homelab_mcp.py:34-37` precedent. |
| A6 | `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` resolves cwd-relative when passed via `-o` override, identical to the pyproject ini-relative default | Pitfall §5, Pattern 1 | MEDIUM — Phase 27 D-02 says "resolved relative to `pyproject.toml`'s directory (pytest's standard `inipath`-relative semantics)". When pytest is invoked from a child cwd, `inipath` still points at the outer pyproject; same resolution. **Verify when locked.** |
| A7 | Parity test failures via dict-inequality produce sufficiently readable diffs for the planner's verification step | Pattern 1 | LOW — the f-string composition surfaces set differences + per-key tuples; matches established diff-emission patterns in the framework's other tests |
| A8 | UAT capture protocols are user-driven and require no automated execution from Phase 30 | §"Live-UAT capture protocol shape" | LOW — explicit per CONTEXT.md and memory `feedback_uat_must_be_user_driven` |

## Open Questions

### 1. `config.test.yaml` has empty `tools: {}` — parity test substrate is vacuous

**What we know:** [VERIFIED] `config.test.yaml` ships with `tools: {}` deliberately so framework CI exercises plugin-load wiring without requiring `uvx homelab-mcp` to launch. Phase 27 D-13/D-16 specify the plugin silently no-injects on empty allowlist. The plugin's `pytest_collect_file` produces zero `<mcp-contracts>::test_*[*]` items under this config.

**What's unclear:** D-02 in CONTEXT.md says "reuse `./config.test.yaml` (live homelab-mcp) — same config Phase 27 D-06 dogfood already uses." But the dogfood config Phase 27 D-06 wired up has NO live homelab-mcp invocation — its tools list is empty. The parity test's premise ("both routes produce equivalent contract-test outcomes") becomes vacuous.

**Recommendation — three options for the planner to choose between (this is a discuss-phase-class decision):**
- **Option A (zero new substrate):** Add a defensive `assert outcomes_a, "..."` and document that the parity test requires `tools:` to be populated. Operator running it from a fresh clone needs to either populate `config.test.yaml` OR run against a different config via env var. Cheapest path; pushes responsibility to the operator running the parity gate.
- **Option B (parity-specific fixture config):** Create `tests/framework/parity/parity.test.yaml` with 2-3 hardcoded safe-read tools opted in. Parity test passes `--config tests/framework/parity/parity.test.yaml` to Route A and `-o "mcp_config_file=tests/framework/parity/parity.test.yaml"` to Route B. Adds one fixture file but isolates parity-test substrate from CI-dogfood substrate. **REJECTED** in CONTEXT.md `<deferred>` ("Dedicated `parity_config.yaml` fixture — rejected in D-02 in favor of reusing `config.test.yaml`") — but the rejection rationale "adds a new fixture to keep in sync for no v1.4 benefit" did not account for the tools-empty substrate problem.
- **Option C (use `config.yaml`):** Point parity test at the user's `config.yaml` (which has ~58 tools enabled) via env var override or path resolution. Closest to live operator behavior but couples the test to a user-specific file.

**Surface this in plan-phase or via a back-trip to discuss-phase.** Default if planner picks unilaterally: **Option A** (defensive assert + documentation), since it honors D-02's "reuse config.test.yaml" letter even if the substrate is empty — and the framework-CI Phase 27 D-06 loop already passes against it, so Phase 30's dogfood verification thread (SC1) is satisfied independently of the parity payload.

### 2. CLI's `__main__` entry-point shape — `sys.executable -m mcp_test_framework.cli` vs `[sys.executable, "-m", "mcp_test_framework"]` vs `["uv", "run", "mcp-contracts", "run", ...]`

**What we know:** [VERIFIED] `cli.py:73-78` declares `app = typer.Typer(...)`. The pyproject `[project.scripts] mcp-contracts = "mcp_test_framework.cli:app"` makes `mcp-contracts run` invoke `app()`. There is NO `if __name__ == "__main__": app()` guard visible at the top of cli.py (verify lower in the file).

**What's unclear:** Whether `python -m mcp_test_framework.cli` invokes `app()`. Without a `__main__` guard, `-m` just imports the module — the Typer `app` is created but never called.

**Recommendation:** Use `[sys.executable, "-m", "mcp_test_framework", "run", ...]` if a `__main__.py` exists at the package root, OR use the installed console script `[sys.executable, "-m", "mcp_test_framework.cli"]` only if cli.py has a `__main__` guard. **Verify during plan-time** by:
- `grep '__main__' src/mcp_test_framework/cli.py`
- `find src/mcp_test_framework -name '__main__.py'`

If neither exists, fall back to `["mcp-contracts", "run", ...]` (relying on the installed console script being on PATH) or `["uv", "run", "mcp-contracts", "run", ...]` (matches `test_runner_live_smoke.py:25-29` precedent verbatim, modulo the `mcp-test-framework` → `mcp-contracts` swap).

### 3. Plan-time vs phase-time amendment of REQUIREMENTS.md CLOSE-01 / CLOSE-03

**What we know:** CONTEXT.md `<downstream_impact>` says CLOSE-01 and CLOSE-03 need rewrites; ROADMAP.md is already current; CLOSE-02 and CLOSE-04 are current.

**What's unclear:** Whether the REQUIREMENTS.md amendment lands as its own plan (parallel with docs-rewrite plan) or as a task inside the docs-rewrite plan. CONTEXT.md says "planner picks whether it bundles with the README rewrite plan or stands alone."

**Recommendation:** Bundle with the README + LIBRARY-MODE.md rewrite plan as one cohesive "operator-facing docs sweep" plan. Same author, same review pass, same commit message scope. Standalone is over-organized for two list-item rewrites.

## Environment Availability

> Phase 30's tests are entirely Python + pytest + stdlib. The parity test additionally requires homelab-mcp + Ollama when run with `-m live_homelab and live_ollama`. UAT capture protocols additionally require Proxmox keyring credentials.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Outer pytest session, both subprocesses | ✓ | pinned `.python-version` | — |
| pytest 9.x | Both subprocesses | ✓ | dev dep `>=9.0` | — |
| mcp[cli]>=1.27 | Plugin auto-load + CLI Typer entry | ✓ | locked in pyproject.toml | — |
| `mcp-contracts` console script | Route A (if invoked via PATH) | ✓ | installed by `uv sync` | `[sys.executable, "-m", ...]` fallback (see Open Q §2) |
| `uvx homelab-mcp` on PATH | Parity test under `-m live_homelab` | ✗ (default CI assumed without this) | — | Skip via `-m "not live_homelab"` default addopts |
| Ollama at `OLLAMA_BASE_URL` | Parity test under `-m live_ollama` | ✗ (default) | — | Skip via default addopts |
| Proxmox keyring credentials | UAT-1 (README scenarios re-capture), UAT-4 (Phase 14 live-smoke) | ✗ (user-shell-dependent; agent shell cannot access keyring per memory `live_uat`) | — | User runs the UAT in operator shell; Phase 30 ships the capture protocol, not the execution |

**Missing dependencies with no fallback:** None blocking. Parity test gracefully skips under default addopts.

**Missing dependencies with fallback:** Proxmox keyring + live stack — fallback is **user-driven UAT execution**, which is the explicit deliverable shape per `feedback_uat_must_be_user_driven`.

## Live-UAT capture protocol shape (CLOSE-04)

Each carry-forward UAT needs a section in `30-UAT.md`. Recommended section template per UAT:

```markdown
### UAT-N: <title>
**Background:** <one-line context for what this UAT proves>
**Carried from:** <Phase/Plan/SC reference>
**Pre-reqs:**
  - <env var, shell, credential, network reachability>
  - <runtime dependency>

**Commands:**
```bash
<exact command to run, one per line>
```

**Expected observable outcome:** <what the operator should see>
**Pass criteria:**
- [ ] <observable assertion 1>
- [ ] <observable assertion 2>
- [ ] <observable assertion 3>

**Evidence (paste here after running):**
```
<paste stdout, screenshot reference, or filepath snapshot>
```

**Status:** [ ] pending / [x] pass / [ ] fail / [ ] blocked
**Notes:** <free-form>
```

### UAT-1: README test-code-scenarios PASS-sample re-capture
**Background:** README §"test-code scenarios" still shows pre-Phase-24 FAIL output for the Proxmox VM lifecycle scenario. Phase 24 shipped the `exclude_unset=True` fix; the snapshot needs re-capture against live Proxmox + homelab-mcp.

**Carried from:** Phase 24 Plan 24-02 Task 3a/3b — deferred at Plan 24-02 close (memory: Phase 24 deferred-items entry, `live-uat` row in STATE.md).

**Pre-reqs:**
- Operator shell with Proxmox keyring access (agent's PowerShell session cannot reach the keyring — see STATE.md deferred-items)
- `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` set
- `homelab-mcp` reachable via `uvx`
- Ollama reachable for any contract pass (separate run; UAT-1 is test-code only, no judges)

**Commands:**
```bash
$env:MCPTF_DOGFOOD_PROXMOX_HOST = "192.168.10.20"
uv run mcp-contracts run --test-code --config config.yaml
```

**Expected observable outcome:** All test-code scenarios pass; output shape matches the README §"test-code scenarios" snapshot format with PASS rows instead of FAIL.

**Pass criteria:**
- [ ] No `ToolCallError` from upstream homelab-mcp `inputSchema` bug surfaces (Phase 24 fix holds)
- [ ] Output matches README §"test-code scenarios" snapshot shape (headers, per-tool rows, summary)
- [ ] Re-snapshot pasted verbatim into README §"test-code scenarios", replacing the pre-Phase-24 FAIL block
- [ ] The HTML sentinel comment at README L282 (`<!-- noqa: sdet-rename-shim — ... -->`) is removed once the snapshot is current

### UAT-2: Phase 17 SC1 — `gen-test-classes` at ~70-tool scale + pyright clean
**Background:** Phase 17 codegen target was ~70 tools. Live UAT was deferred at v1.3 close; needs live homelab-mcp to enumerate the full tool surface and pyright run on the generated output.

**Carried from:** Phase 17 17-VERIFICATION.md `human_needed` row (memory: STATE.md Acknowledged at v1.3 milestone close).

**Pre-reqs:**
- `homelab-mcp` runnable via `uvx`, exposing ~70 tools
- `pyright` installed (dev dep)
- A `config.yaml` with `test_code.generated_root` set to a writable path

**Commands:**
```bash
uv run mcp-contracts gen-test-classes --config config.yaml
uv run pyright <path-from-cfg.test_code.generated_root>/<server_slug>/
```

**Expected observable outcome:** `gen-test-classes` writes ~70 typed Pydantic Params + Response class pairs; `pyright` reports zero errors / zero warnings.

**Pass criteria:**
- [ ] Generated file count matches live tool count (e.g., `find <path> -name 'test_*.py' | wc -l` ≈ 70)
- [ ] `pyright` exit code 0
- [ ] No `# type: ignore` or `# pyright: ignore` lines in generated code

### UAT-3: v1.2 Phase 13 v2 config + migration walkthrough — library-mode example
**Background:** Phase 13 SAFE-01 v1→v2 schema migration; live UAT was deferred at v1.2 close. Phase 30 closes it by demonstrating the migration walkthrough using the library-mode `mcp_config_file` ini route.

**Carried from:** Phase 13 13-VERIFICATION.md `human_needed` row.

**Pre-reqs:**
- A v1-schema `config.yaml` to migrate (legacy fixture or hand-crafted)
- pyproject.toml with `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` set

**Commands:**
```bash
# Start with v1-schema config; observe migration error
uv run pytest --collect-only
# Apply the migration per docs/MIGRATION-v1-to-v2.md
uv run mcp-contracts config-init -o config.yaml.new
# Compare new vs old; merge by hand or replace
uv run pytest --collect-only
```

**Expected observable outcome:** First `pytest --collect-only` emits a fail-loud v1→v2 migration error naming `version: 1` and pointing at the migration doc; second `pytest --collect-only` succeeds and shows injected contract tests.

**Pass criteria:**
- [ ] Migration error names the schema version field
- [ ] Migration error references `mcp-contracts config-init` as the next step
- [ ] After migration, contract tests collect under `<mcp-contracts>::test_*[*]` nodeids
- [ ] No `MCPTF_CONFIG_FILE` env var set during the walkthrough (proves library-mode is the documented route)

### UAT-4: v1.2 Phase 14 live-smoke + visual domain UI under both modes
**Background:** Phase 14 RUNNER-01 hybrid runner + visual domain UI; live UAT deferred at v1.2 close. Phase 30 closes it by capturing the domain UI output under BOTH CLI mode (`mcp-contracts run`) and library mode (`pytest --mcp-domain-ui=force`) and confirming visual parity.

**Carried from:** Phase 14 14-VERIFICATION.md `human_needed` row.

**Pre-reqs:**
- Live homelab-mcp + Ollama reachable
- `config.yaml` with at least 2-3 enabled tools

**Commands:**
```bash
# CLI mode
uv run mcp-contracts run --config config.yaml > /tmp/cli_output.txt 2>&1

# Library mode (force the reporter even in non-TTY contexts)
uv run pytest -o "mcp_config_file=./config.yaml" --mcp-domain-ui=force > /tmp/lib_output.txt 2>&1

# Visual diff
diff -u /tmp/cli_output.txt /tmp/lib_output.txt
```

**Expected observable outcome:**
- Both outputs show the MCP domain UI header / per-tool rows / `Result:` summary
- CLI mode wraps pytest's native output (none visible by default)
- Library mode emits domain UI ADDITIVE to pytest's native output (per Phase 29 D-02)
- Per-tool rows + summary line agree between the two runs (same tools, same outcomes)

**Pass criteria:**
- [ ] CLI mode shows the domain UI without pytest framing
- [ ] Library mode shows BOTH pytest native output AND the domain UI
- [ ] Per-tool verdicts (`✓ PASS` / `✗ FAIL` / `SKIP`) match across both routes
- [ ] `Result:` summary line agrees (same PASS / FAIL / SKIP counts) between the two

## `docs/LIBRARY-MODE.md` outline (CLOSE-03 deliverable)

Recommended structure for the new file. Aim ~250-400 lines.

```markdown
# Library Mode — pytest-native MCP contract testing

> Library mode is the recommended invocation. One line in `pyproject.toml`, then your existing
> `pytest` command runs framework-provided contract tests against your MCP server.

## Quickstart (90 seconds)

\`\`\`bash
uv add mcp-contracts
# In pyproject.toml:
# [tool.pytest.ini_options]
# mcp_config_file = "./config.yaml"
# (then write a minimal config.yaml — see below)
uv run pytest
\`\`\`

## What library mode IS

- A pytest plugin (`mcp_test_framework._plugin`) auto-loaded via `[project.entry-points.pytest11]`.
- Reads one ini value (`mcp_config_file`) from your `pyproject.toml` / `pytest.ini` / any pytest-config surface.
- Injects parametrized contract tests as virtual nodeids of the form `<mcp-contracts>::test_<name>[<tool>]`.
- Plays nicely with your existing tests, fixtures, markers, and CI.

## What library mode IS NOT

- Not a separate test runner — it IS pytest.
- Not a separate config language — it reads the same YAML as the CLI.
- Not opinionated about your project layout — `mcp_config_file` resolves relative to your pyproject.toml.

## The `mcp_config_file` ini value (Phase 27 D-02 mechanism)

\`\`\`toml
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
\`\`\`

| Resolution | When |
|------------|------|
| `pytest -o "mcp_config_file=..."` runtime override | Highest priority — useful for CI matrix runs |
| `[tool.pytest.ini_options] mcp_config_file = ...` | Default for everyday use |
| Unset | Plugin silently no-ops (operator opted out — explicit; no warning) |

> Note: `MCPTF_CONFIG_FILE` env var is deprecated since v1.4 (see Migration below) and removed in v1.5.

## Plugin auto-discovery

The framework declares `[project.entry-points.pytest11]` in its pyproject. Once `mcp-contracts`
is installed in your project's environment, pytest auto-loads it. You do NOT add
`pytest_plugins=[...]` anywhere.

## Injected test surface

Tests appear in your `pytest --collect-only` output as:

\`\`\`
<mcp-contracts>::test_input_schema_present[<tool>]
<mcp-contracts>::test_description_quality_clarity[<tool>]
...
\`\`\`

These are NOT files on disk in your project tree — they're virtual nodes synthesized by the plugin.
To find the source: `python -c "import mcp_test_framework.contracts._tests; print(_tests.__file__)"`.

## Markers

| Marker | Auto-applied | Use |
|--------|--------------|-----|
| `mcp_contract` | Yes (every injected test) | `pytest -m mcp_contract` / `-m "not mcp_contract"` |
| `live_homelab` | No (operator opt-in for live-stack tests) | Existing example marker; see homelab-mcp fixture |
| `live_ollama` | No | Same |

## Fixture surface

All public fixtures are prefixed with `mcp_`:
- `mcp_config` — parsed `Config` object
- `mcp_client` — async `McpTestClient`
- `mcp_judge` — Ollama judge
- `mcp_target_tool` — currently-parametrized tool name
- `mcp_rubric_clarity` / `mcp_rubric_disambiguation` / `mcp_rubric_parameters` — judge rubrics

Unprefixed compat aliases (`config`, `judge`, `client`, `target_tool`) work in v1.4 with
`DeprecationWarning`; removed in v1.5.

## Reporter plugin (`--mcp-domain-ui`, Phase 29)

Default OFF. Three values:

\`\`\`bash
pytest                                    # OFF
pytest --mcp-domain-ui                    # auto (ON if TTY, OFF in CI by default)
pytest --mcp-domain-ui=force              # ON regardless of TTY
pytest --mcp-domain-ui=off                # OFF explicitly
\`\`\`

Loaded under a separate entry-point key so you can `pytest -p no:mcp_test_framework_reporter`
to disable while keeping the contract fixtures.

## Codegen CLI (`gen-test-classes`)

Reads the SAME pyproject ini value as pytest (Phase 28 D-11):

\`\`\`bash
uv run mcp-contracts gen-test-classes
# resolves config via pyproject.toml [tool.pytest.ini_options] mcp_config_file
\`\`\`

`--config PATH` overrides for one-off runs. The config file MUST set
`test_code.generated_root` (required, no smart default — Phase 28 D-01).

## Migration from `MCPTF_CONFIG_FILE` env var

In v1.4, setting `MCPTF_CONFIG_FILE` emits a one-time `DeprecationWarning`. The env var is
removed in v1.5. Migration path:

\`\`\`toml
# Before (v1.3 / v1.4-with-warning):
# (in shell / .env file): MCPTF_CONFIG_FILE=./config.yaml

# After (v1.4 onward):
# pyproject.toml:
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
\`\`\`

## Error tone

Operator-facing errors follow `docs/ERROR-STYLE.md` (link). Examples:
- Missing config file: `mcp_config_file points at '...' which does not exist`
- Empty `tools:` allowlist: silent no-op (legitimate state)
- `test_code.generated_root` unset: fail-loud error naming the field

## Test-code scenarios (test-code-author surface)

See [`docs/TEST-CODE-AUTHORING.md`](TEST-CODE-AUTHORING.md) for the test-code-author walkthrough —
`mcp_session`, `tool()`, `ToolCallError`, scenario authoring conventions. Library mode and CLI mode
share the same test-code surface; nothing library-mode-specific to document here.
```

## README rewrite — operator-onboarding-first structure (CLOSE-03)

Recommended section ordering for the rewritten top of README:

```
1. <H1 title> mcp_test_framework / mcp-contracts
2. One-line value prop ("pytest-native MCP contract testing")
3. Quickstart (3-5 lines: install, one ini line, pytest)
4. Library-mode reference (~50 lines — links inward to docs/LIBRARY-MODE.md for depth)
   - "Add one line to pyproject.toml"
   - "Write a minimal config.yaml" (3-line shape; full config in config.example.yaml)
   - "Run pytest" — shows the injected `<mcp-contracts>::test_*[*]` collection output
5. Sample green run (existing canonical small-N example — moved DOWN; was at L222 in old README)
6. Test-code scenarios subsection (current L266 content; mostly unchanged; UAT-1 re-captures the FAIL→PASS snapshot)
7. Configuration (current L155+ content; light edits to reference `mcp_config_file` ini route alongside the env-var-deprecation note)
8. Appendix: CLI usage (current L45-150 content; demoted, retains all current CLI command docs verbatim)
9. Setup (current L19-43, demoted into Appendix or its own short section near the end)
10. Links — docs/LIBRARY-MODE.md, docs/TEST-CODE-AUTHORING.md, docs/EXTENDING.md, docs/ERROR-STYLE.md
```

**Surfaces verified clean of planning-ID leaks:** [VERIFIED]
- `README.md` — zero matches for `(Phase \d|REQ-|SEED-|D-\d|SC\d|CLOSE-|LIB-|CFG-|CODEGEN-|REPORTER-|RENAME-|PACK-)`. (Memory `project_doc_scrub_planning_artifacts` recorded this scrub as v1.2-deferred, but Phase 25 P25-05 + Phase 25 P25-06 absorbed it; no scrub work remaining.)
- `config.example.yaml` — zero matches. [VERIFIED]
- `.env.example` — zero matches. [VERIFIED]
- `docs/EXTENDING.md` — zero matches. [VERIFIED]

**Implication for the planner:** The v1.2-deferred "ID-leak scrub" tracked in memory `project_doc_scrub_planning_artifacts` has already been resolved by prior phases. Phase 30 does NOT need to spend plan-time on a scrub pass. Reframe the docs sweep as **pure rewrite + new file creation**, not "rewrite + scrub."

## Reference: pytest JUnit XML schema (D-01 substrate)

| pytest outcome | XML representation | `_parse_outcomes` mapping |
|----------------|---------------------|---------------------------|
| pass | `<testcase classname="..." name="..." time="..."/>` (no children) | `passed` |
| assertion failure | `<testcase ...><failure message="..."> traceback... </failure></testcase>` | `failed` |
| collection error / setup error | `<testcase ...><error message="..."> traceback... </error></testcase>` | `error` |
| skipped (`pytest.skip()` or `@pytest.mark.skip`) | `<testcase ...><skipped type="pytest.skip" message="..."/></testcase>` | `skipped` |
| xfail (expected failure, did fail) | `<testcase ...><skipped type="pytest.xfail" message="..."/></testcase>` | `skipped` (D-01 collapse) |
| xpassed (expected failure, but passed) | `<testcase ...><failure message="[XPASS(strict)] ..."/></testcase>` if strict; else passed | `failed` (if strict) or `passed` |
| parameterized variant | nodeid is `<file>::Class::test[<param>]`; classname encodes `<file>::Class`, name encodes `test[<param>]` | reconstructed as `f"{classname}::{name}"` |
| errors-during-collection (file-level) | `<error message="..."/>` on a synthetic `<testcase>` with name=collection target | `error` |

[CITED: https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files] [ASSUMED: A1 — schema stability across pytest 8→9 confirmed by pytest's documented public contract; verify with one real XML during plan-time]

**Nodeid reconstruction caveat:** Pytest's JUnit XML `classname` attribute can be `tests.framework.test_X` (dotted) OR `tests/framework/test_X.py` (path-like) depending on `[tool.pytest.ini_options] junit_logging` / `junit_family`. Default `junit_family=xunit2` since pytest 6.x uses dotted. The dict-equality property is preserved as long as BOTH routes use the SAME `junit_family` (and they do — neither overrides). **No special handling needed.**

## Sources

### Primary (HIGH confidence)
- `.planning/phases/30-cli-demotion-carry-forward-uat-closure-docs-rewrite/30-CONTEXT.md` — locked decisions D-01..D-03, scope, downstream impact, all four threads
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md` — D-02 ini key resolution, D-06 dogfood line, D-09 env var deprecation, D-11 CLI internal subprocess shape, D-13/D-16 empty-allowlist no-op semantics
- `.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md` — D-11 `gen-test-classes` pyproject resolution, D-13 tomllib usage
- `.planning/phases/29-live-domain-ui-reporter-plugin/29-CONTEXT.md` — D-04 `--mcp-domain-ui=auto\|force\|off`, D-05 CLI passes `force`
- `pyproject.toml` — current ini state (`mcp_config_file = "./config.test.yaml"`, `markers = [...]`, `addopts = "-m 'not live_homelab and not live_ollama'"`, `filterwarnings = [...]`, `[project.entry-points.pytest11]` block)
- `config.test.yaml` — framework dogfood config; **`tools: {}` finding drives Open Question §1**
- `tests/framework/conftest.py` — existing shape; Config-stub shim; no skip-when-down pattern
- `tests/framework/test_runner_live_smoke.py` — established subprocess + cwd + tmp_path pattern
- `tests/framework/smoke/test_smoke_homelab_mcp.py` — established `pytestmark = [live_homelab, asyncio]` pattern
- `tests/framework/test_phase27_spike_synthetic_module.py` — established embedded-subprocess-pytest pattern
- `src/mcp_test_framework/_runner.py` lines 480-595 — `ParsedRun` shape; confirms NOT directly reusable for `{nodeid: outcome}` (per-tool aggregated)
- `src/mcp_test_framework/cli.py` lines 672-676, 770, 828, 935, 954 — `--junit-xml` CLI flag plumbing
- `src/mcp_test_framework/_plugin.py` lines 1-80 — plugin shape; auto-load entry-point target

### Secondary (MEDIUM confidence)
- https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files — JUnit XML format (CITED, schema-stability across 8→9 ASSUMED per A1)
- Memory `feedback_uat_must_be_user_driven` — UAT capture protocol shape constraint
- Memory `project_doc_scrub_planning_artifacts` — historical scrub item; verified resolved by Phase 25
- Memory `project_v1_3_close_push_and_scrub` — push timing precedent

### Tertiary (LOW confidence — none used; this phase has no novel external-source claims)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; everything already in repo
- Architecture: HIGH — D-01..D-03 locked; subprocess shape verified against precedent
- Pitfalls: HIGH for §3/§4/§5 (verified against repo); MEDIUM for §2 (pytest `-m` "last wins" needs runtime verification — A2)
- Open Questions: §1 is HIGH-impact (drives whether the parity test asserts anything meaningful); §2 is MEDIUM (one grep + one find resolves it); §3 is LOW (purely organizational)

**Research date:** 2026-05-17
**Valid until:** 2026-06-15 (30 days — stable; pytest/MCP-SDK majors unlikely to change in window)
