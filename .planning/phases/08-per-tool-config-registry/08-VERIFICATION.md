---
phase: 08-per-tool-config-registry
verified: 2026-05-07T15:35:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 08: Per-Tool Config Registry Verification Report

**Phase Goal:** Declarative per-tool skip / args / judge selection — provide a Pydantic-modeled per-tool config registry so an operator can mark a tool skipped (with surfacing skip_reason), provide call_arguments for tools that need required parameters, and select a subset of rubrics per tool, all via a YAML overlay.

**Verified:** 2026-05-07T15:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (consolidated from ROADMAP success criteria + plan must_haves)

| #   | Truth                                                                                                                                                  | Status     | Evidence                                                                                                                                                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | ToolConfig Pydantic sub-model exists with skip/skip_reason/call_arguments/judges/setup/depends_on fields and frozen+extra="forbid" config             | VERIFIED   | `src/mcp_test_framework/models.py:101-159` — `class ToolConfig(BaseModel)` with `model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")` and all six fields with correct types/defaults                       |
| 2   | Top-level Config has `version: int = 1` (rejects ≠1) and `tools: dict[str, ToolConfig]` defaulting to `{}`; root extra="forbid" (CD-02)                | VERIFIED   | `src/mcp_test_framework/config.py:161 extra="forbid"`, `:176 version: int = 1`, `:182 tools: dict[str, ToolConfig]`, `:184-192 _validate_version` rejects ≠1 with named error. Live test: `Config(version=2)` raises ValueError      |
| 3   | RUBRIC_IDS frozenset = `{"clarity", "disambiguation", "parameters"}`; `resolve_rubric_id` raises ValueError listing valid IDs (TOOLCFG-04 / D-17)      | VERIFIED   | `src/mcp_test_framework/rubrics.py:103-105 RUBRIC_IDS`, `:108-124 resolve_rubric_id`. `ClarityRubric.id="clarity"`, `DisambiguationRubric.id="disambiguation"`, `ParametersRubric.id="parameters"` (note: Parameters dimension is `parameters_self_explanatory`, ID is `parameters` — locked per D-10) |
| 4   | YAML overlay with `tools.X.srtip` raises `extra_forbidden`; bad judges raises with valid set listed; skip without reason raises mentioning skip_reason  | VERIFIED   | Pytest passes for all of: `test_toolconfig_rejects_extra_field_typo`, `test_toolconfig_rejects_unknown_judge_id`, `test_toolconfig_skip_requires_non_empty_reason[None/""/"   "]`. Validators in models.py:127-159                  |
| 5   | tool_config fixture resolves `config.tools.get(target_tool.name, ToolConfig())` per test; TEST-01..10 carry uniform skip guard; TEST-05/6/7 carry judge guards; TEST-08/9/10 thread call_arguments | VERIFIED | `src/mcp_test_framework/fixtures.py:404-418`. `tests/test_mcp_tool_contract.py` lines 57, 70, 78, 88, 110, 142, 172, 208, 225, 239 — all 10 test signatures take `tool_config: ToolConfig`. All 10 carry `if tool_config.skip: pytest.skip(...)`. TEST-05/06/07 (lines 124, 154, 185) carry judge-not-selected guards. TEST-08/09/10 (lines 221, 233, 251) call `mcp_client.call_tool(target_tool.name, tool_config.call_arguments)` |
| 6   | `_preflight` emits UserWarning for unknown tool keys (D-14/D-18) and for explicit-target-overrides-skip (D-12)                                          | VERIFIED   | `src/mcp_test_framework/fixtures.py:28 import warnings`, `:180-190` unknown-tool-name warning, `:201-213` explicit-target-overrides-skip warning. Both use `UserWarning, stacklevel=2`                                              |
| 7   | `mcp-test-framework config-init` Typer subcommand emits YAML scaffold (`version: 1` + commented `tools:` blocks with locked rubric IDs); refuses overwrite without --force; reuses `_list_tools_async` (D-24); SIGINT→130 | VERIFIED | `src/mcp_test_framework/cli.py:178-266 config_init`, `:345-397 _format_tools_yaml_scaffold`. Scaffold contains `version: 1`, `judges: [clarity, disambiguation, parameters]`. Calls `_list_tools_async(cfg)` line 231 (no `stdio_client` import — verified via grep). Live `--help` shows all flags |
| 8   | AsyncMock proof for ROADMAP success criterion #4: framework passes configured `call_arguments` (not `{}`) verbatim to `McpTestClient.call_tool`         | VERIFIED   | `tests/test_tool_config.py:166-189 test_call_arguments_forwarded_to_call_tool_via_asyncmock`. Real implementation: imports actual TEST-08 body from `tests.test_mcp_tool_contract`, builds AsyncMock for `call_tool`, awaits the body, asserts `mock_call_tool.assert_called_once_with("demo_tool", {"key": "value", "limit": 7})`. Test PASSES under `uv run pytest` (deterministic, no live deps) |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact                                          | Expected                                                                              | Status     | Details                                                                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `src/mcp_test_framework/rubrics.py`               | ClassVar id on each rubric subclass + RUBRIC_IDS frozenset + resolve_rubric_id helper | VERIFIED   | All three subclasses have `id: ClassVar[str]`. RUBRIC_IDS = frozenset of three IDs. resolve_rubric_id raises with valid-set message    |
| `src/mcp_test_framework/models.py`                | ToolConfig sub-model with extra="forbid", validators                                  | VERIFIED   | ToolConfig at line 101-159; imports RUBRIC_IDS/resolve_rubric_id; both validators present (`_validate_judge_ids`, `_skip_requires_reason`) |
| `src/mcp_test_framework/config.py`                | version + tools fields on top-level Config; extra="forbid"                            | VERIFIED   | All 3 fields confirmed via grep + functional tests. `_BareNameNestedEnvSource` (lines 92-147) naturally skips `dict[str, ToolConfig]` annotation per D-19 |
| `src/mcp_test_framework/fixtures.py`              | tool_config fixture; session-start warning hooks                                      | VERIFIED   | `tool_config` at line 404 (sync, function-scope per D-04). Two warning sites in `_preflight` at lines 180-190 and 201-213            |
| `tests/test_mcp_tool_contract.py`                 | TEST-05/06/07 judge guards; TEST-08/09/10 call_arguments threading; uniform skip      | VERIFIED   | 10 occurrences of `tool_config: ToolConfig`, 10 skip guards, 3 `tool_config.call_arguments` usages, 3 judge guards (one each TEST-05/06/07) |
| `src/mcp_test_framework/cli.py`                   | `config-init` subcommand + `_format_tools_yaml_scaffold` helper                       | VERIFIED   | Both present (lines 178, 345). No `stdio_client` import — D-24 reuse path confirmed                                                  |
| `tests/test_tool_config.py`                       | Schema + AsyncMock + runtime tests for TOOLCFG-01..07                                 | VERIFIED   | 18 deterministic test functions (12 named + parametrize fan-out) + 1 AsyncMock + 3 live-marked. 19 pass deterministically             |
| `tests/test_config_init_cli.py`                   | CLI surface tests (--help, overwrite gate, scaffold round-trip)                       | VERIFIED   | 2 unit tests (pass deterministically) + 4 live-marked tests                                                                         |
| `config.example.yaml`                             | version: 1 + worked tools: block illustrating skip / judges                           | VERIFIED   | Lines 22-45 add `version: 1` + worked tools block. Loads cleanly under `extra="forbid"` (verified live)                              |

