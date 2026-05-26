# Phase 33: Per-bucket skip granularity in `ToolConfig` (999.1) - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator escape hatch for required-field tools: opt out of named test buckets (`schema`, `judge`, `output`) per tool in `config.yaml` while leaving the other buckets enabled. Required-field tools (e.g., `create_proxmox_vm`) can't satisfy the empty-args output bucket but still benefit from schema + judge signal. Today's `ToolConfig.skip: bool` is whole-tool only — too coarse.

Phase 30 UAT-1 surfaced this gap; CONTEXT.md SEED-022 ("framework primitives; SDET owns safety") respected — the framework gets a finer lever; the operator still decides.

**In scope:**
- New `skip_buckets: list[Literal["schema","judge","output"]] = []` field on `ToolConfig`
- Collection-time filtering (matches v1.1.1 / 260508-p0b hotfix pattern — skipped bucket tests are absent from `pytest --collect-only`, not rendered as runtime-SKIPPED rows)
- Pydantic validation rejects unknown bucket names at config load
- `--explain` per-tool block surfaces which buckets were skipped + the config field that drove the skip
- Pre-run digest reflects per-bucket skip counts alongside whole-tool skip counts
- README + `docs/LIBRARY-MODE.md` worked example using `create_proxmox_vm`

**Out of scope** (deferred to other phases or backlog):
- Codegen-driven typed parameter generation for required-field tools (Phase 999.2 in parking lot)
- Renaming the existing runner/reporter `bucket` aggregation concept
- Per-judge granularity (already covered by `ToolConfig.judges`)
- Marker-driven bucket inference (handled per Claude's discretion below)

</domain>

<decisions>
## Implementation Decisions

### Worked example (BUCKET-05)
- **D-01:** Worked example uses a **real homelab-mcp tool** — not a synthetic placeholder, not a test-only tool. Authentic operator config drops directly into the existing `homelab-mcp` config without mental substitution.
- **D-02:** The specific tool is **`create_proxmox_vm`**. Canonical required-field tool (needs name/node/cores/memory/etc.), most operator-recognizable from the active homelab-mcp config, dramatic mismatch between empty-args output bucket and the schema+judge signal makes the value proposition obvious.
- **D-03:** Doc snippet is **YAML + expected output** — the `tools.create_proxmox_vm.skip_buckets: ["output"]` snippet AND a copy of what `mcp-contracts run --explain` prints for that tool AND a slice of the pre-run digest. ~25–40 lines per doc. Lets the operator verify their config worked without having to run it first. Applies to both README and `docs/LIBRARY-MODE.md`.

### Claude's Discretion

The following gray areas were surfaced but the user did NOT select them for discussion. Claude will use the recorded defaults in research/planning. Flag during planning if a deviation is needed.

- **Field naming.** Keep `skip_buckets` (matches REQUIREMENTS.md BUCKET-01 verbatim). The English word `bucket` is already used elsewhere in `_runner.py` / `_reporter.py` for per-tool result aggregation — disambiguate in docs by always qualifying as "test bucket" (schema/judge/output) vs "result bucket" (per-tool aggregation). Do NOT rename either concept.
- **`skip: true` + `skip_buckets: [...]` interaction.** Raise at config load time via a Pydantic `@model_validator(mode="after")` — redundant config is operator error and should fail loud (consistent with `extra="forbid"` strictness and the existing `_skip_requires_reason` validator that already lives on `ToolConfig`). Error message follows the v1.5 operator-tone three-part pattern.
- **`--explain` bucket-level rendering.** Extend the existing per-tool block (don't create a parallel structure). Each skipped bucket gets a single indented line within the tool's block: `  bucket=output: skipped via tools.<name>.skip_buckets`. Grep-able by `bucket=` literal. Matches the "grep-able N+5-line block per tool" wording in SC#3.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 33 scope + requirements
- `.planning/ROADMAP.md` §Phase 33 — Goal, depends-on, success criteria (4 SCs), requirements list
- `.planning/REQUIREMENTS.md` §BUCKET — BUCKET-01 through BUCKET-05 (field shape, collection-time filter, Pydantic validation, --explain + digest, docs)

### Existing config + plugin surface
- `src/mcp_test_framework/models.py:77-136` — `ToolConfig` model (the field lands here). Note `extra="forbid"`, `frozen=True`, existing `skip: bool`, existing `_skip_requires_reason` model_validator pattern to mirror.
- `src/mcp_test_framework/contracts/_tests.py` — The 10 contract test functions that need to be grouped by bucket. Bucket mapping is currently implicit in function names (`test_schema_*` → schema, `test_description_*` + `test_parameters_self_explanatory` → judge, `test_empty_args_*` + `test_result_*` + `test_text_content_*` → output). Planner decides whether to encode via markers, name-prefix regex, or explicit dict.
- `src/mcp_test_framework/_plugin.py:355-446` — `pytest_collection` / `pytest_generate_tests` parametrize machinery. The filter point for collection-time skipping (matches v1.1.1 / 260508-p0b pattern referenced in BUCKET-02).
- `src/mcp_test_framework/_runner.py:611-667` — existing `bucket` (per-tool result aggregation) usage. Naming-collision context for the docs-disambiguation note in Claude's Discretion D-3.
- `src/mcp_test_framework/_reporter.py:196-271` — `bucket` aggregation in the JUnit-XML rewire path. Same naming-collision context.

### Prior-phase patterns this phase follows
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md` — v2-only schema posture, Pydantic `extra="forbid"` enforcement style, operator-tone error registry pattern (`docs/ERROR-STYLE.md`)
- `.planning/phases/32-surface-shim-removals-cli-package-fixtures-discovery/32-CONTEXT.md` — Operator-tone three-part error message structure (what removed → why → next step), `[mcp-contracts]` formatwarning prefix
- v1.1.1 / 260508-p0b hotfix — collection-time filter pattern for whole-tool skip; locate the existing implementation in `_plugin.py` and extend symmetrically for bucket-level filter (don't fork a new code path)

### Operator-facing docs to update
- `README.md` — worked example using `create_proxmox_vm` (D-03)
- `docs/LIBRARY-MODE.md` — worked example using `create_proxmox_vm` (D-03)
- `docs/ERROR-STYLE.md` — register the new Pydantic validation message + the `skip` ↔ `skip_buckets` redundancy message (Claude's Discretion)
- `docs/EXTENDING.md` — light pass to confirm no stale references

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ToolConfig._skip_requires_reason` model_validator** (`models.py:122-136`) — Template for the new `skip` vs `skip_buckets` redundancy validator. Same `@model_validator(mode="after")` shape, same operator-tone error style.
- **`Field` + `Literal` typed list** — Pydantic-native pattern; `BUCKET-03` validation falls out for free from `list[Literal["schema","judge","output"]]`. No custom `@field_validator` needed for unknown-bucket-name rejection — Pydantic's stock error names the valid Literal values.
- **v1.1.1 collection-time skip path in `_plugin.py`** (around the `parametrize_names` filter) — the existing whole-tool skip already filters parametrize at collection time. The per-bucket filter is a sibling step in the same hook; the design pattern is already established and tested.
- **`--explain` per-tool block renderer** (`_runner.py` / `_reporter.py` `--explain` path) — extend with a single `bucket=<name>: skipped via tools.<name>.skip_buckets` line per skipped bucket inside the existing block.

### Established Patterns
- **Operator-tone three-part error message** — what happened → why → next step. Used uniformly across v1.5 shim rejections + Pydantic validation. New `skip` vs `skip_buckets` redundancy error MUST follow this shape.
- **`extra="forbid"` on every operator-facing model** — typos at load time, not runtime. Already on `ToolConfig`.
- **Bucket-name grouping is implicit in function names** in `contracts/_tests.py`. Planner must decide the encoding: explicit `dict[Literal["schema","judge","output"], list[str]]` in `_plugin.py`, a new `@pytest.mark.bucket("schema")` marker on each test function, or a name-prefix regex inferred at collection time. Pick the option that adds the least new surface for the future capstone (Phase 35 zero-shim regression gate).

### Integration Points
- `Config.tools` (the `dict[str, ToolConfig]` field that already exists) — no new top-level config key; this lands as a sub-field on the existing per-tool entry.
- `pytest_generate_tests` / `pytest_collection` in `_plugin.py` — the filter point that turns `skip_buckets` into "this test was never collected" rather than "this test ran and was SKIPPED".
- `--explain` text output path + pre-run digest path — both already iterate per-tool config; per-bucket counts thread through the same iteration.

</code_context>

<specifics>
## Specific Ideas

- Worked example tool: **`create_proxmox_vm`** (D-02). Operator-recognizable, large required-field schema, empty-args output bucket cannot succeed, schema + judge buckets retain full value.
- Doc snippet length: ~25–40 lines per doc (D-03) — YAML config + `--explain` output + pre-run digest slice. Both README and `docs/LIBRARY-MODE.md` get the same example for parity.
- `--explain` bucket line format (Claude's Discretion): `bucket=<name>: skipped via tools.<name>.skip_buckets` (grep-able by `bucket=` literal).
- `skip` + `skip_buckets` redundancy: hard-fail at config load with an operator-tone three-part error, NOT silent precedence (Claude's Discretion).

</specifics>

<deferred>
## Deferred Ideas

- **Renaming the existing `bucket` (per-tool result aggregation) concept in `_runner.py` / `_reporter.py`** to eliminate the name collision with the new `skip_buckets` (test-bucket) field. Phase 33 keeps both terms and disambiguates in docs (Claude's Discretion). A v1.6 cleanup pass could pick one canonical name across the codebase if the docs disambiguation proves insufficient.
- **Per-judge skip granularity** — already covered by the existing `ToolConfig.judges: Optional[list[str]]` field (empty list = explicit opt-out of all judges). Don't duplicate that capability inside `skip_buckets`.
- **Marker-driven test→bucket inference** (`@pytest.mark.bucket("schema")` decorators on each contract test) — one of three options the planner will pick from; if the planner picks markers, this isn't deferred. If the planner picks explicit dict / name-prefix, deferred for a future refactor.
- **Codegen for required-field tools** (Phase 999.2 in the backlog) — pairs naturally with bucket-skip but is its own phase; mention in BUCKET-05 worked example only as a forward reference, do NOT implement.

</deferred>

---

*Phase: 33-Per-bucket skip granularity in `ToolConfig` (999.1)*
*Context gathered: 2026-05-26*
