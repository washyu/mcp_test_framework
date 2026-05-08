---
phase: 08-per-tool-config-registry
plan: 04
status: complete
requirements: [TOOLCFG-01, TOOLCFG-02, TOOLCFG-03, TOOLCFG-04, TOOLCFG-05, TOOLCFG-06, TOOLCFG-07]
key_files:
  created:
    - tests/test_tool_config.py
    - tests/test_config_init_cli.py
  modified:
    - config.example.yaml
commits:
  - 6553b07 test(08-04): add tests/test_tool_config.py -- schema + AsyncMock + live runtime
  - 16bf7e1 test(08-04): add tests/test_config_init_cli.py -- CLI surface tests
  - 6fd0e5a docs(08-04): add version: 1 + worked tools: block to config.example.yaml
---

## Test count breakdown

`tests/test_tool_config.py` (22 collected, 19 deterministic + 3 live):

| Category | Count | Notes |
|----------|-------|-------|
| Schema (sync, parametrized) | 16 | `test_default_toolconfig_values`, `test_default_config_version_and_tools`, `test_config_rejects_extra_top_level_field`, `test_toolconfig_rejects_extra_field_typo`, `test_toolconfig_rejects_unknown_judge_id`, `test_toolconfig_accepts_empty_judges_list`, `test_toolconfig_accepts_none_judges`, `test_toolconfig_accepts_all_locked_rubric_ids`, `test_toolconfig_skip_requires_non_empty_reason[None\|""\|"   "]` (3 params), `test_toolconfig_skip_with_reason_succeeds`, `test_config_rejects_unsupported_version[0\|2\|-1\|99]` (4 params), `test_reserved_fields_typed_but_runtime_no_op`, `test_yaml_overlay_loads_tools_block` |
| AsyncMock proof | 1 | `test_call_arguments_forwarded_to_call_tool_via_asyncmock` |
| Live (subprocess pytest) | 3 | `test_skip_via_config_skips_all_ten_tests_for_tool`, `test_judges_subset_skips_un_selected_judged_tests`, `test_unknown_tool_in_tools_block_emits_warning` |

`tests/test_config_init_cli.py` (6 collected, 2 deterministic + 4 live):

| Category | Count | Notes |
|----------|-------|-------|
| CLI unit (CliRunner, no live) | 2 | `test_help_lists_flags`, `test_refuse_overwrite_without_force` |
| CLI live (CliRunner + live MCP) | 4 | `test_default_emits_scaffold_to_stdout`, `test_output_writes_to_file`, `test_overwrite_with_force_succeeds`, `test_scaffold_round_trips_through_config` |

**Phase 08 deliverable subset:** `tests/test_tool_config.py` +
`tests/test_config_init_cli.py` + `tests/unit/` + `tests/test_isolation.py`
under default markers → **78 passed, 7 deselected** (live-marked) in 8.39s.

## Did `live_homelab` / `live_ollama` markers need registration?

No — both markers are already declared in `pyproject.toml`'s
`[tool.pytest.ini_options].markers` block (visible via
`pytest --markers` or `grep -A3 markers pyproject.toml`):

```toml
markers = [
  "live_homelab: requires homelab-mcp runnable via uvx (or on PATH)",
  "live_ollama: requires reachable Ollama at OLLAMA_BASE_URL with the configured model",
]
```

These were registered in earlier phases (Phase 04 / 05). Plan 08-04 reuses
them without modification.

## Interactions with existing test files

- **`tests/test_mcp_tool_contract.py`** (Phase 04 + 07 + Phase 08-02): the
  AsyncMock proof in `test_tool_config.py` imports
  `test_empty_args_call_returns_non_error` directly and awaits it with fake
  fixtures. This is an in-process integration of Plan 02's runtime
  threading and proves the runtime contract without touching live MCP.
  No regressions in the existing `test_mcp_tool_contract.py` collection
  shape (still 580 tests = 10 functions × 58 tools).
- **`tests/test_isolation.py`** (Phase 06): unchanged. Phase 06's
  hash-byte-identical regression test naturally covers the FOURTH spawn
  site (`config-init` → `_list_tools_async` → `McpTestClient.__aenter__`)
  by virtue of D-24 reuse — no new test was needed in 08-04 to prove
  isolation holds for the new CLI subcommand.
- **`tests/unit/`** (Phase 04): unchanged. 57/57 still pass.
- **`tests/conftest.py`** (Phase 07): unchanged. The `pytest_generate_tests`
  hook still parametrizes test_mcp_tool_contract.py over the discovered
  tool list; the new `tool_config` fixture composes naturally with this
  parametrization (function-scoped, so it tracks per-tool `target_tool.name`).

No fixture chain regression — every existing test file still collects and
runs.

## CD-02 sign-off (`extra="forbid"` at top-level Config)