### Key Link Verification

| From                                                    | To                                                       | Via                                                  | Status | Details                                                                                  |
| ------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| `models.py:ToolConfig.judges` validator                 | `rubrics.py:RUBRIC_IDS`                                  | `from mcp_test_framework.rubrics import RUBRIC_IDS`  | WIRED  | Import line 33 of models.py; validator references RUBRIC_IDS at line 139                  |
| `config.py:Config.tools` field                          | `models.py:ToolConfig`                                   | annotation `dict[str, ToolConfig]`                   | WIRED  | Line 49 imports ToolConfig; line 182 uses it in field annotation                          |
| `tests/test_mcp_tool_contract.py` test signatures       | `fixtures.py:tool_config`                                | fixture request via `tool_config: ToolConfig`        | WIRED  | All 10 test signatures take `tool_config: ToolConfig`; fixture at fixtures.py:404         |
| `tests/test_mcp_tool_contract.py:test_empty_args_*`     | `mcp_client.py:McpTestClient.call_tool`                  | `call_tool(target_tool.name, tool_config.call_arguments)` | WIRED | Line 221, 233, 251 of test file                                                          |
| `cli.py:config_init`                                    | `cli.py:_list_tools_async`                               | `runner.run(_list_tools_async(cfg))`                 | WIRED  | Line 231; same call as `list-tools` (line 164). No open-coded `stdio_client` (verified)  |
| `tests/test_config_init_cli.py`                         | `cli.py:config_init`                                     | `CliRunner().invoke(app, ['config-init', ...])`      | WIRED  | Line 25 + multiple `_invoke("config-init", ...)` call sites                              |
| `config.example.yaml`                                   | `models.py:ToolConfig`                                   | `Config()` loads YAML with `tools:` block            | WIRED  | Live verified: `Config().tools == {'list_registered_servers': ..., 'list_keyring_credentials': ...}` |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable                | Source                                                     | Produces Real Data | Status   |
| --------------------------------- | ---------------------------- | ---------------------------------------------------------- | ------------------ | -------- |
| `tool_config` fixture             | ToolConfig instance          | `config.tools.get(target_tool.name, ToolConfig())`         | Yes — flows from YAML overlay through Pydantic to test bodies | FLOWING |
| TEST-08/09/10 `call_arguments`    | `tool_config.call_arguments` | Pydantic-loaded YAML dict, threaded into `mcp_client.call_tool` | Yes — AsyncMock test proves verbatim pass-through         | FLOWING |
| `config-init` scaffold tools list | discovered MCP tools         | `_list_tools_async(cfg)` (live MCP handshake)              | Yes — same isolation-aware spawn as list-tools (D-24)      | FLOWING |
| `_preflight` warning iteration    | `set(config.tools) - discovered_names` | live tool discovery + YAML overlay                          | Yes — both sources are live data                          | FLOWING |

