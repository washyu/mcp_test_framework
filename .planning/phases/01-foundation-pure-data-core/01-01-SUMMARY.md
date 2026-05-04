---
phase: 01-foundation-pure-data-core
plan: 01
subsystem: infra
tags: [python, uv, pyproject, ruff, pytest-asyncio, hatchling, pep735]

requires: []
provides:
  - "PEP 735 [dependency-groups].dev block with pytest 9.0.3, pytest-asyncio 1.3.0, ruff 0.15.12"
  - "Runtime deps locked: mcp 1.27.0, pydantic 2.13.3, pydantic-settings 2.14.0, jsonschema 4.26.0"
  - "uv.lock committed (639 lines, 40 packages, Python 3.14.3)"
  - "pytest-asyncio strict mode + session-scoped fixture loop configured at the build layer"
  - "Ruff TID251 banned-api rule for homelab_mcp declared (partial SETUP-03 coverage; runtime sys.modules belt ships in Plan 04)"
  - "src/mcp_test_framework package importable; tests/ + tests/unit/ scaffolding ready for Plans 02 and 03"
  - "Hatch wheel target configured for the project-name/package-name mismatch (mvp- vs mcp_)"
affects:
  - 01-02-pure-data-models  # consumes pydantic, pydantic-settings, jsonschema runtime deps
  - 01-03-schema-validator  # consumes jsonschema, mcp.types.Tool runtime deps
  - 01-04-tests-scaffold    # consumes pytest, pytest-asyncio, ruff config
  - 02-mcp-stdio-client     # consumes mcp SDK runtime dep
  - 03-ollama-judge         # consumes pydantic + new httpx runtime dep (added in Phase 3)
  - 04-integration-tests    # consumes pytest-asyncio strict + session loop policy
  - 05-cli                  # consumes [project.scripts] entry point (commented out here, wired in Phase 5)

tech-stack:
  added:
    - "uv 0.11.3 (Python 3.14.3 toolchain)"
    - "mcp 1.27.0 (runtime, types only in Phase 1)"
    - "pydantic 2.13.3 + pydantic-core 2.46.3"
    - "pydantic-settings 2.14.0 with [yaml] extra (pulls pyyaml 6.0.3, python-dotenv 1.2.2 transitively)"
    - "jsonschema 4.26.0 + jsonschema-specifications 2025.9.1 + referencing 0.37.0"
    - "pytest 9.0.3 + pytest-asyncio 1.3.0 (strict mode default)"
    - "ruff 0.15.12 (TID flake8-tidy-imports rule active)"
    - "hatchling (build backend, wheel target explicit)"
  patterns:
    - "PEP 735 [dependency-groups].dev (NOT legacy [tool.uv].dev-dependencies, NOT [project.optional-dependencies].dev)"
    - "Runtime deps in [project.dependencies]; tooling in [dependency-groups].dev"
    - "Black-box enforcement: ruff TID251 banned-api at lint layer; sys.modules belt deferred to Plan 04"
    - "uv.lock committed (Pitfall 5 -- not in .gitignore)"
    - "Hatch wheel target explicit when project name and package name diverge"

key-files:
  created:
    - "pyproject.toml (full Phase 1 shape per 01-RESEARCH Pattern 1, plus hatch wheel target)"
    - "src/mcp_test_framework/__init__.py (package marker; __version__ = '0.1.0')"
    - "tests/__init__.py (test package marker)"
    - "tests/unit/__init__.py (unit subpackage marker for Phase 1 unit tests)"
    - ".gitignore (.env excluded; uv.lock intentionally NOT excluded)"
    - "uv.lock (639 lines; 40 packages)"
  modified: []
  deleted:
    - "main.py (uv init hello-world stub; nothing depends on it per CONTEXT.md)"

key-decisions:
  - "ruff target-version = 'py314' accepted by ruff 0.15.12 with no warnings (Open Question 1 resolved -- no fallback needed)"
  - "mcp 1.27.0 installed cleanly on Python 3.14.3 (Open Question 2 resolved -- no wheel-build issues)"
  - "Hatch [tool.hatch.build.targets.wheel] packages = ['src/mcp_test_framework'] is required because project name (mvp-test-framework) != package name (mcp_test_framework); uv sync fails without it"
  - "Used Write tool with __version__ = '0.1.0' export in src/__init__.py (plan permitted either empty or version export)"

