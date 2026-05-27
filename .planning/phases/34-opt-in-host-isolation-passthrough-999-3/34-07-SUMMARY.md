---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 07
subsystem: config-init-scaffold-emitter
tags: [config-init, scaffold-emitter, operator-facing-docs, isol-01]
requires:
  - "34-01 (Config.host_isolation Literal field with strict default)"
  - "34-02 (operator-tone literal_error rejection branch -- doc-pointer text alignment)"
provides:
  - "_format_tools_yaml_scaffold emits PRECEDING-comment-block + 'host_isolation: strict' line between version: 2 and test_code: blocks"
  - "Round-trip pin -- emitted scaffold parses back into Config with host_isolation == 'strict'"
  - "Verbatim 5-line trade-off comment-block copy consumed by docs plan 34-08 README + LIBRARY-MODE.md authoring"
affects:
  - src/mcp_test_framework/cli.py
  - tests/framework/test_config_init_cli.py
tech_stack_added: []
tech_stack_patterns:
  - "Preceding-comment-block style matches surrounding scaffold visual rhythm (every other field in this scaffold uses preceding comments per RESEARCH Finding 7 + Open Question 2 recommendation)"
  - "Fallback scaffold path at cli.py:1254 inherits new line automatically via _format_tools_yaml_scaffold([]) -- no separate edit needed (RESEARCH Finding 7 verified)"
key_files_created: []
key_files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/test_config_init_cli.py
decisions:
  - "Comment-block style is PRECEDING block (not end-of-line) -- matches every other field in the scaffold; end-of-line would break the visual rhythm"
  - "Default-value comment dropped from the line itself -- the first comment-line establishes '(default)' so an inline '# (default: strict)' would be redundant"
  - "Unit-level test invokes _format_tools_yaml_scaffold([]) directly (no live MCP server needed) -- the empty-tools path still exercises the header that carries the host_isolation block"
  - "Round-trip test passes test_code as bare kwarg (TestCodeConfig); the scaffold itself also emits a test_code block but the bare kwarg covers the Config construction shape independent of the YAML overlay"
metrics:
  duration: ~3 minutes
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-05-27
---

# Phase 34 Plan 07: config-init scaffold emits host_isolation: strict Summary

**One-liner:** Updates `_format_tools_yaml_scaffold` to emit a 5-line preceding-comment block followed by `host_isolation: strict` between the `version: 2` and `test_code:` blocks, so operators who run `mcp-contracts config-init` after Phase 34 ships see the new knob with the strict vs passthrough trade-off explained inline; pinned by a new round-trip test in `tests/framework/test_config_init_cli.py`.

## Inserted Scaffold Block (verbatim, for plan 34-08 doc reference)

The six new string literals inserted into `_format_tools_yaml_scaffold` (between `"version: 2\n"`/`"\n"` and `"# test-code codegen + fixture output path. REQUIRED.\n"`):

```python
"# Host isolation mode. 'strict' (default) isolates the spawned MCP\n"
"# subprocess from your operator host (allowlist + tempdir HOME redirect +\n"
"# null keyring backend). 'passthrough' hands the operator's full env to\n"
"# the subprocess so live credentials and keyring are reachable; in this\n"
"# mode pytest-xdist worker count is clamped to 1.\n"
"host_isolation: strict\n"
```

Rendered scaffold excerpt (what an operator sees in their generated `config.yaml`):

```yaml
# Schema version. This release accepts version 2.
version: 2

# Host isolation mode. 'strict' (default) isolates the spawned MCP
# subprocess from your operator host (allowlist + tempdir HOME redirect +
# null keyring backend). 'passthrough' hands the operator's full env to
# the subprocess so live credentials and keyring are reachable; in this
# mode pytest-xdist worker count is clamped to 1.
host_isolation: strict

# test-code codegen + fixture output path. REQUIRED.
```

Docs plan 34-08 should copy the **5-line comment-block prose** verbatim when authoring the README and `docs/LIBRARY-MODE.md` worked example so the scaffold copy and the documentation prose align.

## Emit Order Confirmation

The scaffold now emits top-level fields in this order, matching the `Config` model field order:

1. `ollama:` (sub-mapping)
2. `mcp_server:` (sub-mapping)
3. `judge_timeout_seconds: 120`
4. `version: 2`
5. **`host_isolation: strict`** (NEW)
6. `test_code:` (sub-mapping)
7. `tools:` (sub-mapping)

Verified at runtime by the acceptance-criterion smoke check:

```
uv run python -c "from mcp_test_framework.cli import _format_tools_yaml_scaffold; ..."
=> order OK
```

## Fallback Scaffold Path -- Unchanged

`src/mcp_test_framework/cli.py:1254` (the `FileNotFoundError`/no-tools-discovered arm of `config-init`) was NOT separately edited. It calls `_format_tools_yaml_scaffold([])` (empty tools list), so the new line is inherited automatically. RESEARCH Finding 7 verified this in advance; the round-trip pin uses the same `_format_tools_yaml_scaffold([])` call shape and exercises the fallback's exact code path.

## Tasks Completed