### Behavioral Spot-Checks

| Behavior                                                          | Command                                                                                                          | Result                                          | Status |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ------ |
| Phase 08 deterministic tests pass                                 | `MCPTF_CONFIG_FILE=./config.yaml uv run pytest tests/test_tool_config.py tests/test_config_init_cli.py -v`        | 21 passed, 7 deselected                          | PASS   |
| Full default-marker suite passes                                  | `MCPTF_CONFIG_FILE=./config.yaml uv run pytest tests/test_tool_config.py tests/test_config_init_cli.py tests/unit tests/test_isolation.py` | 78 passed, 7 deselected (matches SUMMARY claim)  | PASS   |
| `config.example.yaml` loads under root `extra="forbid"`           | `MCPTF_CONFIG_FILE=config.example.yaml uv run python -c "from mcp_test_framework.config import Config; print(Config().version, list(Config().tools))"` | `1 ['list_registered_servers', 'list_keyring_credentials']` | PASS |
| `config-init --help` works (no live discovery needed)             | `uv run mcp-test-framework config-init --help`                                                                    | Shows `--config`, `--output`, `--force` flags    | PASS   |
| RUBRIC_IDS exposes locked v1.1 rubric set                         | `uv run python -c "from mcp_test_framework.rubrics import RUBRIC_IDS; print(sorted(RUBRIC_IDS))"`                | `['clarity', 'disambiguation', 'parameters']`   | PASS   |
| Unknown rubric ID raises with valid set in message                | `resolve_rubric_id('clarty')` → ValueError                                                                       | `unknown rubric id 'clarty'; valid: ['clarity', 'disambiguation', 'parameters']` | PASS |
| `Config(version=2)` raises with version + value in message        | inline Python                                                                                                    | ValueError mentions `version` and `2`            | PASS   |
| `ToolConfig(srtip=True)` rejected with extra_forbidden            | inline Python                                                                                                    | ValidationError contains `extra_forbidden`       | PASS   |

### Requirements Coverage

| Requirement | Source Plan(s)            | Description                                                                              | Status    | Evidence                                                                                                                                                                                                       |
| ----------- | ------------------------- | ---------------------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TOOLCFG-01  | 08-01, 08-02, 08-03, 08-04 | ToolConfig with skip/skip_reason/call_arguments/judges Pydantic-modeled                  | SATISFIED | `src/mcp_test_framework/models.py:101-125` ToolConfig with all 4 fields + 2 reserved fields. AsyncMock test proves call_arguments threading. Live: tests/test_tool_config.py 12 schema tests pass               |
| TOOLCFG-02  | 08-01, 08-03, 08-04        | Top-level `version: 1` field; forward-migration handle                                   | SATISFIED | `config.py:176 version: int = 1` + `:184-192 _validate_version`. Scaffold emits `version: 1`. Tests `test_default_config_version_and_tools`, `test_config_rejects_unsupported_version[0/2/-1/99]` PASS         |
| TOOLCFG-03  | 08-01, 08-04               | `setup`/`depends_on` Optional/unused fields per SEED-004                                 | SATISFIED | `models.py:124-125` setup, depends_on fields. Comments cite TOOLCFG-03/D-06. Scaffold OMITS them per CD-06 (avoids users assuming they work). Test `test_reserved_fields_typed_but_runtime_no_op` PASSES         |
| TOOLCFG-04  | 08-01, 08-03, 08-04        | `judges: [...]` resolves against rubric constants `clarity`, `disambiguation`, `parameters` | SATISFIED | `rubrics.py:103-105 RUBRIC_IDS`. ParametersRubric.id="parameters" (locked separately from prompt dimension). Tests `test_toolconfig_rejects_unknown_judge_id`, `test_toolconfig_accepts_all_locked_rubric_ids` PASS |
| TOOLCFG-05  | 08-01, 08-04               | `extra="forbid"` so typos produce clear errors at config load                            | SATISFIED | `models.py:118 ToolConfig.model_config extra="forbid"` AND `config.py:161 Config.model_config extra="forbid"` (CD-02 root tightening). Tests for both layers PASS                                              |
| TOOLCFG-06  | 08-02, 08-04               | Tools with no entry use safe defaults: skip=False, empty call_arguments, all judges run | SATISFIED | `models.py:120-123` defaults match spec. `fixtures.py:418` returns `ToolConfig()` for missing entries. Tests `test_default_toolconfig_values`, `test_toolconfig_accepts_none_judges` PASS                       |
| TOOLCFG-07  | 08-02, 08-04               | Skipped tools surface in pytest output via `pytest.skip(reason=skip_reason)`             | SATISFIED | `models.py:145-159 _skip_requires_reason` enforces non-empty reason at load. All 10 tests in `tests/test_mcp_tool_contract.py` carry `pytest.skip(reason=tool_config.skip_reason or ...)`. Live runtime test gated behind live markers |

