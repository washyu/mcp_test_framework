---
phase: 16-reporter-ux-overhaul
plan: 05
subsystem: reporter
tags: [bugfix, digest, judges, toolcfg-06, gap-closure]
gap_closure: true
gap_reference: 16-VERIFICATION.md gaps_remaining[0] (G-1)
requirements: [UX-01]
dependency_graph:
  requires:
    - 16-01 (RenderContext + _render_pre_run_digest + pre-run digest pipeline)
    - 16-02 (cli.py:run pre-run digest wiring at line 533)
    - models.py ToolConfig.judges TOOLCFG-06 (None / [] / subset semantic)
    - rubrics.py RUBRIC_IDS frozenset
  provides:
    - _runner._compose_judges_from_tool_configs(tools_config) helper
    - Truthful digest Judges-line for the TOOLCFG-06 None default case
  affects:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/cli.py
    - tests/framework/unit/test_runner_pre_run_digest.py
tech_stack:
  added: []
  patterns:
    - Pure composer helper next to its sibling (_compose_pre_run_skip_reasons),
      mirroring Phase 16 D-14 "no new module file" stance
key_files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py (+29 lines: import + helper)
    - src/mcp_test_framework/cli.py (-6 / +6 net 0; 5-line buggy loop replaced
      with single helper call + expanded comment block)
    - tests/framework/unit/test_runner_pre_run_digest.py (+100 lines: import
      additions + three new tests)
decisions:
  - "Helper placed in _runner.py next to _compose_pre_run_skip_reasons rather
    than cli.py: pure composer with no Typer/CLI coupling, testable without
    spinning the CliRunner wrapper, and code-locality with its existing
    sibling composer follows the Phase 16 D-14 'no new module file' stance."
  - "Switched the new tests from SimpleNamespace stubs to real ToolConfig
    instances. SimpleNamespace can't honestly distinguish judges-attribute-
    is-None from judges-attribute-is-absent; ToolConfig pins the TOOLCFG-06
    contract at the test boundary the same way models.py:98 pins it at the
    config-load boundary."
  - "Comment block at the cli.py call site cites the TOOLCFG-06 semantic
    + the prior bug + the 16-VERIFICATION.md G-1 reference inline so a
    future reader doesn't have to chase docs to understand why the helper
    is preferred over a one-line union loop."
metrics:
  duration_minutes: 7
  completed_at: 2026-05-12T16:05:12Z
  files_touched: 3
  loc_added: 135
  loc_removed: 6
  loc_net: +129
  commits: 3
---

# Phase 16 Plan 05: Digest Judges-Union Fix Summary

Replaced cli.py's buggy union loop (which silently collapsed `ToolConfig.judges=None` — the TOOLCFG-06 default meaning "run all rubrics" — to `[]` and produced a digest that lied about runtime behavior) with a pure `_compose_judges_from_tool_configs(tools_config)` helper in `_runner.py` that honors the three-way None / [] / subset semantic, and pinned the corrected behavior with three new regression tests.

## What Shipped

### Source

- **`src/mcp_test_framework/_runner.py`** (+29 lines)
  - New import: `from .rubrics import RUBRIC_IDS` (intra-package, top-of-file)
  - New helper `_compose_judges_from_tool_configs(tools_config: dict) -> list[str]` placed immediately after `_compose_pre_run_skip_reasons` (line ~631 in the new file). Pure function: expands `judges=None` to all `RUBRIC_IDS`, treats `[]` as no-op, passes subsets through, returns sorted de-duplicated list.

- **`src/mcp_test_framework/cli.py`** (−6 / +6 lines, net 0)
  - Replaced the 5-line `judges_set: set[str] = set(); for tool_cfg in cfg.tools.values(): for judge_name in getattr(tool_cfg, "judges", []) or []: judges_set.add(judge_name); judges = sorted(judges_set)` block at the old lines 510-516 with a single call: `judges = _runner._compose_judges_from_tool_configs(cfg.tools)`.
  - Comment block expanded inline to cite TOOLCFG-06 + the prior bug + the gap reference.
  - Both downstream `RenderContext` build sites (pre-run digest ctx + post-run summary rebuild) pick up the fix transparently via the unchanged `judges` local — no second edit needed.

### Tests

- **`tests/framework/unit/test_runner_pre_run_digest.py`** (+100 lines)
  - Expanded imports to include `_compose_judges_from_tool_configs` and `ToolConfig`.
  - Three new tests appended at end of file, exercising both the helper directly AND the renderer end-to-end via capsys:
    - `test_judges_line_lists_all_rubrics_when_judges_unset` — the G-1 regression case (TOOLCFG-06 None default).
    - `test_judges_line_reports_none_configured_when_judges_explicitly_empty` — pins `judges=[]` as the only path to `(none configured)`.
    - `test_judges_line_lists_subset_when_judges_explicit` — pins literal subset passthrough + sort + de-dup; disambiguation must not leak.

## Commits