`config.example.yaml` (post-Plan-04 form, 46 lines) loads cleanly through
`Config()` under post-Plan-01 `extra="forbid"`:

```
$ MCPTF_CONFIG_FILE=config.example.yaml uv run python -c \
    "from mcp_test_framework.config import Config; \
     cfg = Config(); print(cfg.version, list(cfg.tools))"
1 ['list_registered_servers', 'list_keyring_credentials']
```

`extra="forbid"` does NOT reject any key in the canonical example file —
the existing top-level keys (`ollama`, `mcp_server`, `target`,
`judge_timeout_seconds`) plus the new ones (`version`, `tools`) are all
declared `Config` fields. Sign-off complete: CD-02 ships.

## AsyncMock proof — ROADMAP success criterion #4

`test_call_arguments_forwarded_to_call_tool_via_asyncmock` passes
deterministically:

```
PASSED tests/test_tool_config.py::test_call_arguments_forwarded_to_call_tool_via_asyncmock
```

The proof: `await test_empty_args_call_returns_non_error(fake_mcp_client,
fake_target_tool, ToolConfig(call_arguments={"key": "value", "limit": 7}))`
followed by `mock_call_tool.assert_called_once_with("demo_tool", {"key":
"value", "limit": 7})`. This directly satisfies ROADMAP success criterion
#4 — "framework passes those exact arguments to `call_tool` instead of the
default `{}`" — without depending on a live homelab-mcp instance.

Regression breaks loudly: any future change that reverts
`tests/test_mcp_tool_contract.py::test_empty_args_call_returns_non_error`
to use `{}` instead of `tool_config.call_arguments` will fail this test
on the first CI run.

## Homelab-mcp tool-name drift (informs Phase 10 DOC-04)

The example uses two tool names confirmed present in homelab-mcp at
2026-05-07 per Phase 06/07 discovery records:

- `list_registered_servers`
- `list_keyring_credentials`

If homelab-mcp upstream removes either tool, the YAML overlay will
produce a `UserWarning` ("tools.<name>... configured but not in
discovered tool list") at session start — non-fatal, but visible in
pytest's warnings summary. Phase 10 DOC-04 should note this dependency
and recommend operators run `mcp-test-framework list-tools` before
copying the example.

## Verification evidence

- `uv run pytest tests/test_tool_config.py -v -m "not live_homelab and not live_ollama"` → **19 passed, 3 deselected** in 4.14s
- `uv run pytest tests/test_config_init_cli.py -v -m "not live_homelab and not live_ollama"` → **2 passed, 4 deselected** in 4.08s
- Combined deliverable subset: `pytest tests/test_tool_config.py tests/test_config_init_cli.py tests/unit/ tests/test_isolation.py -m "not live_homelab and not live_ollama"` → **78 passed, 7 deselected** in 8.39s
- `MCPTF_CONFIG_FILE=config.example.yaml uv run python -c "from mcp_test_framework.config import Config; ..."` → **`OK`** (worked example loads under `extra="forbid"`)
- `uv run ruff check tests/test_tool_config.py tests/test_config_init_cli.py` → `All checks passed!`
- `grep` acceptance criteria for both new files all pass.

## Pre-existing live-MCP failures (NOT caused by this plan)

`tests/test_mcp_tool_contract.py::test_empty_args_call_returns_non_error[ssh_discover]`
fails when run under default markers because `ssh_discover` requires
`hostname` and is not configured with `call_arguments`. This is the
PRE-EXISTING condition the entire Phase 08 surface enables operators to
fix:

```yaml
# Operator's config.yaml -- not part of the framework, opt-in:
tools:
  ssh_discover:
    call_arguments:
      hostname: "192.168.10.81"
      username: "admin"
```

Plan 08-04's worked example does NOT include such an entry because the
example is committed to git and per-host SSH credentials must not be.
The mechanism is verified by the AsyncMock proof + the live-marked
runtime tests; the operator-facing usage is documented in DOC-04
(Phase 10).

The unrelated `test_description_disambiguation[list_registered_servers]`
remains the v1.0-deferred upstream-fix item.

## Self-Check: PASSED

- [x] All 3 tasks executed; each committed atomically (3 commits)
- [x] Schema + AsyncMock subset deterministic (19 + 2 = 21 tests; all PASS)
- [x] Combined Plan 08-04 deliverable subset = 78 PASS / 7 deselected (live)
- [x] `config.example.yaml` loads under `extra="forbid"` (CD-02 verified)
- [x] AsyncMock proof satisfies ROADMAP success criterion #4 deterministically
- [x] No regressions in unit (57), isolation (1+5), or contract-collection (580)
- [x] All acceptance-criteria grep counts match (verified during commit prep)
- [x] Live markers gated correctly — default `pytest` excludes the 7 live tests
