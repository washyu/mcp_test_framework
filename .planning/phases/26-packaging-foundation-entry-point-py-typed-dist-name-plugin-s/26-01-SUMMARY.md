---
phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s
plan: 01
subsystem: packaging

tags: [packaging, pyproject, entry-points, dist-rename, pytest11, source-of-truth-amendment]

# Dependency graph
requires:
  - phase: 25-public-api-rename-seed-023-sdet-test-code
    provides: "Locked `mcp_test_framework.test_code` public-import surface — Phase 26 can reference it from entry-point strings without a follow-up rename"
provides:
  - "`pyproject.toml [project] name = \"mcp-contracts\"` (D-01)"
  - "Both console scripts declared: `mcp-contracts` (primary, D-05) and `mcp-test-framework` (v1.4 deprecation shim, D-06)"
  - "`[project.entry-points.pytest11]` declaring `mcp_test_framework = mcp_test_framework._plugin` (D-09 / PACK-01)"
  - "`cli.py:974` version command now looks up `metadata.version(\"mcp-contracts\")` — RESEARCH.md key finding 5 closed"
  - "Module docstring distribution-name/package-name discrepancy block refreshed to post-rename truth (D-01/D-04/D-06)"
  - "REQUIREMENTS.md PACK-03 row + ROADMAP.md Phase 26 Goal/SC1 amended for `mcp-contracts` + TestPyPI scope + D-02 closed-by-non-applicability — source-of-truth docs correct from Wave 1 onward (revision 1: moved from Plan 26-05 Task 2)"
affects:
  - "Plan 26-02 (creates the `_plugin.py` and `_deprecated_script.py` module bodies that entry-point strings reference)"
  - "Plan 26-03 (relies on hatch `packages` auto-including `py.typed` markers — hatch comment cites this in RESEARCH.md)"
  - "Plan 26-04 (wheel-shape gate asserts entry-point line + script entries appear verbatim in `dist-info/entry_points.txt`)"
  - "Plan 26-05 (no longer needs Task 2 source-of-truth amendments — moved here in revision 1)"
  - "All Waves 2-4 executors and the plan-checker (they read REQUIREMENTS.md / ROADMAP.md as source of truth)"

# Tech tracking
tech-stack:
  added: []  # Zero new deps; only metadata + one cli.py string fix + planning-doc edits
  patterns:
    - "Declared-but-not-yet-bodied entry-points: `pyproject.toml` references `_plugin` and `_deprecated_script` modules that don't exist on disk yet — hatchling accepts string references at metadata-parse time, the build only fails if pytest11 tries to import the missing module. Wave 1 lands the declarations; Plan 26-02 (Wave 2) lands the bodies."
    - "Dist name decoupled from importable package name (D-04): conventional Python pattern à la Pillow/PIL (dist `Pillow`, import `PIL`) and beautifulsoup4/bs4. Dist becomes `mcp-contracts`; importable package stays `mcp_test_framework`."
    - "Console-script back-compat shim pattern: legacy script name `mcp-test-framework` retained in `[project.scripts]` for one milestone (v1.4), dispatching to a wrapper that emits DeprecationWarning before forwarding to the new entry point — module body lands in Plan 26-02."

key-files:
  created: []  # No new files; all three tasks edit existing files
  modified:
    - "pyproject.toml — dist rename + both console scripts + pytest11 entry point + hatch comment refresh"
    - "src/mcp_test_framework/cli.py — version command dist-name lookup + module docstring discrepancy block"
    - ".planning/REQUIREMENTS.md — PACK-03 row amended (mcp-contracts, D-01/D-02/D-03 citations)"
    - ".planning/ROADMAP.md — Phase 26 Goal + SC1 amended (mcp-contracts, TestPyPI scope, closed-by-non-applicability)"

