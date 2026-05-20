---
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/framework/parity/test_cli_vs_pytest_route.py
  - tests/framework/conftest.py
  - docs/LIBRARY-MODE.md
  - README.md
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 30 delivers one new production-shape test (`tests/framework/parity/test_cli_vs_pytest_route.py`), a one-function addition to `tests/framework/conftest.py`, and two doc files (`docs/LIBRARY-MODE.md`, `README.md`). The docs are high quality — no planning-ID leaks, consistent terminology, cross-refs intact. The `conftest.py` change is minimal and correct (aside from an info-level naming note). The parity test contains one BLOCKER and two WARNINGS that compromise its ability to deliver on its stated contract (CLOSE-02: "identical pass/fail signal between CLI and library routes").

The BLOCKER is a **scope mismatch**: Route A (CLI) collects `tests/contract/` by default; Route B (raw pytest) is invoked with `tests/` (the full suite). These are different test sets — the parity comparison is between non-equivalent collection scopes, so the "identical `{nodeid: outcome}` dict" assertion would fail on any real stack run or produce a misleading result. The D-02a defensive assert masks the issue only when `tools: {}` (vacuous case), meaning the bug would surface only during an actual parity gate run with a populated config.

---

## Critical Issues

### CR-01: Route A and Route B collect different test scopes — parity comparison is invalid

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:97-116`

**Issue:** Route A invokes the CLI (`mcp_test_framework.cli run`), which internally calls `_build_pytest_args()` in `src/mcp_test_framework/_runner.py`. Per `_runner.py:144-145`, the default scope for `run` is `tests/contract` only (the operator-facing SUT-contract surface). Route B invokes `pytest tests/` — the entire test suite including `tests/framework/`, `tests/test_code/`, and any other subdirectories.

The two subprocesses therefore collect entirely different test sets. The `{nodeid: outcome}` dicts will always diverge on a real stack: Route A will produce only the injected `<mcp-contracts>::test_*[tool]` nodes (from the plugin running inside `tests/contract` scope), while Route B will also collect all tests under `tests/framework/` (framework self-tests). The assertion `outcomes_a == outcomes_b` will either always fail (framework tests in B but not A) or always produce a vacuous empty pass (if both happen to empty out for unrelated reasons). Either way the parity gate does not measure what CLOSE-02 requires.

**Evidence from source:** `src/mcp_test_framework/_runner.py` lines 144-149:
```python
else:
    args = ["tests/contract"]
if with_framework:
    args.append("tests/framework")
```

Route B subprocess command (parity test line 110-116):
```python
sys.executable, "-m", "pytest",
"-o", "mcp_config_file=./config.test.yaml",
f"--junitxml={xml_b}",
"-m", "not parity",
"tests/",        # <-- collects the entire test suite
```

**Fix:** Route B must collect the same scope as Route A uses internally. Since the CLI's default scope is `tests/contract` (where the plugin injects virtual contract tests), Route B must collect only that scope — or both routes must be driven at the same explicit scope. The simplest fix is to change Route B to also target `tests/contract` and add the plugin's ini override:

```python
proc_b = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "-o", f"mcp_config_file={repo_root / 'config.test.yaml'}",
        f"--junitxml={xml_b}",
        "-m", "not parity",
        "tests/contract",   # match Route A's default scope
    ],
    cwd=repo_root, capture_output=True, text=True, check=False,
)
```

Alternatively, if the intent is to compare the full suite under both routes, Route A must be invoked with `--with-framework` — but the plan explicitly chose the default (operator-facing) scope per D-02, so narrowing Route B to `tests/contract` is the correct fix.

---

## Warnings

### WR-01: D-02a defensive assert only checks `outcomes_a` — a vacuous Route B passes undetected

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:143-152`

**Issue:** The defensive non-vacuous assertion checks only `assert outcomes_a` (Route A produced at least one test case). If Route B produces an empty outcome dict while Route A produces test cases, the assertion passes (Route A is non-empty) and then `outcomes_a == outcomes_b` fails with a confusing "Only in Route A" error rather than the clear "Route B vacuous" message the D-02a pattern is meant to produce.

More importantly, the empty-dict guard exists to prevent "vacuous PASS" — the case where both routes produce zero outcomes and the equality check trivially passes. A symmetric guard should check both sides:

```python
assert outcomes_a, (
    "Route A (CLI) produced zero <testcase> entries — ..."
)
assert outcomes_b, (
    "Route B (pytest) produced zero <testcase> entries — ..."
)
```