### Anti-Patterns Found

| File                                              | Line | Pattern                       | Severity | Impact                                                                                                                                  |
| ------------------------------------------------- | ---- | ----------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/mcp_test_framework/cli.py`                   | 240  | "out of scope for this plan" comment about three-copy hint hazard | Info    | Documented technical debt — three copies of the MCP-not-on-PATH hint exist (cli.py, fixtures.py, conftest.py). Phase 08 acknowledges and explicitly defers consolidation. Not a blocker. |
| `src/mcp_test_framework/models.py`                | 124  | `setup: Optional[Any] = None` (reserved field, runtime no-op)     | Info    | Intentional per TOOLCFG-03 / D-06 — typed but unused for SEED-004 forward-compat. NOT a stub: scaffold omission per CD-06 documents the dormancy. |

No BLOCKER or WARNING anti-patterns found.

### Human Verification Required

(none required — all behaviors verified via deterministic tests, AsyncMock proof, and live runtime spot-checks)

The 7 live-marked tests (3 in `test_tool_config.py`, 4 in `test_config_init_cli.py`) require homelab-mcp + Ollama for end-to-end exercise; these are explicitly out-of-band and gated behind `@pytest.mark.live_homelab`/`@pytest.mark.live_ollama` so they do not run under default pytest invocations. They are operator-driven verification, not phase-blocking. The deterministic verification (78 passed in default suite, including the AsyncMock proof of call_arguments threading) is sufficient to declare phase goal achieved.

### Gaps Summary

No gaps. Phase 08 delivers the declarative per-tool config registry end-to-end:

1. **Schema surface** (Plan 01): `ToolConfig` Pydantic sub-model + `Config.version` + `Config.tools` + `extra="forbid"` at both layers + locked rubric ID registry. All validators (D-15/D-16/D-17) emit named, debuggable errors.
2. **Runtime threading** (Plan 02): `tool_config` fixture + uniform skip guard on all 10 tests + judge-selection guards on TEST-05/06/07 + `call_arguments` threading on TEST-08/09/10 + two `_preflight` warning sites (D-12 explicit-target-overrides-skip; D-14/D-18 unknown-tool-name).
3. **Operator onramp** (Plan 03): `config-init` Typer subcommand emits YAML scaffold with `version: 1` + per-tool commented blocks + locked rubric IDs; reuses `_list_tools_async` (D-24); refuses overwrite without `--force`; SIGINT→130; FileNotFoundError inherits 260507-j6i hint.
4. **Verification + worked example** (Plan 04): 19 deterministic tests + 3 live runtime tests in `test_tool_config.py`, 2 unit + 4 live tests in `test_config_init_cli.py`. AsyncMock test (`test_call_arguments_forwarded_to_call_tool_via_asyncmock`) is real — imports actual TEST-08 body from `tests.test_mcp_tool_contract`, builds AsyncMock for `call_tool`, awaits the body, asserts `assert_called_once_with("demo_tool", {"key": "value", "limit": 7})`. This is the strong proof of ROADMAP success criterion #4 and runs deterministically under default pytest. `config.example.yaml` gains `version: 1` + worked `tools:` block and loads cleanly under `extra="forbid"`.

Pre-existing live-MCP failures (e.g., `ssh_discover` empty-args, `list_registered_servers` disambiguation) are NOT regressions caused by this phase — they are exactly the cases Phase 08 enables operators to fix via `tools.<name>.call_arguments` and `tools.<name>.skip`. The verifier confirms 78 passed / 7 deselected on the default-marker suite, matching the SUMMARY claim.

CD-02 root tightening (`extra="forbid"` at top level) is sound: `config.example.yaml` and active `config.yaml` both load cleanly under the new constraint. No fixture or test file required cleanup.

---

_Verified: 2026-05-07T15:35:00Z_
_Verifier: Claude (gsd-verifier)_