key-decisions:
  - "D-01 (CONTEXT) executed: dist name `mcp-contracts` (not `mcp-test-framework`, which is taken on PyPI by an unrelated project per D-03)"
  - "D-04 (CONTEXT) honored: importable package `mcp_test_framework` is UNCHANGED — only dist name and CLI script change. Conventional Python pattern (Pillow/PIL, beautifulsoup4/bs4) — operators continue `from mcp_test_framework import ...` after install"
  - "D-05/D-06 (CONTEXT) executed: both `mcp-contracts` (primary) and `mcp-test-framework` (v1.4 deprecation shim) declared in `[project.scripts]` — shim drops in v1.5 (D-18)"
  - "D-09 (CONTEXT) executed: `[project.entry-points.pytest11]` declared — operators no longer need `pytest_plugins=[...]` in their conftest once Plan 26-02 lands `_plugin.py`"
  - "Hatch `packages = [\"src/mcp_test_framework\"]` line UNCHANGED per RESEARCH.md (hatch discussion #554: `packages` auto-includes non-`.py` files including PEP 561 `py.typed` markers; Plan 26-03 relies on this)"
  - "`filterwarnings` line UNCHANGED — Phase 25 D-03's `always::DeprecationWarning:mcp_test_framework` already covers Phase 26 shims"
  - "Revision 1 / plan-checker Issue #5: REQUIREMENTS.md + ROADMAP.md amendments moved from Plan 26-05 Task 2 to this plan so Waves 2-4 read correct source-of-truth text"

patterns-established:
  - "Declared-but-not-yet-bodied entry-points (substrate before bodies)"
  - "Dist-name vs import-name decoupling per D-04"
  - "Console-script back-compat shim (one-milestone deprecation window)"

requirements-completed: [PACK-01, PACK-02, PACK-03]

# Metrics
duration: ~12min
completed: 2026-05-16
---

# Phase 26 Plan 01: Packaging substrate — dist rename to mcp-contracts + pytest11 entry point + cli.py version fix + source-of-truth doc amendments

**`pyproject.toml` rewritten to ship as `mcp-contracts` with both console scripts and the `pytest11` entry-point declared; `cli.py:974` patched to look up the new dist name; REQUIREMENTS.md PACK-03 + ROADMAP.md Phase 26 Goal/SC1 amended so Waves 2–4 read correct source-of-truth text.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-16T06:31:00Z (approx)
- **Completed:** 2026-05-16T06:43:34Z
- **Tasks:** 3
- **Files modified:** 4 (pyproject.toml, src/mcp_test_framework/cli.py, .planning/REQUIREMENTS.md, .planning/ROADMAP.md)
- **Tests added:** 0 (this is a declarative-substrate plan; Plan 26-04 lands the wheel-shape regression gate)

## Accomplishments