| Task | Name                                                                          | Commit  | Files                                       |
| ---- | ----------------------------------------------------------------------------- | ------- | ------------------------------------------- |
| 1    | Write failing pin for host_isolation scaffold emit (RED)                      | 17c084f | tests/framework/test_config_init_cli.py     |
| 2    | Emit host_isolation: strict in config-init scaffold (GREEN)                   | c952cac | src/mcp_test_framework/cli.py               |

## Verification

All plan-level `<verification>` and `<success_criteria>` checks pass:

- `uv run pytest tests/framework/test_config_init_cli.py -x -k host_isolation` => 1/1 passed (new pin)
- `uv run pytest tests/framework/test_config_init_cli.py -x` => 3/3 passed (4 live tests deselected -- no live server in this run; expected)
- `uv run pytest tests/framework/` => 785 passed, 2 skipped, 18 deselected, 1 xfailed (no regression)
- `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x` => 1/1 passed (Phase 22 D-04 gate clean -- the new scaffold comment text avoids planning-ID tokens)
- `grep -nE '"host_isolation: strict' src/mcp_test_framework/cli.py` => match at L1785 (new scaffold emit line; the earlier L365 match is the pre-existing operator-tone error branch text)
- `grep -nE '"# Host isolation mode\. .strict. \(default\)' src/mcp_test_framework/cli.py` => match in new block
- `grep -nE 'pytest-xdist worker count is clamped to 1' src/mcp_test_framework/cli.py` => match in new block
- Emit-order smoke check (`version < host_isolation < test_code` by index): OK

## Test Added

`tests/framework/test_config_init_cli.py::test_config_init_scaffold_emits_host_isolation_strict`

Unit-level (no `@live_homelab` marker). Three assertions:

1. `"host_isolation: strict" in scaffold_text` -- emit line present
2. `"# Host isolation mode." in scaffold_text` -- preceding comment block present
3. `parsed.host_isolation == "strict"` -- round-trip: emitted scaffold parses back into Config with the strict default preserved

## Deviations from Plan

None - plan executed exactly as written.

Plan 34-07's tasks dropped in cleanly:
- Path B from Task 1 (new test function) was the right path -- existing tests use the `CliRunner`-invoked `config-init` subcommand path; no existing test invokes `_format_tools_yaml_scaffold` as a function, so a new unit-level test is the right shape.
- The Task 2 insertion landed verbatim from the plan; the comment block has no planning-ID tokens, so the Phase 22 D-04 gate stayed green without rewording.
- Fallback path inheritance verified per RESEARCH Finding 7 -- no separate edit.

## Authentication Gates

None.

## Threat Flags

None. The plan's threat register (T-34-07-01..04) is fully addressed:
- T-34-07-01 (Tampering -- comment-block drift): mitigated by the round-trip test's `"# Host isolation mode."` substring assertion; future doc-text drift breaks the test.
- T-34-07-02 (Info disclosure -- operator misses the new knob): mitigated by uncommented emit with strict default spelled.
- T-34-07-03 (Tampering -- emit order regresses): mitigated by the acceptance-criterion order check (`version < host_isolation < test_code`).
- T-34-07-04 (Repudiation -- fallback path fails to inherit): accept; RESEARCH Finding 7 verified inheritance is automatic via `_format_tools_yaml_scaffold([])` shared call.

## Known Stubs

None. The scaffold emit is fully wired, the round-trip parses, and the doc plan 34-08 will land the README + `docs/LIBRARY-MODE.md` prose that the comment-block trade-off copy aligns with.

## TDD Gate Compliance

Per-task `tdd="true"` discipline observed:

- **Task 1 (RED gate):** `test_config_init_scaffold_emits_host_isolation_strict` added in commit `17c084f` as a `test(34-07): ...` commit. Ran `uv run pytest tests/framework/test_config_init_cli.py -x -k host_isolation` -- exited non-zero with AssertionError on `'host_isolation: strict' in scaffold_text`. RED phase confirmed.
- **Task 2 (GREEN gate):** scaffold block inserted in commit `c952cac` as a `feat(34-07): ...` commit. Re-ran the same pytest invocation -- exited zero. Full framework suite -- 785 passed, no regressions. GREEN phase confirmed.
- **REFACTOR gate:** not invoked; the new comment block follows the existing scaffold's hand-formatted-string idiom verbatim and required no follow-up cleanup.

Commit messages use the project's `{type}({phase}-{plan}): {summary}` convention.

## Self-Check: PASSED

- `src/mcp_test_framework/cli.py` modified (lines 1780-1784 carry the new 5-line preceding comment block, line 1785 carries the `host_isolation: strict` emit line): FOUND
- `tests/framework/test_config_init_cli.py` modified (new test function at line 145): FOUND
- Commit `17c084f` (test 34-07): FOUND in git log
- Commit `c952cac` (feat 34-07): FOUND in git log
- pytest run on `tests/framework/test_config_init_cli.py -k host_isolation`: 1/1 passed
- pytest run on `tests/framework/`: 785 passed, 0 failed
- planning-ID gate (`test_no_planning_ids_in_src`): passes
- Fallback path inheritance: scaffold emit verified via `_format_tools_yaml_scaffold([])` call shape used by both the round-trip test and the `cli.py:1254` fallback arm
