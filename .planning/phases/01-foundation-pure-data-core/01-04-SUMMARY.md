---
phase: 01-foundation-pure-data-core
plan: 04
subsystem: tests
tags: [ruff, conftest, sys-modules, black-box, tid251, smoke-test]

requires:
  - "01-01: pyproject.toml [tool.ruff.lint.flake8-tidy-imports.banned-api] homelab_mcp ban; tests/__init__.py + tests/unit/__init__.py package markers"
provides:
  - "tests/conftest.py with pytest_configure sys.modules guard for homelab_mcp / homelab_mcp.* (belt for the TID251 submodule gap, RESEARCH Pitfall 4)"
  - "tests/_fixtures/banned_import_should_fail.py.txt deliberate-violation fixture (.py.txt extension keeps it invisible to repo-wide ruff check)"
  - "tests/unit/test_banned_imports.py with 3 sync smoke tests proving the lint rule fires (top-level import, from-import, documented submodule gap)"
  - "Closed SETUP-03 black-box enforcement loop (Plan 01 declared the rule; this plan proves it activates)"
affects:
  - 04-integration-tests    # Phase 4 fixtures (mcp_client, judge, target_tool, config) will land on top of tests/conftest.py
  - 04-tests-scaffold       # tests/_fixtures/ directory pattern available for future fixture data files

tech-stack:
  added: []
  patterns:
    - "Pattern: tests/conftest.py owns the session-level pytest_configure hook for runtime black-box enforcement; Phase 4 will add session-scoped async fixtures to the same file"
    - "Pattern: tests/_fixtures/<name>.py.txt is the storage shape for deliberately-malformed lintable code -- the .py.txt extension keeps the file invisible to `uv run ruff check src tests` while still being copyable to a real .py path under tmp_path for explicit ruff invocation"
    - "Pattern: smoke tests pin ruff to this repo's pyproject.toml via `--config <repo_root>/pyproject.toml` -- a developer's ~/.config/ruff override cannot interfere with the test"

key-files:
  created:
    - "tests/conftest.py (38 lines: pytest_configure with sys.modules scan)"
    - "tests/_fixtures/banned_import_should_fail.py.txt (12 lines: comment block + literal `import homelab_mcp`)"
    - "tests/unit/test_banned_imports.py (132 lines: 3 sync smoke tests + helpers)"
  modified: []
  deleted: []

key-decisions:
  - "Submodule-import case (`from homelab_mcp.client import x`) is caught by ruff 0.15.12's TID251 in current behavior, contradicting RESEARCH Pitfall 4's claim about ruff issue #1614. The third test handles BOTH outcomes: passes if ruff catches (gap closed), xfails with a documentation pointer if ruff misses. The runtime sys.modules guard in tests/conftest.py is the belt that closes the gap regardless of ruff version drift."
  - "The smoke tests' ruff invocation uses `--config <repo_root>/pyproject.toml` to lock the consulted config to this project. Without --config, ruff would walk up from the tmp_path file looking for pyproject.toml and might pick up a developer's ~/.config/ruff/ruff.toml, weakening the test's signal. Acceptance: T-04-03 mitigation honored."
  - "Helper `_run_ruff_against(target)` and `_output(result)` were extracted to keep the three test bodies short and visually parallel. Acceptance grep `grep -c '^def test_' tests/unit/test_banned_imports.py` correctly returns 3 (helper functions are private and don't match the regex)."
  - "Fixture file lives at `tests/_fixtures/banned_import_should_fail.py.txt` (NOT `tests/unit/_fixtures/...`). The `tests/_fixtures/` location is the natural per-spec home for cross-cutting test data; `tests/unit/_fixtures/` would imply unit-only and break Phase 4 reuse if integration tests ever need similar fixtures."

requirements-completed: [SETUP-03]

duration: "2 min 2 sec"
completed: 2026-05-04
---

# Phase 1 Plan 4: Banned-Import Belt-and-Suspenders Summary

