# Phase 08: Per-tool config registry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 08-per-tool-config-registry
**Areas discussed:** Schema shape, Judge subset semantics, Validation strictness + target/skip interaction, config-init CLI, call_arguments scope, Env-var routing surface

---

## Schema shape

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `tools:` + `version:` on Config | Add `version: int = 1` and `tools: dict[str, ToolConfig] = {}` directly on the existing Config root. ToolConfig is a new sub-model in models.py. Lines up with TOOLCFG-02's "top-level version" wording and keeps `target.tool_name` (single-tool mode from Phase 07) untouched as a separate concern. | ✓ |
| Nest under `target.tools` | Put the per-tool registry under `target.tools.<name>` so all tool-related config lives in one sub-model. Couples skip/judges to TargetConfig. Awkward for `version:` which TOOLCFG-02 puts at the top level. | |
| New `tool_registry:` sub-model + `version:` on Config | Wrap tools in a dedicated `ToolRegistryConfig` sub-model. Most ceremony; only worth it if we expect more registry-level fields beyond `version`. | |

**User's choice:** Top-level `tools:` + `version:` on Config (Recommended).
**Notes:** Recommended option accepted without amendment. `target.tool_name` stays as the single-tool selector; `tools.*` is orthogonal per-tool-behavior.

---

## Judge subset semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Per-test pytest.skip with reason | TEST-05/06/07 each check their own rubric ID against the tool's `judges` list (or default-all) at test entry; if not in the list, `pytest.skip(reason="judge X not selected for tool Y")`. One mechanism reused for skip/judges — uniform pytest reporting and JUnit visibility (Phase 09 OUTPUT-02 free-rides). Test bodies are 1-line guarded. | ✓ |
| Conditional collection / dynamic parametrize | Modify the discovery hook so each (test, tool) pair is only collected when the tool's `judges` allow it. Cleaner test bodies but the parametrize wiring becomes per-test-aware and harder to reason about; collection-time logic touches another seam. | |
| Custom pytest marker + collection filter | Add a `pytest.mark.judge("clarity")` decorator on TEST-05/06/07 and a hook that deselects items whose mark doesn't match the tool's judges. More extensible long-term but adds marker plumbing for one feature. | |

**User's choice:** Per-test pytest.skip with reason (Recommended).
**Notes:** Same skip mechanism reused for `skip:true` and judge-subset un-selection. Phase 09's reporter sees both as standard pytest skips with reasons.

---

## Validation strictness + target/skip interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Strict: extra=forbid + cross-field validators + warn on unknown tool names; explicit-target overrides skip | extra='forbid' on ToolConfig (TOOLCFG-05); model-validator requires `skip_reason` non-empty when `skip=true`; unknown judge IDs raise at load (resolve against rubric constants); unknown tool names in `tools:` log a warning at session start. When `target.tool_name=X` AND `tools.X.skip=true`: explicit single-target wins, with warning. | ✓ |
| Strict load-time + skip wins for explicit-target | Same load-time strictness, but if `target.tool_name=X` AND `tools.X.skip=true`, the run skips that one tool too (consistent precedence: skip is the absolute switch). Risk: a user setting TARGET_TOOL_NAME and getting a 0-test run with no obvious cause. | |
| Lenient: no cross-field validation, ignore unknown names | Just `extra='forbid'` for typos; skip without skip_reason still works (uses a generic message); unknown tool names silently ignored. Less code, looser contract — risks the silent-omission failure mode TOOLCFG-05 was written to prevent. | |

**User's choice:** Strict + explicit-target overrides skip (Recommended).
**Notes:** Skip-reason is required when skip=true. Unknown tool names are warnings (not load-time errors) because the discovered list isn't known until the MCP handshake runs.

---

## config-init CLI

| Option | Description | Selected |
|--------|-------------|----------|
| New `mcp-test-framework config-init` subcommand emitting to stdout | Discovers tools from the live server, prints a complete `tools:` YAML block + top-level `version: 1`. Default = stdout. With `--output PATH`, writes to file; refuses to overwrite an existing file unless `--force`. Idiomatic and composable. | ✓ |
| Add `--emit-config` flag to existing `list-tools` | Reuses `list-tools` plumbing (no new subcommand). Less discoverable; conflates 'show me tools' with 'give me a config scaffold'. | |
| Defer config-init to Phase 10 docs (just publish a snippet) | Phase 08 ships only the schema; Phase 10 docs include a copy-pasteable template. Saves CLI work this phase but pushes the Phase 07 D-04 deferral down the road. | |
| Skip config-init entirely (re-defer beyond v1.1) | Drop the starter-config generator from v1.1 — users hand-write `tools:` blocks. Re-promote Phase 07 D-04 to a backlog seed. Smallest scope; loses the Phase 07 deferral commitment. | |