The second assert catches the case where Route A works but Route B silently collects nothing (e.g., misconfigured `mcp_config_file` ini override, or a scope argument that resolves to no tests).

**Fix:** Add a matching `assert outcomes_b, (...)` immediately after the `assert outcomes_a` block, with an analogous error message pointing at Route B.

---

### WR-02: Route A's `-m "not parity"` passthrough conflicts with `addopts` live-marker exclusions inside inner subprocess

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:97-105`

**Issue:** The CLI's inner subprocess pytest runs with the project's `pyproject.toml` `addopts = "-m 'not live_homelab and not live_ollama'"` already active (the ini is read by the inner subprocess from `pyproject.toml`). Route A then additionally passes `-- -m "not parity"` via Typer passthrough.

When pytest receives both an `addopts` `-m` expression and a command-line `-m` expression, the command-line `-m` **replaces** (not composes with) the `addopts` one. The inner Route A subprocess therefore collects tests with only `-m "not parity"` in effect — the `live_homelab` and `live_ollama` exclusions from `addopts` are overridden. This means Route A's inner pytest can collect and attempt to run live-stack tests that the outer parity test's own marker gates were intended to guard.

Route B has the same issue: `-m "not parity"` overrides `addopts`, so live tests could be collected inside Route B's subprocess.

**Fix:** Compose the marker expression to carry both guards:

```python
# Route A passthrough
"--", "-m", "not parity and not live_homelab and not live_ollama",

# Route B direct
"-m", "not parity and not live_homelab and not live_ollama",
```

This ensures the inner subprocesses inherit the same live-test exclusion the outer framework CI applies.

---

### WR-03: `_parse_outcomes` silently overwrites duplicate nodeids

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:72-84`

**Issue:** The `_parse_outcomes` function builds `nodeid` from `classname::name`. If two `<testcase>` elements share the same reconstructed nodeid (which can happen when the same test function name appears in multiple parametrize variants that share a bracket-less name, or when pytest's JUnit writer produces duplicate classname/name pairs for setup-error entries), later entries silently overwrite earlier ones in the `out` dict. The function offers no duplicate detection or warning.

The any-fail-wins docstring claims `failure > error > skipped > passed` priority, but the `if/elif/else` chain in the loop body does NOT implement any-fail-wins across multiple elements with the same nodeid — it implements last-seen-wins. If a `passed` entry is emitted last for a nodeid that had an earlier `failure` entry, the outcome will be recorded as `passed`.

**Fix:** Implement true any-fail-wins:

```python
PRIORITY = {"failed": 0, "error": 1, "skipped": 2, "passed": 3}

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
    # Apply any-fail-wins: only update if the new outcome has higher priority
    if nodeid not in out or PRIORITY[outcome] < PRIORITY[out[nodeid]]:
        out[nodeid] = outcome
```

---

## Info

### IN-01: `conftest.py` hook parameter `config` shadows the `config` fixture by name

**File:** `tests/framework/conftest.py:27`

**Issue:** The `pytest_configure(config: pytest.Config)` hook parameter shares the name `config` with the `@pytest.fixture(scope="session") def config()` fixture defined in the same module. This is not a bug — pluggy hooks and pytest fixtures occupy different namespaces, and the comment in the docstring explains it correctly. However, a future contributor reading the file cold will need to understand why two `config` identifiers in the same module refer to different things. The plan originally proposed `pytestconfig` to avoid exactly this reader confusion, but pluggy rejected it.

**Suggestion:** A short inline comment on the parameter line (beyond the docstring prose) would help static readers scanning the file. The existing docstring explanation is sufficient — this is advisory only.

---

### IN-02: LIBRARY-MODE.md "Running the parity gate locally" section references `config.test.yaml` with incorrect expectation given WR-02

**File:** `docs/LIBRARY-MODE.md:362-368`

**Issue:** The parity gate section instructs the operator to run:

```bash
pytest -m "parity and live_homelab and live_ollama" tests/framework/parity/
```

This selects the parity test, which then internally spawns two subprocesses. Given WR-02 (the inner `-m "not parity"` overrides `addopts`), those subprocesses may unexpectedly collect live-stack tests in the inner runs. The doc does not warn about this interaction. Once WR-02 is fixed, the doc instruction will be correct as written.

**Suggestion:** After WR-02 is resolved in the code, no doc change is needed. If WR-02 is left as-is, add a note: "The inner subprocesses spawned by the parity test compose their own `-m` expression; if your `addopts` excludes live markers, verify the inner marker expression carries those exclusions too."

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