patterns-established:
  - "Pattern 1: pyproject.toml dependency layering -- runtime in [project.dependencies], dev tooling in [dependency-groups].dev (PEP 735)"
  - "Pattern 2: Black-box enforcement -- ruff TID251 banned-api at the build/lint layer; runtime sys.modules guard ships in Plan 04 as belt-and-suspenders for the submodule-import gap"
  - "Pattern 3: pytest-asyncio strict mode + session-scoped fixture loop is configured ONCE at the build layer; Phase 4 tests opt-in via @pytest.mark.asyncio(loop_scope='session') marker per PITFALLS.md Pitfall 1"

requirements-completed: [SETUP-01, SETUP-02, SETUP-03]

duration: "2 min 29 sec"
completed: 2026-05-04
---

# Phase 1 Plan 1: Project Bootstrap Summary

**uv-managed Python 3.14.3 project skeleton with pyproject.toml (PEP 735 dep groups), pytest-asyncio strict + session-loop config, ruff TID251 black-box enforcement, src/tests scaffolding, and committed 639-line uv.lock**

## Performance

- **Duration:** 2 min 29 sec (149 seconds)
- **Started:** 2026-05-04T21:59:20Z
- **Completed:** 2026-05-04T22:01:49Z
- **Tasks:** 2
- **Files created:** 6
- **Files deleted:** 1 (main.py stub)

## Accomplishments

- Rewrote `pyproject.toml` from a 7-line `uv init` stub to the full Phase 1 target shape per `01-RESEARCH.md` Pattern 1: 4 runtime deps, 3 dev deps under PEP 735 `[dependency-groups].dev`, pytest-asyncio strict mode + session-scoped fixture loop, ruff `TID251` `banned-api` rule for `homelab_mcp`.
- Generated and committed `uv.lock` (639 lines, 40 packages resolved against Python 3.14.3) — the reproducible-install promise from CONTEXT.md success criterion 1.
- Scaffolded `src/mcp_test_framework/` and `tests/unit/` package directories so Plans 02 and 03 can land their pure-data modules and unit tests without any further infra work.
- Verified the full bootstrap: `uv run python -c "import mcp_test_framework"` exits 0, `uv run pytest --collect-only tests/` configfile-loads correctly with `mode=Mode.STRICT, asyncio_default_fixture_loop_scope=session`, `uv run ruff check src tests` reports `All checks passed!`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite pyproject.toml** — `7139b44` (feat)
2. **Task 2: Scaffold src/tests + .gitignore + uv.lock; delete main.py** — `2e1038a` (feat)

_The Task 2 commit also carries the Rule 3 Hatch wheel-target deviation in pyproject.toml (see Deviations)._

## Files Created/Modified

- `pyproject.toml` — Full Phase 1 shape: runtime deps, PEP 735 dev deps, pytest-asyncio + ruff + hatch wheel config (created in Task 1, amended in Task 2 for Rule 3 deviation)
- `src/mcp_test_framework/__init__.py` — Package marker exporting `__version__ = "0.1.0"`
- `tests/__init__.py` — Tests package marker (empty)
- `tests/unit/__init__.py` — Unit subpackage marker for Phase 1 unit tests (empty)
- `.gitignore` — `.env`, `.venv/`, `__pycache__/`, etc.; `uv.lock` deliberately NOT listed (Pitfall 5)
- `uv.lock` — 639 lines, 40 packages locked against Python 3.14.3
- `main.py` — DELETED (uv init hello-world stub; nothing depends on it per CONTEXT.md)

## Decisions Made

