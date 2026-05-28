---
id: SEED-010
status: delivered
planted: 2026-05-08
planted_during: v1.1 manual UAT exploration (formalized at v1.2 milestone framing 2026-05-08)
trigger_when: N/A — delivered
delivered: 2026-05-13
delivered_in: v1.3 — `tests/contract/` + `tests/framework/` split shipped (operator runner scopes to contract tests; framework self-tests run separately)
scope: Small-Medium
target_milestone: v1.2 (cohort with SEED-007/008/009/011)
---

# SEED-010: Operator vs framework test surface split  *[DELIVERED v1.3]*

## Why This Matters

`tests/` currently mixes two audiences in one directory: ~107 framework self-tests (config validation, reporter contract, isolation, banned-imports, snippet correctness) plus ~20 contract tests against the SUT (`test_mcp_tool_contract.py`). When an operator runs `mcp-test-framework run`, pytest collects all 127 cases — 84 % of what they see is the framework testing itself, not their MCP server.

Memory: `Operator vs framework test surface (SEED-010) — 5th operator-vs-dev pattern in one UAT session — v1.2 theme should be "operator-first design"` (2026-05-08).

## When to Surface

**Active for v1.2.** Milestone framing has already selected this seed for inclusion.

## Scope Estimate

**Small-Medium.** Mostly mechanical — `git mv` test files into the right subdirectory, update `pytest_collection_modifyitems` or pytest markers so the operator runner only collects `tests/contract/`. The non-trivial part is deciding the split rules cleanly and updating CI / docs.

## Components

### 1. Folder split

```
tests/
  contract/        # operator-facing: tests against the SUT contract
    test_mcp_tool_contract.py
    test_*tool*.py (any future per-tool contract files)
    conftest.py    # fixtures specific to running against a live MCP server
  framework/       # internal: framework self-tests
    test_config.py
    test_reporter.py
    test_isolation*.py
    test_banned_imports.py
    test_readme_snippets.py
    test_*.py      # all current framework self-tests
    conftest.py    # framework-internal fixtures
  conftest.py      # shared (pytest_generate_tests hook for tool discovery, etc.)
```

### 2. Operator runner default scope

`mcp-test-framework run` collects only `tests/contract/` by default. Framework self-tests (`tests/framework/`) are dev-only and run via `uv run pytest tests/framework/` or a `--all`/`--with-framework` opt-in flag.

### 3. CI matrix

CI runs both `tests/contract/` (against fixtures or a stable SUT) and `tests/framework/`. Contract suite is what downstream operators care about.

## Sequencing Within v1.2

**Lands AFTER SEED-011** (hybrid runner with domain UI). Runner contract drives the split — once the runner is the operator's interface, deciding what scope it collects becomes well-defined. Memory: `Decide BEFORE SEED-010 folder split.`

## Tradeoffs

- Operators currently running `uv run pytest tests/` see fewer cases — a clearer surface but a behavior change. Hybrid runner (SEED-011) absorbs this so they don't invoke pytest directly.
- Framework contributors run two test suites instead of one — minor friction, mitigated by `pytest tests/` continuing to collect both.
- Contract tests can `from src.mcp_test_framework import ...` without leaking framework internals into operator-visible failures.

## Breadcrumbs

- `tests/test_mcp_tool_contract.py` — the canonical operator-facing test (parametrized over discovered tools)
- `tests/conftest.py:127-139` — `pytest_generate_tests` hook (shared)
- `tests/test_*.py` (framework self-tests, ~107 cases)
- `src/mcp_test_framework/cli.py` `run` command — gains scope-selection logic if SEED-011 is the runner
- Existing GSD: `feedback_phase_scope_intent.md` — the operator-vs-dev pattern keeps recurring; this split institutionalizes the boundary

## Related Memories

- `Operator vs framework test surface (SEED-010)` (memory entry)
- `Hybrid runner with domain UI (SEED-011)` (memory entry; sequencing dependency)
