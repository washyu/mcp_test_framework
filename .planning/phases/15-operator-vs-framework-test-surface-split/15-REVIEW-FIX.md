---
phase: 15-operator-vs-framework-test-surface-split
fixed_at: 2026-05-11T00:00:00Z
review_path: .planning/phases/15-operator-vs-framework-test-surface-split/15-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 2
skipped: 1
status: partial
---

# Phase 15: Code Review Fix Report

**Fixed at:** 2026-05-11
**Source review:** .planning/phases/15-operator-vs-framework-test-surface-split/15-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03)
- Fixed: 2 (WR-01, WR-03)
- Skipped: 1 (WR-02 -- deferred to SEED-015)

In-scope filter for this run is `critical_warning`. WR-02 is in-scope by
severity but intentionally deferred per orchestrator instruction; see the
Skipped Issues section for the rationale. INFO findings (IN-01..IN-06) are
outside the `critical_warning` scope and were not attempted.

## Fixed Issues

### WR-01: Relocation-induced `parents[1]` bug missed in `test_runner_live_smoke.py`

**Files modified:** `tests/framework/test_runner_live_smoke.py`
**Commit:** 122761c
**Applied fix:** Updated three call sites (lines 33, 47, 57) from
`Path(__file__).resolve().parents[1]` to
`Path(__file__).resolve().parents[2]`. After Plan 15-01 relocated the file
from `tests/` into `tests/framework/`, `parents[1]` was resolving to
`<repo>/tests/`; `parents[2]` now correctly resolves to the repo root.
Verified empirically by running `Path('tests/framework/test_runner_live_smoke.py').resolve().parents[2]`
in a `uv run python` shell -- it returns the repo root as expected. The file
is gated by `pytest.mark.live_homelab` and not collected by default, so the
live smoke run was not exercised in this fix verification; correctness of
the index change is established by the empirical path resolution above.

### WR-03: `--raw` help text is now stale with respect to `--with-framework`

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** da92157
**Applied fix:** Replaced the `--raw` help-string assertion that the flag is
"Equivalent to `uv run pytest tests/contract/` modulo the config pre-flight
gate" with text that surfaces the `--with-framework` composition explicitly:

> "Bypass the domain UI wrapper and stream pytest's native output. All flags
> forward verbatim to pytest. Default scope is tests/contract; pass
> --with-framework to also include tests/framework. The config pre-flight
> gate still runs."

Verified by running `uv run mcp-test-framework run --help` and confirming
the new wording renders in the Typer-generated `--help` output. Python AST
parse of the modified file succeeded.

## Skipped Issues

### WR-02: README sample-run output references stale test paths

**File:** `README.md:151-162`
**Reason:** Deferred to SEED-015 (library-mode delivery). The orchestrator
explicitly directed that the "Sample green run" section will be rewritten
wholesale if the framework pivots to library-mode delivery in v1.3+, and
patching the path strings now would be churn against a section that is
slated for full replacement. This is an explicit deferral decision, not a
fixer failure.
**Original issue:** The pytest progress summary names test files at their
pre-Phase-15 locations (`tests\smoke\...`, `tests\test_homelab_...`,
`tests\unit\...`) and quotes a headline count (`67 passed, 5 deselected`)
that no longer matches the post-split default scope of `tests/contract/`
only. The README prose at lines 168-170 partially acknowledges the new
layout, which makes the inconsistency more visible. IN-06 was folded into
this finding by the reviewer; it is skipped on the same rationale.

---

_Fixed: 2026-05-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
