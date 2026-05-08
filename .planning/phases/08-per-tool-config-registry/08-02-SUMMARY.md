---
phase: 08-per-tool-config-registry
plan: 02
status: complete
requirements: [TOOLCFG-01, TOOLCFG-06, TOOLCFG-07]
key_files:
  created: []
  modified:
    - src/mcp_test_framework/fixtures.py
    - tests/test_mcp_tool_contract.py
commits:
  - e6a1970 feat(08-02): add tool_config fixture + preflight warnings
  - f85fa96 feat(08-02): thread ToolConfig guards through TEST-01..10
---

## What was built

Runtime threading of `ToolConfig` through the test surface:

1. **`fixtures.py`** — new sync `tool_config` fixture (default function scope
   so it tracks the per-test parametrized `target_tool.name`); two new
   `_preflight` warning sites for D-14/D-18 (unknown `tools.*` keys) and D-12
   (explicit-target-overrides-skip).
2. **`tests/test_mcp_tool_contract.py`** — every test (TEST-01..10) gains a
   `tool_config: ToolConfig` parameter and a 2-line skip guard at the body's
   top (CD-05). TEST-05/06/07 gain judge-selection guards. TEST-08/09/10
   replace `{}` with `tool_config.call_arguments` (D-11).

## Guard placement (CD-05 chosen): inline at top of test bodies

Every test body now opens with:

```python
if tool_config.skip:
    pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
```

The `or "tool skipped via config"` fallback is defensive — Plan 01's
`_skip_requires_reason` validator enforces non-empty `skip_reason` at config
load, so the fallback never fires in practice. Kept for safety against
direct `ToolConfig(...)` construction in tests.

TEST-05/06/07 add a second guard immediately after the first, naming the
specific rubric ID:

```python
if tool_config.judges is not None and "clarity" not in tool_config.judges:
    pytest.skip(reason=f"judge 'clarity' not selected for tool {target_tool.name!r}")
```

(`"disambiguation"` / `"parameters"` for TEST-06 / TEST-07 respectively.)
The rubric ID `"parameters"` is the user-facing short form per D-10 /
TOOLCFG-04 — distinct from the prompt `dimension`
`"parameters_self_explanatory"`.

Both guards fire before any `await` in the body, preserving the Phase 04.1
cancel-scope invariant ("no anyio scope opened across yield" — for tests,
"no awaited fixture body opens a cancel scope before the skip resolves").

## Did Category-1 tests receive the uniform skip guard?

**Yes.** TEST-01 through TEST-04 (Category-1 deterministic schema tests) each
received the `tool_config: ToolConfig` parameter and the 2-line skip-on-config
guard. They do NOT receive the judge-selection guard (Category-1 isn't
judged), and they do NOT touch `call_tool` so `call_arguments` is irrelevant
to them.

The reasoning is uniform-coverage: TOOLCFG-07 demands "the run record shows
what was skipped and why". If a tool is `skip: true` and Category-1 still
ran, the user would see a partial-skip pattern (4 PASSED + 6 SKIPPED) rather
than the intended total-skip pattern (10 SKIPPED). The uniform guard makes
"skip a tool" mean what users mean by it.

## Two `_preflight` warning sites — exact format

**1. Unknown tool name (D-14 / D-18)** — emitted inside `_preflight`
*after* the MCP `list_tools()` handshake succeeds:

```
tools.<unknown>:
    "tools.{unknown_name!r} configured but not in discovered tool list "
    "(available: {sorted(discovered_names)!r}); config entry has no effect"
```

Iterates `sorted(set(config.tools) - discovered_names)` so output is stable.
`UserWarning`, `stacklevel=2`. Visible through pytest's default warnings
summary; non-fatal.

**2. Explicit target overrides configured skip (D-12)** — emitted *after*
the existing target-membership check:

```
target.tool_name=<X>:
    "target.tool_name={X!r} explicitly set; "
    "overriding tools.{X!r}.skip=True for this run"
```

Fires only when `config.target.tool_name` is set AND a `tools.<that_name>`
entry exists AND that entry has `skip=True`. Fires exactly once per session
(it's inside `_preflight`, which is `autouse=True, scope="session"`).

## TOOLCFG-06 default-behavior confirmation

With no `tools:` block in the active YAML overlay (the current
`config.yaml` in this worktree has none), `Config().tools == {}` and every
test resolves `config.tools.get(target_tool.name, ToolConfig())` → a fresh
default `ToolConfig()`:

- `skip=False` → first guard never triggers
- `judges=None` → second guard's `is not None` check short-circuits, all
  three judged tests run unchanged
- `call_arguments={}` → TEST-08/09/10 receive `{}` exactly as before

Concretely: `pytest tests/test_mcp_tool_contract.py --collect-only -q`
collects **580 tests** (10 functions × 58 discovered tools — same count as
the Phase 07 verified baseline). `tests/unit/` + `tests/test_isolation.py`
remain at 57/57 PASS. Default behavior is preserved bit-for-bit.

## Pre-existing live-MCP failures (NOT caused by this plan)

`uv run pytest tests/test_mcp_tool_contract.py` against the live homelab-mcp
will still fail on:
- `test_description_disambiguation[list_registered_servers]` — the v1.0-deferred
  upstream-fix item.
- `test_empty_args_call_returns_non_error[ssh_discover]` etc. — tools whose
  `inputSchema.required` is non-empty fail with `isError=True`. **This is
  exactly what Plan 04's worked example resolves** by writing
  `tools.ssh_discover.call_arguments` into the canonical YAML — Plan 04
  ships the dedicated tests + example.

## Verification evidence

- `uv run python -c "import inspect; from mcp_test_framework import fixtures; src = inspect.getsource(fixtures); ..."` → `OK`
- `uv run python -c "import re; src = open('tests/test_mcp_tool_contract.py').read(); count_sig = len(re.findall(r'tool_config: ToolConfig', src)); ..."` → `OK` (10 sigs, 3 call_arguments substitutions, all 3 judge guards present, 10 skip guards)
- `uv run ruff check src/mcp_test_framework/fixtures.py tests/test_mcp_tool_contract.py` → `All checks passed!`
- `uv run pytest tests/unit/ tests/test_isolation.py` → **57 passed in 8.35s**
- `uv run pytest tests/test_mcp_tool_contract.py --collect-only -q` → **580 tests collected** (same shape as Phase 07 baseline)

## Self-Check: PASSED

- [x] All 2 tasks executed and verified
- [x] Each task committed individually
- [x] Plan 04.1 cancel-scope invariant honored (sync fixture, no anyio scope across yield; pytest.skip fires before any await)
- [x] Default `tools={}` preserves Phase 07 baseline (580 tests collected, 57 unit tests pass)
- [x] All 6 acceptance-criteria grep counts pass