**Closes the SETUP-03 enforcement loop with a runtime conftest sys.modules guard plus a 3-test ruff smoke suite that proves TID251 actually fires on `import homelab_mcp` and `from homelab_mcp import X`. Documents the historical submodule gap (ruff issue #1614) with a third test that passes whether ruff has fixed it or not.**

## Performance

- **Duration:** 2 min 2 sec (122 seconds)
- **Started:** 2026-05-04T22:21:08Z
- **Completed:** 2026-05-04T22:23:10Z
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 0
- **Files deleted:** 0

## Accomplishments

- Wrote `tests/conftest.py` per RESEARCH Pattern 5 verbatim: a single `pytest_configure(config)` function that scans `sys.modules` at session start for `homelab_mcp` or any `homelab_mcp.*` submodule and raises `RuntimeError` if any leaked in. The guard's docstring explicitly cites RESEARCH Pitfall 4 and ruff issue #1614 so future maintainers can find the rationale.
- Wrote `tests/_fixtures/banned_import_should_fail.py.txt` containing a literal `import homelab_mcp` plus a comment block warning future contributors NOT to rename the file to `.py` (which would break the repo-wide `ruff check src tests`).
- Wrote `tests/unit/test_banned_imports.py` with 3 sync test functions:
  1. `test_ruff_tid251_fires_on_top_level_import` — copies the fixture to `tmp_path/banned.py`, invokes `uv run ruff check --no-cache --config <pyproject> <target>`, asserts exit non-zero AND output contains "TID251" or "homelab_mcp". This is the positive case ruff IS guaranteed to catch.
  2. `test_ruff_tid251_fires_on_from_import` — same flow with inline `from homelab_mcp import something\n`. Also caught by ruff's banned-api.
  3. `test_ruff_tid251_misses_submodule_import_documented_gap` — same flow with `from homelab_mcp.client import x\n`. Branches: if ruff catches it (returncode != 0) the test passes; if ruff misses (returncode == 0) the test xfails with a pointer to the conftest belt.
- Verified all four success criteria are met: `uv run pytest tests/` reports 24 passed, 0 failed (3 new + 21 from prior plans); `uv run ruff check src tests` reports `All checks passed!`; the `.py.txt` fixture is invisible to the repo-wide ruff invocation; and the smoke test demonstrably fires TID251 on the deliberate violation.

## Task Commits

Each task was committed atomically:

1. **Task 1: tests/conftest.py sys.modules guard** — `816ef69` (feat)
2. **Task 2: fixture file + 3-test ruff smoke suite** — `e4c63d7` (test)

## Files Created/Modified

- `tests/conftest.py` — 38 lines. Single `pytest_configure(config)` function. Scans `sys.modules` for `homelab_mcp` or `homelab_mcp.*`. Raises `RuntimeError` with a diagnostic message if any leaked in. Created in `816ef69`.
- `tests/_fixtures/banned_import_should_fail.py.txt` — 12 lines (mostly a comment block explaining the .py.txt convention, ending with the literal violation `import homelab_mcp`). Created in `e4c63d7`.
- `tests/unit/test_banned_imports.py` — 132 lines. Imports `subprocess`, `Path`, `pytest`. Defines `_REPO_ROOT`, `_PYPROJECT`, `_FIXTURE` module-level constants; private helpers `_run_ruff_against(target)` and `_output(result)`; three test functions. All sync (no `@pytest.mark.asyncio`). Created in `e4c63d7`.

## Decisions Made

- **The third test passes if ruff catches the submodule case, xfails if ruff misses.** The plan body says "if ruff happens to catch it (it won't — see RESEARCH issue #1614)" use `pytest.xfail(strict=False, ...)`. In practice on ruff 0.15.12 + this repo's banned-api config, ruff DID catch it. The test's branch handles both outcomes; the xfail path is the documentation footprint for the gap, the pass path is the "gap closed by ruff" outcome. Either way the conftest belt remains the load-bearing runtime check.
- **`--config <repo_root>/pyproject.toml`** is passed to every ruff invocation in the smoke test so the test's signal cannot be silently weakened by a developer's `~/.config/ruff/ruff.toml`. T-04-03 mitigation honored.
- **`_run_ruff_against(target)` helper** abstracts the subprocess invocation. Three identical 12-line subprocess calls would have been visual noise; the helper keeps each test body to ~10 lines focused on the actual assertions.

## Confirmations Required by Plan Output Spec

1. **Whether ruff caught the submodule-import case.** **YES** — ruff 0.15.12 against this repo's `[tool.ruff.lint.flake8-tidy-imports.banned-api] "homelab_mcp" = {...}` entry catches `from homelab_mcp.client import x` with TID251 (verified by an out-of-test probe during execution). The third test's `pytest.xfail` branch was not exercised; the test passed cleanly via the "ruff fixed the gap" path. This contradicts RESEARCH Pitfall 4's claim that ruff issue #1614 is still open. The runtime sys.modules guard in tests/conftest.py remains the load-bearing belt — the lint-layer closure is bonus coverage that may be ruff-version-dependent.
2. **Exact ruff command line used in the smoke test:** `uv run ruff check --no-cache --config <repo_root>/pyproject.toml <tmp_target>`. The `--no-cache` flag prevents stale results between sequential test invocations sharing the same tmp tree; `--config` pins configuration to this project's pyproject.toml; `cwd=<repo_root>` keeps relative-path resolution sane on Windows.
3. **Confirmation that pyproject.toml's TID251 rule is the only ruff config consulted.** CONFIRMED. The smoke test passes `--config <repo_root>/pyproject.toml`, so any user-level `~/.config/ruff/ruff.toml` is ignored. The ruff probe during execution showed the exact TID251 message ending in "Drive it via mcp.client.stdio.stdio_client only." — the verbatim `msg` from this repo's pyproject.toml — confirming no other config interfered.

## Test Count + Pass/Fail

- **Plan 04 tests:** 3 collected, 3 passed, 0 failed (`uv run pytest tests/unit/test_banned_imports.py -v` exits 0).
- **Combined Phase 1 suite:** 24 collected, 24 passed, 0 failed (`uv run pytest tests/` exits 0).
- Pytest 9.0.3 + pytest-asyncio 1.3.0 strict mode active; configfile `pyproject.toml` loaded; no test marked `@pytest.mark.asyncio` (all sync).

## Deviations from Plan

### Auto-fixed Issues

None.

### Research-vs-Reality Notes

- **RESEARCH Pitfall 4 partially obsolete on current ruff.** RESEARCH.md asserts ruff's TID251 does NOT catch `from homelab_mcp.client import X` (citing ruff issue #1614). On ruff 0.15.12 + this repo's banned-api config, that case IS caught. Either issue #1614 has been resolved in a recent ruff release, or the `from X.sub import Y` form is treated as `import X` followed by an attribute access in the parser pass that runs banned-api checks. Practically: the lint-layer gap is narrower than RESEARCH claimed. The conftest sys.modules belt remains valuable — both as defense-in-depth against ruff version regressions and as the only check that catches dynamic imports (e.g., `importlib.import_module("homelab_mcp")`), which static analysis cannot cover regardless of ruff version.

---

**Total deviations:** 0 (clean execution; both tasks shipped as specified on first try).

## Issues Encountered

- **Windows CRLF warnings** on staging the new files. Same as Plans 01-01, 01-02, and 01-03. Harmless; git auto-normalizes on next checkout.
- **None functional.** Both tasks executed cleanly; no Rule 1/2/3 fixes needed.

## User Setup Required

None. The smoke test invokes ruff via `uv run` against fixtures it writes itself under pytest's `tmp_path`; no external services, no user secrets, no manual steps.

## TDD Gate Compliance

The plan declares `type: execute` (not `type: tdd`) at the plan level, so plan-level TDD-gate enforcement is N/A. Task 2 carries `tdd="true"`, but in this case the "implementation under test" is the ruff configuration shipped in Plan 01-01 — the test itself is the sole new code besides the inert fixture file. There is no production code module being driven by the test, so the RED → GREEN → REFACTOR cycle collapses to "write the test, verify it passes against the existing rule, commit." That is what happened.

## Verification Evidence

- `uv run pytest tests/unit/test_banned_imports.py -v`: 3 passed, 0 failed (200ms wall)
- `uv run pytest tests/ -v`: 24 passed, 0 failed (combined; 550ms wall)
- `uv run pytest --collect-only tests/`: 24 tests collected; conftest's sys.modules guard does NOT trigger on the clean session
- `uv run ruff check src tests`: `All checks passed!` (exit 0; the .py.txt fixture is invisible by extension)
- Out-of-test ruff probe against fixture copy confirms TID251 fires with the project's exact `msg` text
- Out-of-test probe against `from homelab_mcp.client import x\n` confirms ruff 0.15.12 also catches the submodule case (contradicting RESEARCH Pitfall 4 — see Research-vs-Reality Notes)
- `grep -c '^def test_' tests/unit/test_banned_imports.py` returns 3
- `grep -q 'subprocess' tests/unit/test_banned_imports.py` exits 0
- `grep -q 'TID251' tests/unit/test_banned_imports.py` exits 0
- `grep -q '^import homelab_mcp$' tests/_fixtures/banned_import_should_fail.py.txt` exits 0
- `test ! -f tests/_fixtures/banned_import_should_fail.py` exits 0 (no .py twin exists)
- `grep -q 'def pytest_configure' tests/conftest.py` exits 0
- `grep -q '== "homelab_mcp"' tests/conftest.py` exits 0
- `grep -q 'homelab_mcp\.' tests/conftest.py` exits 0
- `grep -q 'raise RuntimeError' tests/conftest.py` exits 0

## Phase 1 Closure

This plan is the last plan in Phase 1 (foundation-pure-data-core). With Plan 04 complete, the Phase 1 deliverables are fully landed:

- **SETUP-01** (Plan 01) — uv install + lockfile
- **SETUP-02** (Plan 01) — pytest-asyncio strict + session loop scope
- **SETUP-03** (Plan 01 + Plan 04) — black-box enforcement: lint-layer ruff TID251 (Plan 01) + runtime sys.modules guard + smoke-test proof (Plan 04)
- **CORE-01** (Plan 02) — frozen Config(BaseSettings) with locked precedence + 9 unit tests
- **CORE-02** (Plan 03) — schema_validator with 7 structural checks + 12 unit tests
- **DOCS-02** (Plan 02) — .env.example + config.example.yaml

Total Phase 1 test surface: 24 passing tests, 0 failures, ruff clean. No outstanding blockers; ready for Phase 2 (mcp-stdio-client).

## Threat Surface Scan

No new security-relevant surface introduced. The plan's `<threat_model>` already disposed:

- T-04-01 (`homelab_mcp.client` submodule bypass) as `mitigate` — belt (conftest sys.modules) + suspenders (ruff TID251). Both are shipped. The submodule case appears to be caught at the lint layer too (see Research-vs-Reality Notes), so the gap is narrower than threatmodeled — but the runtime belt remains and is the load-bearing check across ruff versions.
- T-04-02 (a future contributor adds a `.py` fixture containing `import homelab_mcp` and breaks `ruff check`) as `accept` — documented in fixture comment block; the failure mode is loud and obvious.
- T-04-03 (smoke test invokes ruff with a different config than pyproject.toml) as `mitigate` — the smoke test passes `--config <repo_root>/pyproject.toml` explicitly; verified.

All mitigations honored.

## Next Phase Readiness

- **Phase 2 (mcp-stdio-client)** is unblocked. The runtime black-box guard is in place: any accidental `import homelab_mcp` in `mcp_client.py` will fail the test session at `pytest_configure` time. Phase 2's `McpTestClient` will land alongside the existing `tests/conftest.py` — Phase 4 will then add session-scoped async fixtures to the same file.
- **Phase 4 (integration tests)** test discovery infrastructure is now complete: `tests/conftest.py` exists; `tests/unit/` is populated; `tests/_fixtures/` pattern is established for any future fixture data the integration tests may need.
- No outstanding blockers.

## Self-Check: PASSED

Verified via filesystem and git:

- `tests/conftest.py` — FOUND (committed in `816ef69`)
- `tests/_fixtures/banned_import_should_fail.py.txt` — FOUND (committed in `e4c63d7`)
- `tests/unit/test_banned_imports.py` — FOUND (committed in `e4c63d7`)
- `tests/_fixtures/banned_import_should_fail.py` — ABSENT (the .py twin does NOT exist; verified by `test ! -f`)
- Commit `816ef69` — FOUND in `git log` (`feat(01-04): add tests/conftest.py sys.modules guard for homelab_mcp`)
- Commit `e4c63d7` — FOUND in `git log` (`test(01-04): add ruff TID251 smoke test with banned-import fixture`)

---
*Phase: 01-foundation-pure-data-core*
*Completed: 2026-05-04*