**User's choice:** New `mcp-test-framework config-init` subcommand emitting to stdout (Recommended).
**Notes:** Honors Phase 07 D-04. Reuses `McpTestClient.__aenter__` (Phase 06 D-16) for isolation parity at the new spawn site.

---

## call_arguments scope

| Option | Description | Selected |
|--------|-------------|----------|
| All three (TEST-08/09/10) use call_arguments | TEST-08/09/10 currently all call `mcp_client.call_tool(name, {})`. With config, they all pass `tool_config.call_arguments` (default {}). Coherent: they're testing one tool invocation's contract — same args, three assertions. Lets a user with a required-args tool actually pass all three. | ✓ |
| Only TEST-08; TEST-09/10 keep `{}` | TEST-08 (the non-error check) uses configured args; TEST-09/10 keep their `{}` calls. Risk: tools with non-empty `inputSchema.required` still fail TEST-09/10 with isError=True payloads even after config fix; confusing partial pass. | |
| Add a separate `call_arguments_strict` field for TEST-09/10 | Two args fields per tool. Most flexible; nobody is asking for it. Skip. | |

**User's choice:** All three TEST-08/09/10 use call_arguments (Recommended).
**Notes:** One `call_arguments` value per tool, threaded through every CallTool-driven test.

---

## Env-var routing surface

| Option | Description | Selected |
|--------|-------------|----------|
| YAML/init-only — no env-var routing for `tools.*` | `tools.<name>.skip` etc. are configured via YAML or programmatic Config(...) kwargs only. The bare-name env-source pattern (config.py:_BareNameNestedEnvSource) is wired per-field via AliasChoices and doesn't generalize cleanly to a dynamic `dict[str, ToolConfig]`. Top-level `version` similarly defaults; not usefully overrideable via env. | ✓ |
| Add bare-name env aliases for top-level `version` only | `version` gets `MCPTF_CONFIG_VERSION` alias for symmetry; `tools.*` stay YAML/init-only. Minor surface increase; arguably zero practical need. | |
| Generalize the bare-name env source to dynamic dict fields | Invest in pattern that lets `MCPTF_TOOL_LIST_SERVERS_SKIP=true`-style overrides work. Significant complexity for unclear benefit; risk-prone. | |

**User's choice:** YAML/init-only — no env-var routing for `tools.*` (Recommended).
**Notes:** Keeps the env surface small. Existing `MCPTF_CONFIG_FILE` YAML overlay path is the supported override mechanism.

---

## Claude's Discretion

Items deferred to planner/researcher per CONTEXT.md `Claude's Discretion` section:

- **CD-01:** `version: int` validation strategy — equality default vs. explicit `field_validator`.
- **CD-02:** Whether to tighten top-level `Config.model_config` from `extra="ignore"` to `extra="forbid"`.
- **CD-03:** Where the rubric-ID registry lives — in `rubrics.py` (ClassVar) or a dedicated `_rubric_registry.py` module.
- **CD-04:** Warning channel for unknown tool names — `warnings.warn`, pytest config-time warning, or stderr print.
- **CD-05:** Per-test guard placement (D-08/D-09) — inline in test body, decorator, or fixture.
- **CD-06:** `config-init` emit format details (comments, key ordering, whether to include reserved `setup:`/`depends_on:` as commented examples).
- **CD-07:** Module placement of `ToolConfig` (likely `models.py`).
- **CD-08:** Plan-cut within the phase (likely schema → runtime → CLI → tests).

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` section. Highlights:

- Stateful-testing runtime for `setup:`/`depends_on:` (SEED-004 / v1.5+).
- Dynamic rubric data in `judges:` (SEED-003 / v1.3).
- `extra_env` per-tool overrides.
- Env-var routing for `tools.*`.
- Hard-fail on unknown tool names (today: warning).
- `config-init` interactive TUI mode.
- `config-init --merge` (preserve existing config on re-emit).
- Versioned rubric IDs (e.g. `clarity@v2`).