| # | Hash      | Type | Message |
|---|-----------|------|---------|
| 1 | `4140a9a` | feat | add `_compose_judges_from_tool_configs` honoring TOOLCFG-06 |
| 2 | `08dd336` | fix  | replace cli.py judges union loop with helper call |
| 3 | `caa199f` | test | pin Judges-line semantic across None/[]/subset cases |

`git diff --stat a2bbdc0..HEAD`:
```
 src/mcp_test_framework/_runner.py                  |  29 ++++++
 src/mcp_test_framework/cli.py                      |  12 +--
 tests/framework/unit/test_runner_pre_run_digest.py | 100 +++++++++++++++++++++
 3 files changed, 135 insertions(+), 6 deletions(-)
```

Exactly the three files prescribed by the plan's `<success_criteria>` item 5 ("No collateral damage").

## Why the Helper Sits in `_runner.py` (not `cli.py`)

`_runner.py` is the natural home for pure composers — it already hosts `_compose_pre_run_skip_reasons`, `_compose_unparametrized_skips_from_config`, and the digest renderer itself. Placing `_compose_judges_from_tool_configs` next to its sibling composer (a) keeps the digest's data-assembly layer in one module, (b) lets unit tests exercise the helper without spinning up the Typer CLI wrapper or `CliRunner.invoke`, and (c) mirrors the Phase 16 D-14 "no new module file" stance — the helper is small enough that a dedicated module would over-engineer.

## Verification

### Eradication greps (all expected to return 0)

| Check | Pattern | Result |
|-------|---------|--------|
| Old `or []` bug pattern absent | `getattr(tool_cfg, "judges", []) or []` in cli.py | **0** |
| Old union loop variable absent | `judges_set: set[str] = set()` in cli.py | **0** |
| Old loop header absent | `for tool_cfg in cfg.tools.values():` in cli.py | **0** |

### Helper-wiring greps

| Check | Pattern | Result |
|-------|---------|--------|
| Helper exists in `_runner.py` | `_compose_judges_from_tool_configs` | 1 def line |
| Helper called from `cli.py` | `_compose_judges_from_tool_configs` | 1 call site |
| `RUBRIC_IDS` imported in `_runner.py` | `from .rubrics import RUBRIC_IDS` | 1 import |

### Test gates

| Suite | Result |
|-------|--------|
| `tests/framework/unit/test_runner_pre_run_digest.py` | **14 passed** (11 pre-existing + 3 new) |
| `tests/framework/unit/test_runner_explain.py` | included in 40-test suite below |
| `tests/framework/test_runner_verbosity.py` | included in 40-test suite below |
| Combined digest + explain + verbosity | **40 passed** |
| Inline smoke (`uv run python -c "..."`) | None default = `['clarity', 'disambiguation', 'parameters']`; `[]` = `[]`; `['clarity']` = `['clarity']` |
| UAT-mirror smoke (two ToolConfig() entries) | `['clarity', 'disambiguation', 'parameters']` — NOT `[]` |

### UAT-mirror

Running `_compose_judges_from_tool_configs` over the exact two-tool default-judges fixture from gap G-1 (the live 2026-05-12 UAT repro) now produces:

```
['clarity', 'disambiguation', 'parameters']
```

Pre-plan-05 this returned `[]`, which fed through to `Judges:      (none configured)` in the digest — exactly the lying-digest behavior recorded in `16-VERIFICATION.md` gaps_remaining[0]. The digest now matches what the runtime contract gates at `tests/contract/test_mcp_tool_contract.py:124,154,185` actually execute.

## Gap Closure Pointer

This plan closes `16-VERIFICATION.md` `gaps_remaining[0]` (G-1):

> Pre-run digest's `Judges:` line accurately reports the rubrics that will run for the configured tools (UX-01 / SC-1)

The next Phase 16 verification run can mark G-1 resolved. The pre-existing human-verification item (live Ollama judge run for UX-03 per-judge reasoning) is unchanged and was not in scope for this plan.

## Deviations from Plan

None — plan executed exactly as written.

The only minor observation: the `test_runner_pre_run_digest.py` file is touched by the `_preflight` autouse fixture (Phase 15 directory-rename residue noted in 16-VERIFICATION.md `env_note`), so the test runs required `MCPTF_CONFIG_FILE=config-v2-worktree.yaml` to satisfy the v2-schema config gate. This is a pre-existing environment quirk on the verification host and not a Phase 16 regression. The acceptance verification commands in the plan should be invoked with that env var on this host; CI environments that ship a v2 config alongside the suite do not need it.

## Self-Check: PASSED

All claimed artifacts verified present:

- `src/mcp_test_framework/_runner.py` — FOUND (modified, helper exported)
- `src/mcp_test_framework/cli.py` — FOUND (modified, helper called)
- `tests/framework/unit/test_runner_pre_run_digest.py` — FOUND (modified, 3 new tests pass)
- Commit `4140a9a` — FOUND
- Commit `08dd336` — FOUND
- Commit `caa199f` — FOUND