- **Dist rename to `mcp-contracts` landed at the `[project]` level** (D-01). `uv sync` re-installs the project as `mcp-contracts==0.1.0` — confirmed in the Task 1 verification output.
- **Both console scripts declared.** `mcp-contracts` is the primary (D-05); `mcp-test-framework` is the v1.4 deprecation shim (D-06) pointing at the not-yet-created `_deprecated_script.py` wrapper (lands in Plan 26-02). hatchling accepts string references at metadata-parse time even though the module body doesn't exist on disk yet — verified by `uv sync` exiting 0.
- **`[project.entry-points.pytest11]` declared** (D-09 / PACK-01) — operators no longer need `pytest_plugins=[...]` in their conftest once Plan 26-02 lands `_plugin.py`. The entry-point string `mcp_test_framework = "mcp_test_framework._plugin"` is the load-bearing piece that Plan 26-04's wheel-shape gate asserts appears verbatim in `dist-info/entry_points.txt`.
- **`cli.py:974` patched** — `metadata.version("mcp-contracts")` (was `"mvp-test-framework"`). The `version` command now resolves to `0.1.0` via the freshly-installed dist metadata (`uv run python -m mcp_test_framework.cli version` confirmed). Module docstring discrepancy block refreshed to the post-rename truth.
- **Source-of-truth docs amended** (revision 1, plan-checker Issue #5): REQUIREMENTS.md PACK-03 + ROADMAP.md Phase 26 Goal + SC1 now reference `mcp-contracts` (D-01), TestPyPI scope (CONTEXT.md "Claude's Discretion"), and D-02 closed-by-non-applicability for the shim. Moved from Plan 26-05 Task 2 so Waves 2–4 don't execute against stale text.
- **Zero new dependencies.** Phase 26 adds nothing to `[dependency-groups] dev`; the wheel-shape gate (Plan 26-04) uses stdlib `zipfile`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `pyproject.toml`** — `9ee9568` (feat)
2. **Task 2: Patch `cli.py:974` + module docstring** — `6c69f11` (fix)
3. **Task 3: Amend REQUIREMENTS.md PACK-03 + ROADMAP.md Phase 26 Goal/SC1** — `8eb16c8` (docs)

## Files Created/Modified

- `pyproject.toml` — Three changes:
  1. `[project] name = "mcp-contracts"` (was `"mvp-test-framework"`)
  2. `[project.scripts]` block: added `mcp-contracts = "mcp_test_framework.cli:app"` (primary), changed `mcp-test-framework` script to point at `mcp_test_framework._deprecated_script:main` (shim wrapper, body in Plan 26-02)
  3. New `[project.entry-points.pytest11]` table with `mcp_test_framework = "mcp_test_framework._plugin"`
  4. Hatch comment refresh (line range 102-105 → 102-108): cite D-01/D-04 + hatch discussion #554 about `packages` auto-including `py.typed` markers
  - UNCHANGED: hatch `packages = ["src/mcp_test_framework"]`, `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]`, `[dependency-groups] dev`, `[tool.ruff]`, `[tool.pyright]`, `[build-system]`, `requires-python`, `version`, `description`, `readme`, `dependencies`
- `src/mcp_test_framework/cli.py` — Two edits:
  1. `cli.py:974` — `metadata.version("mvp-test-framework")` → `metadata.version("mcp-contracts")` with refreshed inline comment citing D-01
  2. Module docstring (lines 27, 30-33) — refreshed `version` reads-from line and the four-line "Distribution-name vs package-name discrepancy" block, now showing primary `mcp-contracts` + legacy shim `mcp-test-framework` per D-05/D-06
- `.planning/REQUIREMENTS.md` — PACK-03 row amended (line 26)
- `.planning/ROADMAP.md` — Phase 26 Goal (line 105) and SC1 (line 109) amended

### pyproject.toml diff (essential lines)

```toml
# Before
[project]
name = "mvp-test-framework"
...
[project.scripts]
mcp-test-framework = "mcp_test_framework.cli:app"

# After
[project]
name = "mcp-contracts"
...
[project.scripts]
mcp-contracts = "mcp_test_framework.cli:app"
mcp-test-framework = "mcp_test_framework._deprecated_script:main"

[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"
```

### cli.py:974 diff (single-line essential change)

```python
# Before
v = metadata.version("mvp-test-framework")  # distribution name, NOT importable package

# After
v = metadata.version("mcp-contracts")  # Phase 26 D-01: distribution name (NOT importable package)
```

### REQUIREMENTS.md PACK-03 diff

```markdown
# Before
- [ ] **PACK-03**: Operator can `pip install mcp-test-framework` and `uv add mcp-test-framework` successfully — PyPI distribution name corrected from `mvp-test-framework` to `mcp-test-framework`; one-milestone deprecation shim under the old name redirects to the new (drops in v1.5).

# After
- [ ] **PACK-03**: Operator can `pip install mcp-contracts` and `uv add mcp-contracts` successfully — PyPI distribution name corrected from the planning-stage placeholder `mvp-test-framework` to the final shipping name `mcp-contracts` (Phase 26 D-01; the originally-targeted `mcp-test-framework` is taken on PyPI by an unrelated project per D-03). Per D-02: no PyPI shim under the legacy name is needed because the project was never published. A console-script shim under `mcp-test-framework` is retained in v1.4 for local-install compatibility (Phase 26 D-06) and drops in v1.5.
```

### ROADMAP.md Phase 26 Goal diff

```markdown
# Before
**Goal**: Operator adds `mcp-test-framework` to `pyproject.toml`, runs `uv add` / `pip install`, and their pytest auto-loads ...

# After
**Goal**: Operator adds `mcp-contracts` to `pyproject.toml`, runs `uv add` / `pip install`, and their pytest auto-loads ...
```

### ROADMAP.md Phase 26 SC1 diff

```markdown
# Before
1. Operator running `pip install mcp-test-framework` (corrected from `mvp-test-framework`) or `uv add mcp-test-framework` succeeds against the PyPI-published wheel; a one-milestone shim under the old name redirects.

# After
1. Operator running `pip install mcp-contracts` or `uv add mcp-contracts` succeeds against the **TestPyPI**-published wheel (Phase 26 ships a TestPyPI dry-run + local-install verification; production PyPI publish defers to Phase 30 CLOSE-01..04). No PyPI shim under the legacy `mvp-test-framework` name is needed — D-02: the project has never been published, so PACK-03's "one-milestone shim" clause is closed-by-non-applicability.
```

## Decisions Made

None — followed plan as specified. All three tasks executed exactly per the plan's `<action>` blocks (decision content was locked in CONTEXT.md as D-01..D-09 + the "Claude's Discretion" TestPyPI-scope decision; this plan is the mechanical execution).

## Deviations from Plan

None — plan executed exactly as written.

The three tasks landed verbatim per their `<action>` blocks. No bugs surfaced, no auto-fixes needed, no architectural questions raised.

**Total deviations:** 0
**Impact on plan:** None — plan executed cleanly.

## Issues Encountered

None.

`uv sync` accepted the new metadata at the first attempt (the `mcp-contracts==0.1.0` install line in the Task 1 verification output is the load-bearing confirmation that hatchling accepts the entry-point string references even though `_plugin` and `_deprecated_script` don't yet exist on disk — entry-point strings are imported lazily by their consumers, not eagerly at metadata-parse time).

The `version` command resolving to `0.1.0` immediately after the `uv sync` reinstall confirms the end-to-end dist-metadata path is wired correctly.

## Forward References (Not Yet Created)

The following entry-point strings reference modules that **don't yet exist on disk** — Plan 26-02 closes the loop:

- `mcp_test_framework._plugin` (referenced from `[project.entry-points.pytest11]`)
- `mcp_test_framework._deprecated_script:main` (referenced from `[project.scripts] mcp-test-framework`)

This is **intentional and safe** because Python's entry-point dispatch is lazy — the strings are only imported when pytest scans `pytest11` entry points (Plan 26-02 timeframe) and when an operator invokes `mcp-test-framework` from the shell (also Plan 26-02 timeframe). `uv sync` validates only that the metadata syntax is well-formed, not that the referenced modules exist.

## User Setup Required

None — no external service configuration required. Phase 26 is build-time / packaging metadata only.

## Next Phase Readiness

- **Wave 2 (Plan 26-02) is unblocked.** It can now safely create `src/mcp_test_framework/_plugin.py` and `src/mcp_test_framework/_deprecated_script.py` — both module paths are already declared in `pyproject.toml` and will be picked up by pytest's `pytest11` scan and the `mcp-test-framework` console-script dispatch as soon as the modules exist on disk.
- **Wave 1 sibling (Plan 26-03)** edits `contracts/` only — zero file overlap with this plan; can land in parallel (or has already landed in parallel via the orchestrator wave).
- **Plan 26-04 wheel-shape gate** has clear assertions it must enforce: the `dist-info/entry_points.txt` of the built wheel must contain the `[pytest11] mcp_test_framework = mcp_test_framework._plugin` line and both `[console_scripts]` entries verbatim.
- **Plan 26-05 Task 2 is now empty** of source-of-truth amendments — they landed here. Plan 26-05 should be re-scoped or its Task 2 closed-by-non-applicability.

## Self-Check: PASSED

- `pyproject.toml` exists; contains `name = "mcp-contracts"`, both `[project.scripts]` entries, the `[project.entry-points.pytest11]` table, the entry-point string `mcp_test_framework = "mcp_test_framework._plugin"`. Verified via the Task 1 grep matrix.
- `src/mcp_test_framework/cli.py` exists; line 974 calls `metadata.version("mcp-contracts")`; docstring discrepancy block updated. `uv run python -c "from mcp_test_framework.cli import app; print('OK')"` printed `OK`; `uv run python -m mcp_test_framework.cli version` printed `0.1.0`.
- `.planning/REQUIREMENTS.md` PACK-03 row contains `pip install mcp-contracts` and cites `Phase 26 D-01`. Verified via grep.
- `.planning/ROADMAP.md` Phase 26 Goal/SC1 contain `mcp-contracts`, `TestPyPI`, `closed-by-non-applicability`. Verified via grep + the Task 3 `uv run python -c` assertion script.
- Commits verified present in `git log --oneline -5`: `9ee9568` (Task 1), `6c69f11` (Task 2), `8eb16c8` (Task 3).
- `grep mvp-test-framework pyproject.toml src/mcp_test_framework/cli.py` returned exit code 1 (no matches) — legacy dist name fully purged from both files.

---
*Phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s*
*Plan: 01*
*Completed: 2026-05-16*
