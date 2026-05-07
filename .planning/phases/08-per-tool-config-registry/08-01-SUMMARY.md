---
phase: 08-per-tool-config-registry
plan: 01
status: complete
requirements: [TOOLCFG-01, TOOLCFG-02, TOOLCFG-03, TOOLCFG-04, TOOLCFG-05]
key_files:
  created: []
  modified:
    - src/mcp_test_framework/rubrics.py
    - src/mcp_test_framework/models.py
    - src/mcp_test_framework/config.py
commits:
  - 785844a feat(08-01): add rubric ID registry + resolver to rubrics.py
  - c0edf5c feat(08-01): add ToolConfig sub-model with extra=forbid + validators
  - 52ee37a feat(08-01): wire version + tools fields into top-level Config
---

## What was built

The schema surface for the per-tool config registry. Three additive modifications:

1. **`rubrics.py`** — `id: ClassVar[str]` on each concrete rubric subclass (locked
   per TOOLCFG-04 / D-10 as `clarity`, `disambiguation`, `parameters`), plus
   module-level `RUBRIC_IDS` frozenset and `resolve_rubric_id()` helper that
   raises `ValueError` listing valid IDs on unknown input.
2. **`models.py`** — `ToolConfig` sub-model (frozen, `extra="forbid"`) with
   `skip`, `skip_reason`, `call_arguments`, `judges`, `setup`, `depends_on`
   fields; `_validate_judge_ids` field validator (D-17) and
   `_skip_requires_reason` model validator (D-16).
3. **`config.py`** — `version: int = 1` (with explicit field validator per CD-01)
   and `tools: dict[str, ToolConfig]` fields on top-level `Config`; `extra`
   flipped from `"ignore"` to `"forbid"` (CD-02 / D-15).

## Field-order rationale (D-04)

`ToolConfig` order mirrors the order users write per-tool overrides in YAML:
`skip` first because the most common per-tool override is "this tool is broken
upstream — skip it"; `skip_reason` immediately after for visual coupling with
its required partner; `call_arguments` next because runtime parameter
threading is the second-most-common use; `judges` after that for description-
quality narrowing; `setup` and `depends_on` last because they are reserved
fields (TOOLCFG-03 / D-06) — runtime no-ops in v1.1.

## Validator wiring + error messages

| Validator | Trigger | Error message form |
|-----------|---------|---------------------|
| `_validate_judge_ids` (field) | `judges` contains an unknown ID | `unknown rubric id 'clarty'; valid: ['clarity', 'disambiguation', 'parameters']` (raised by `resolve_rubric_id`, called only on miss to keep the canonical message a single source per CD-03) |
| `_skip_requires_reason` (model) | `skip=True` with `skip_reason` empty / whitespace / None | `skip=True requires a non-empty skip_reason (TOOLCFG-07: ...)` |
| `_validate_version` (Config field) | `version != 1` | `config version {v} not supported by this build, expected 1` |

`extra="forbid"` raises Pydantic's standard `ValidationError` with `extra_forbidden`
on either `ToolConfig` (per-tool typo: `srtip:` instead of `skip:`) or top-level
`Config` (per CD-02 — catches `targt:` for `target:`).

## CD-02 tightening: any cleanup needed?

None. The flip from `extra="ignore"` to `extra="forbid"` on top-level `Config`
did not require touching `config.example.yaml` or any test fixture — the existing
canonical YAML uses only `ollama:`, `mcp_server:`, `target:`, and
`judge_timeout_seconds:`, all of which are declared fields. The pre-existing
57-test unit suite (`tests/unit/` + `tests/test_isolation.py`) passes 57/57
after the flip with no fixture cleanup. `config.example.yaml` will be extended
with the worked `tools:` block by Plan 04.

## D-19 confirmation: env source naturally skips `tools` and `version`

`_BareNameNestedEnvSource.__call__` (config.py lines 127-146) iterates
`settings_cls.model_fields` and walks only fields whose annotation is a
`BaseModel` subclass (line 134). The new fields' annotations are `dict[str,
ToolConfig]` (annotation type: `dict`) and `int` respectively — neither is a
`BaseModel` subclass, so both are skipped automatically. **No edit to
`_BareNameNestedEnvSource` was required**; D-19 (no env routing for
`tools.*`) is honored by construction.

## Verification evidence

- `uv run python -c "from mcp_test_framework.rubrics import RUBRIC_IDS, resolve_rubric_id, ClarityRubric, DisambiguationRubric, ParametersRubric; ..." ` → `OK`
- `uv run python -c "from mcp_test_framework.models import ToolConfig; ..."` → `OK` (defaults + all 4 documented error paths trigger)
- `uv run python -c "from mcp_test_framework.config import Config; ..."` → `OK` (version + tools defaults; YAML overlay round-trip via `MCPTF_CONFIG_FILE` tempfile)
- `uv run pytest tests/unit/ tests/test_isolation.py` → **57 passed in 8.07s** (no regression)
- `uv run ruff check src/mcp_test_framework/{rubrics,models,config}.py` → `All checks passed!`

## Note on full pytest suite

`tests/test_mcp_tool_contract.py` does not currently pass against the live
`homelab-mcp` server — the failures are pre-existing and outside Plan 08-01's
scope:

- `test_description_disambiguation[list_registered_servers]` is the v1.0-deferred
  upstream-fix item (STATE.md "Deferred Items" table) — homelab-mcp's tool
  description is the bottleneck, not the framework.
- Tools that require arguments (e.g. `ssh_discover[hostname]`) fail
  `test_empty_args_call_returns_non_error` — **this is precisely what Plan
  08-02 fixes** by threading `tool_config.call_arguments` into
  `mcp_client.call_tool(...)`.

Plan 08-01 is the schema surface only; runtime threading lands in 08-02 and
verification tests land in 08-04.

## Self-Check: PASSED

- [x] All 3 tasks executed and verified
- [x] Each task committed individually (3 commits, all atomic)
- [x] No regression in unit test suite (57/57 passing)
- [x] All documented error paths trigger with the expected messages
- [x] D-19 (no env routing for `tools.*`) honored by construction
- [x] Ruff clean across all 3 modified files
