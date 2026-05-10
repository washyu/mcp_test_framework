---
phase: 13-config-safety-opt-in-tool-selection
plan: 04
status: complete
completed: 2026-05-10
commits:
  - e0c524f
  - b916f0d
key-files:
  modified:
    - src/mcp_test_framework/models.py
    - src/mcp_test_framework/config.py
    - src/mcp_test_framework/fixtures.py
    - tests/conftest.py
    - tests/unit/test_config.py
    - tests/unit/test_reporter.py
  created: []
  deleted: []
---

# Plan 13-04: target-removal — SUMMARY

## What was built

Executed Phase 12 D-03's forward reference and Phase 13 D-11 + D-14. The v1.1
dual-mechanism for tool selection (allowlist + `target.tool_name` override) is
now a single mechanism (allowlist only).

### Task 1: Delete TargetConfig + Config.target field (D-11) — commit `e0c524f`

- **`src/mcp_test_framework/models.py`** — removed the entire `TargetConfig`
  class (23 lines: ConfigDict + `tool_name` field with TARGET_TOOL_NAME alias +
  the `_empty_to_none` field_validator). The surviving imports
  (`Optional`, `AliasChoices`, `field_validator`) are still used by `ToolConfig`,
  so the import block is unchanged.
- **`src/mcp_test_framework/config.py`** — removed `TargetConfig` from the
  imports block and the `target: TargetConfig = Field(...)` declaration. The
  pre-emptive comment "Plan 13-04 will remove the `target` field" is also gone.
- **`tests/unit/test_config.py`**
  - Added `test_phase_13_d_11_target_block_in_yaml_rejected` — proves
    `extra="forbid"` catches a stray `target:` block in a v2 YAML
    (defense-in-depth alongside SAFE-06's version refusal).
  - Updated `test_defaults` to assert `not hasattr(cfg, "target")` (was
    `cfg.target.tool_name is None`).

### Task 2: Delete target.tool_name consumers (D-14) — commit `b916f0d`

- **`src/mcp_test_framework/fixtures.py`** — removed lines 268-289:
  - the membership check (`if config.target.tool_name is not None: ...
    pytest.exit(...)`)
  - the override-warning block (`overriding tools.<name>.skip=True for this run`)

  These were the two `config.target.tool_name`-referencing blocks immediately
  below the unknown-tool warning. The unknown-tool warning itself is preserved.

  Stale comment at the `target_tool` fixture docstring (line 444 pre-change)
  updated to reference the allowlist semantics instead of `target.tool_name`.

- **`tests/conftest.py`** — `_resolve_tool_names` is now a single-branch
  function: discover (cached) then return the allowlist filter. The
  `explicit = config.target.tool_name; if explicit: return [explicit]`
  short-circuit is gone. Docstring updated.

- **`tests/unit/test_reporter.py`** — simplified the three `_FakeConfig` stubs
  Plan 13-03 added with inner `_Tgt` classes. The `_resolve_tool_names`
  function no longer reads `config.target`, so the fakes don't need it.

- Ruff auto-fix applied to `src/mcp_test_framework/fixtures.py` (I001 import
  ordering for the `mcp_test_framework.models import ToolConfig` line that
  the env-overlay strip in Plan 13-02 left mid-block).

## Acceptance gates — all green

- `grep -rnE "TargetConfig|config\.target|_Tgt" src/ tests/ --include="*.py"`
  returns zero matches.
- `grep -n "overriding tools" src/mcp_test_framework/fixtures.py` returns zero.
- `uv run python -c "from mcp_test_framework.models import TargetConfig"`
  raises `ImportError`.
- `uv run python -c "from mcp_test_framework.config import Config;
  print(hasattr(Config(yaml_file='/nonexistent'), 'target'))"` prints `False`.
- `uv run pytest tests/unit/ -q` → **176 passed, 1 warning** (the warning is
  the pre-existing reporter-double-import note; not introduced here).
- `uv run ruff check src/mcp_test_framework/fixtures.py tests/conftest.py`
  exits 0.

## Locked decisions implemented

- **D-11** — `TargetConfig` removed from the Pydantic model; v2 YAML with a
  stray `target:` block raises `ValidationError(extra_forbidden)`.
- **D-14** — Override-warning block at `fixtures.py:268-289` deleted; the
  allowlist replaces it. Operator `skip: true` is now respected unconditionally.

## Forward references closed

- **Phase 12 D-03** — `focus-<tool>.yaml + --config focus-<tool>.yaml` is now
  the sole single-tool-focus mechanism. No in-process target field exists.
- **Plan 13-05 MIGRATION doc** — the doc's "drop the `target:` block" guidance
  for v1→v2 porting is now load-truthful: the v2 validator rejects it.

## Deviations from plan

None — both tasks executed as specified. One ruff auto-fix on import sorting
(Rule 1 / not blocking) — same kind of auto-fix Plan 13-03 logged.

## Worktree-mode note

This plan was executed inline on the main working tree, not via a worktree
agent. The two parallel-spawned wave-3 agents (13-04 + 13-05) both failed the
`<worktree_branch_check>` step because `EnterWorktree` branched from an old
v1.1 release commit (`5e25c1e`) instead of the wave-2 HEAD (`db52b78`); the
agent permission policy denied the mandated `git reset --hard EXPECTED_BASE`
recovery step. Orchestrator reset both worktrees externally and switched
wave 3 to sequential inline execution.