- **Used `__version__ = "0.1.0"` in `src/mcp_test_framework/__init__.py`.** Plan permitted either empty file or version export; version export is preferred so `import mcp_test_framework; mcp_test_framework.__version__` works for diagnostics from Plan 04 onward.
- **Resolved Open Question 1 (ruff `target-version = "py314"`).** Ruff 0.15.12 accepts `py314` literally with no warnings or errors. No fallback to `py313` needed.
- **Resolved Open Question 2 (`mcp` 1.27 on Python 3.14).** `uv sync` resolved and installed `mcp 1.27.0` cleanly on Python 3.14.3 (CPython). No wheel-build failures encountered. Transitive deps (`pyjwt`, `pywin32`, `cryptography`, `httpx`, etc.) all installed without issue on Windows 11 / Python 3.14.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` to pyproject.toml**

- **Found during:** Task 2 (running `uv sync`)
- **Issue:** `uv sync` failed during the editable-install build step with:
  > `ValueError: Unable to determine which files to ship inside the wheel using the following heuristics: ... The most likely cause of this is that there is no directory that matches the name of your project (mvp_test_framework).`
  Hatchling's default heuristic looks for a directory matching the project name (transformed to underscores: `mvp_test_framework`), but the package is intentionally named `mcp_test_framework` per `docs/mcp_test_framework_mvp_spec.md`. `mvp` ≠ `mcp` — Hatchling can't auto-detect this mismatch.
- **Fix:** Added a `[tool.hatch.build.targets.wheel]` block declaring `packages = ["src/mcp_test_framework"]`. The plan said "keep existing hatchling block as-is (whatever uv init produced)" — uv init produced no wheel-target config, so the most permissive interpretation of "as-is" was to add the minimum required for hatchling to find the package.
- **Files modified:** `pyproject.toml` (5 added lines under `[build-system]`, with an inline comment documenting the deviation)
- **Verification:** `uv sync` succeeded after the fix; 40 packages resolved and installed; `uv run python -c "import mcp_test_framework"` exits 0.
- **Committed in:** `2e1038a` (Task 2 commit; the Hatch fix was amended into the pyproject.toml edits before staging)

---

**Total deviations:** 1 auto-fixed (1 blocking — Rule 3)
**Impact on plan:** The Hatch wheel-target addition was strictly required to complete the plan's `uv sync` step. No scope creep — the change is mechanical, project-specific, and would have been required regardless of who executed the plan. The plan's "keep [build-system] as-is" wording assumed `uv init` had produced wheel-target config, but it had not — this is a plan-text gap, not an executor judgment call.

## Issues Encountered

- **Pytest exit code 5 vs the plan's expectation of exit 0 for empty discovery.** Pytest 9 returns exit code 5 ("no tests collected") when test discovery succeeds but finds zero tests — by design, not a failure. The plan's verify command (`grep -E 'collected [0-9]+ items|no tests ran'`) accepts this output, but the acceptance-criterion text said "exits 0". The verify-command grep was the load-bearing check (and matched: output included `collected 0 items`); the "exits 0" phrasing is slightly off vs pytest 9's actual behavior. Discovery itself succeeded — the configfile loaded, strict mode + session loop_scope are active. Treating the criterion as met. Recommend Plan 02 or later author tighten the wording to "exits 0 OR exits 5 with 'collected 0 items'".
- **Windows CRLF line-ending warnings on every staged text file.** Harmless — git auto-normalizes on next checkout. No content drift.

## User Setup Required

None. No external services configured in this plan.

## TDD Gate Compliance

N/A — Plan frontmatter declares `type: execute`, not `type: tdd`. No RED/GREEN/REFACTOR cycle expected.

## Verification Evidence

- `python -c "import tomllib"` assertion sweep on pyproject.toml: PASS (all required keys present; legacy `[tool.uv]` and top-level `dev-dependencies` absent; no direct `pyyaml`/`python-dotenv`)
- `uv sync` exit 0; 40 packages installed
- `wc -l uv.lock` = 639 (>>50 minimum)
- `grep -q '^\.env$' .gitignore` PASS; `grep -E '^uv\.lock$' .gitignore` returns nothing (correct)
- `test ! -f main.py` PASS
- `uv run python -c "import mcp_test_framework"` exit 0; prints `import OK 0.1.0`
- `uv run pytest --collect-only tests/` discovery succeeds (configfile loaded; `mode=Mode.STRICT`; `asyncio_default_fixture_loop_scope=session`); exit 5 by pytest-9 design for zero-tests-collected
- `uv run ruff check src tests` exit 0; output: `All checks passed!`

## Next Phase Readiness

- **Plan 01-02 (pure-data models)** is unblocked: pydantic 2.13.3 and pydantic-settings 2.14.0 are installed; `src/mcp_test_framework/` package exists.
- **Plan 01-03 (schema validator)** is unblocked: jsonschema 4.26.0 and `mcp.types.Tool` are importable.
- **Plan 01-04 (tests scaffold + smoke)** will need to add `tests/conftest.py` with the `sys.modules` belt-and-suspenders guard for the TID251 submodule gap (Pitfall 4 from 01-RESEARCH.md). This is intentionally deferred — Plan 01-01's scope was the lint-layer half of SETUP-03 only.
- No outstanding blockers.

## Self-Check: PASSED

Verified via filesystem and git:

- `pyproject.toml` — FOUND (committed in `7139b44`, amended `2e1038a`)
- `src/mcp_test_framework/__init__.py` — FOUND (committed in `2e1038a`)
- `tests/__init__.py` — FOUND (committed in `2e1038a`)
- `tests/unit/__init__.py` — FOUND (committed in `2e1038a`)
- `.gitignore` — FOUND (committed in `2e1038a`)
- `uv.lock` — FOUND (committed in `2e1038a`)
- `main.py` — ABSENT (deleted before Task 2 commit, never tracked in git)
- Commit `7139b44` — FOUND in `git log`
- Commit `2e1038a` — FOUND in `git log`

---
*Phase: 01-foundation-pure-data-core*
*Completed: 2026-05-04*
