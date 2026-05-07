# Phase 08: Per-tool config registry - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

A test author can declaratively control per-tool behavior — skip with reason, fixed `call_arguments`, judge subset selection — via a validated `tools.<tool_name>` config block, without touching framework code. The config schema reserves `setup:` and `depends_on:` as Optional/unused fields per SEED-004 forward-compat (v1.5+ activates them additively). Top-level `version: 1` field; `extra="forbid"` produces clear errors on field-name typos. Phase also ships the `mcp-test-framework config-init` starter-config generator deferred from Phase 07 D-04.

**In scope (per ROADMAP.md and REQUIREMENTS.md):** TOOLCFG-01..TOOLCFG-07 + the `config-init` CLI surface (Phase 07 D-04 honoring).

**Explicitly NOT in scope:**
- `setup:` / `depends_on:` runtime semantics — schema-reservation only; SEED-004 / v1.5+ activates.
- Dynamic / data-driven rubrics — `judges:` resolves to existing rubric *constants* only; SEED-003 / v1.3 ships rubrics-as-data.
- JUnit XML emission / `--junit-xml` — Phase 09 (OUTPUT-01..03). Phase 08's `pytest.skip(reason=...)` flows through whatever reporter is active and is the seam Phase 09 builds on.
- Multi-tool discovery / parametrize wiring — owned by Phase 07 (MULTI-01..04, already merged).
- Per-tool isolation overrides (e.g. tool that needs real keyring) — see Phase 06 deferred ideas.
- Process-parallel execution / xdist — v1.2 (SEED-002).
- Env-var routing for `tools.*` config — explicitly YAML/init-only (D-19).

</domain>

<decisions>
## Implementation Decisions

### Schema shape & top-level surface

- **D-01:** New `tools: dict[str, ToolConfig]` field added directly to the **top-level `Config`** model (`config.py`). `tools` is keyed by tool name (matches the names returned by `list_tools()` — string-equality). `ToolConfig` is a new sub-model in `models.py`. No new wrapper sub-model (`ToolRegistryConfig`) — the registry is just a dict and adding ceremony costs more than it buys.
- **D-02:** New `version: int = 1` field added directly to the top-level `Config` model. Matches TOOLCFG-02's "top-level version" wording. Field acts as a forward-migration handle: future schema changes either default to `version: 2+` or branch on the loaded value. v1.1 ships only `version: 1` and asserts it; any other value should fail loud at load time (planner's call on validator vs. equality default — see CD-01).
- **D-03:** `target.tool_name` (Phase 07 D-01/D-02) is **untouched**. Single-target mode and per-tool registry are orthogonal: `target.tool_name` says *which subset of tools to test*, `tools.<name>.*` says *how each tool behaves once selected*. Together they multiply, not collide (interaction rules in D-12).

### `ToolConfig` field set

- **D-04:** `ToolConfig` fields, in declaration order: `skip: bool = False`, `skip_reason: Optional[str] = None`, `call_arguments: dict[str, Any] = {}`, `judges: Optional[list[str]] = None`, `setup: Optional[Any] = None` (reserved per TOOLCFG-03), `depends_on: Optional[list[str]] = None` (reserved per TOOLCFG-03).
- **D-05:** `ToolConfig.model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")` — `extra="forbid"` is the load-time guard required by TOOLCFG-05 (typos like `srtip:` raise loud at load, not at test time as silent omissions). Frozen + populate_by_name follows the existing `OllamaConfig` / `McpServerConfig` / `TargetConfig` shape from `models.py`.
- **D-06:** `setup:` and `depends_on:` are typed `Optional[Any]` / `Optional[list[str]]` and **ignored at runtime** — present in the model so v1.5+ stateful-testing milestone can light them up additively without a schema migration. SEED-004's "Action item for v1.1" maps directly to D-04/D-06.
- **D-07:** `judges` is `Optional[list[str]]` (NOT `list[str] = []`). Distinguishes `None` (run all available rubrics — TOOLCFG-06 default) from `[]` (run no rubrics — explicit opt-out, useful per-tool). The empty-list-vs-None semantic is meaningful here.

### `judges` selection semantics — per-test pytest.skip

- **D-08:** When `tools.<name>.judges` is a list (set or empty) AND a rubric ID is NOT in that list, the corresponding judged test (TEST-05/06/07) calls `pytest.skip(reason=f"judge {rubric_id!r} not selected for tool {tool_name!r}")` at test entry. When `judges is None` (default), all three judged tests run — TOOLCFG-06.
- **D-09:** Mechanism = guard at the top of each judged test body, NOT collection-time deselection. Reasons: (1) keeps Phase 07's collection hook untouched, (2) one mechanism reused for `skip:` and `judges:` subset (uniform pytest reporting + JUnit visibility — Phase 09 OUTPUT-02 free-rides), (3) the test still appears in pytest output as `SKIPPED` rather than vanishing — better signal for the user.
- **D-10:** Rubric-ID resolution: each rubric class (`ClarityRubric`, `DisambiguationRubric`, `ParametersRubric`) gains an `id: ClassVar[str]` (or equivalent — planner picks the cleanest seam). Strings are `"clarity"`, `"disambiguation"`, `"parameters"` per TOOLCFG-04. The `judges:` validator resolves each entry against this set; unknown IDs raise at load time (D-15).

### `call_arguments` semantics

- **D-11:** TEST-08, TEST-09, AND TEST-10 all use `tool_config.call_arguments` (default `{}`). They are testing one tool invocation's contract — same args, three assertions on the response. With required-args tools, providing args once unblocks all three; that's the user-facing fix for the visible failures Phase 07 D-06/D-07 left behind.

### Interaction: explicit target + skip / judges

- **D-12:** When `target.tool_name="X"` AND `tools.X.skip=true`: **explicit single-target wins** — the run still exercises tool X (skip is overridden), and the framework emits a session-start warning (`pytest.warns` or stderr — planner's call) noting the override. Rationale: setting `TARGET_TOOL_NAME` is a deliberate single-target intent; silently no-op'ing the run violates the principle of least surprise.
- **D-13:** When `target.tool_name="X"` AND `tools.X.judges=[...]`: subset honored. Single-tool mode + judge subset compose without conflict.
- **D-14:** When `tools.X` is configured but X is NOT in the discovered tool list at session start: emit a session-start **warning** (not a hard fail). Rationale: a user may stage config for a tool they're about to add server-side, or for a tool that exists in another deployment they switch between. Hard-failing the run on an unknown name is over-strict.

### Validation strictness (load-time)

- **D-15:** `extra="forbid"` on `ToolConfig` (covers `srtip:` typos — TOOLCFG-05). `extra="forbid"` should also be applied to top-level `Config` for v1.1+ if not already (currently `extra="ignore"` per `config.py:160`); planner verifies and tightens — see CD-02.
- **D-16:** Cross-field validator: when `skip=True`, `skip_reason` MUST be a non-empty string. Pydantic `model_validator(mode="after")` raises clearly. TOOLCFG-07 demands the reason surface in pytest output; an empty reason defeats that requirement at the source.
- **D-17:** Field validator on `judges`: each string MUST resolve against the rubric-ID registry. Unknown IDs raise `ValueError` with a list of valid IDs in the message. Same for `version`: only `1` is accepted in v1.1 (defends the upgrade path).
- **D-18:** Unknown tool names in `tools:` block → session-start **warning** (D-14). NOT a load-time error: the discovered-tool list isn't known until the MCP handshake runs, and load-time is too early to compare.

### Env-var routing surface

- **D-19:** `tools.*` config is **YAML/init-only** — NO env-var routing for the dynamic dict. The `_BareNameNestedEnvSource` in `config.py:91-146` walks per-field `validation_alias=AliasChoices(...)` and doesn't generalize cleanly to `dict[str, ToolConfig]`. Inventing `MCPTF_TOOL_LIST_SERVERS_SKIP=true`-style aliases adds surface without a real use case. `version` similarly defaults; not usefully overrideable via env.
- **D-20:** YAML overlay path is the load source (`MCPTF_CONFIG_FILE`). The existing `YamlConfigSettingsSource` already handles `tools:` keys natively as nested dicts — no new source needed.

### Starter-config generator (`config-init`)

- **D-21:** New CLI subcommand: `mcp-test-framework config-init`. Discovers tools from the live server (reuses the Phase 07 discovery seam — `tests/conftest.py:_discover_tools` lifted to a CLI-callable helper, OR a new sibling helper in `cli.py` / a `config_init.py` module — planner's call on placement) and emits a complete YAML scaffold to **stdout** by default.
- **D-22:** Emitted scaffold shape: top-level `version: 1`, then a `tools:` block with one entry per discovered tool. Each entry contains commented defaults (e.g., `# skip: false`, `# call_arguments: {}`, `# judges: [clarity, disambiguation, parameters]`) so the user can uncomment + edit. Includes a header comment block citing this phase + linking the README's per-tool-config section (Phase 10 DOC-04 will fill that anchor).
- **D-23:** Output flags: `--output PATH` writes to file; without `--force`, refuses to overwrite an existing file at PATH (exit code 2 + stderr message). Exit code 0 on stdout-mode and successful file write. Discovery failure inherits the same hint as `_preflight` / `_resolve_tool_names` (260507-j6i pattern at `tests/conftest.py:107-119` and `fixtures.py:118-122`).
- **D-24:** `config-init` reuses `McpTestClient.__aenter__` (Phase 06 D-16 isolation-aware) — does NOT open-code `stdio_client`. Inherits the isolation contract for free at this fourth spawn site (after `_preflight`, `_owner_task`, and Phase 07's discovery hook).

### Claude's Discretion

- **CD-01:** `version: int` validation strategy — equality default (`Field(default=1, le=1, ge=1)`) vs. explicit `field_validator` raising on mismatch. Equality default is simpler but error message is generic ("Input should be ≤ 1"); custom validator gives clearer error ("config version 2 not supported by this build, expected 1"). Planner picks based on Pydantic 2 idiom in this codebase.
- **CD-02:** Whether to tighten top-level `Config.model_config` from `extra="ignore"` (current at `config.py:160`) to `extra="forbid"`. Tightening would catch typos at the root level (e.g., `targt:` instead of `target:`) but might break users with stale-but-tolerated YAML. Recommendation lean: tighten in this phase since v1.1 already revisits the schema; planner verifies impact on existing fixtures/config.example.yaml.
- **CD-03:** Where the rubric-ID registry lives — `rubrics.py` (each class has `id: ClassVar[str]`; module-level lookup function), or a dedicated `_rubric_registry.py` with a `RUBRIC_IDS: frozenset[str]` constant + resolver. Rubrics module already exists; planner picks the seam that doesn't grow it past readability.
- **CD-04:** Whether the unknown-tool-name warning (D-14, D-18) emits via `warnings.warn(...)` (Python warnings) or pytest's `request.config.issue_config_time_warning(...)` or a stderr print. Planner picks based on visibility in `uv run mcp-test-framework run` terminal output — must be visible without being part of the failure count.
- **CD-05:** Where the per-test guard lives for D-08/D-09 (`pytest.skip` for un-selected judges). Three viable placements: (1) inline at the top of TEST-05/06/07 bodies; (2) a small decorator (`@requires_judge("clarity")`) added to each judged test; (3) a fixture (`_judge_gate`) that test bodies request. Decorator is cleanest if Phase 09's reporter integration benefits from a marker; inline is shortest. Planner's call.
- **CD-06:** `config-init`'s emit format details — comments style, key ordering, whether to include the reserved `setup:` / `depends_on:` fields as commented examples (probably no — they're dormant for v1.1 and including them risks users assuming they work). Planner picks readable defaults.
- **CD-07:** Module placement of the `ToolConfig` model. Existing `models.py` houses sub-models; adding `ToolConfig` there is the obvious choice unless its size + helpers (validators, rubric-ID resolver wiring) push it past readability — in which case a new `tool_config.py` module is fine.
- **CD-08:** Plan-cut within the phase. Likely shape: P1 — schema land (ToolConfig + version + Config wiring + validators); P2 — runtime wiring (skip/judges guards in test bodies, call_arguments threading); P3 — `config-init` CLI; P4 — tests. Planner picks; the dependency edge schema → runtime → CLI → tests is the load-bearing constraint.

### Folded Todos

None — the only matched todo (`2026-05-07-v1-1-isolate-test-runs-from-user-state.md`, score 0.6) is the source todo for Phase 06 (already folded there) and out of scope for the per-tool config registry.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 08 row + "Phase 08: Per-tool config registry" details (goal, depends-on Phase 07, requirements, 5 success criteria)
- `.planning/REQUIREMENTS.md` §"TOOLCFG — Per-tool config registry" — TOOLCFG-01..TOOLCFG-07 acceptance criteria + traceability table
- `.planning/PROJECT.md` §"Current Milestone: v1.1" — anti-scope (xdist, OpenAI-compat, dynamic rubrics are deferred); §"Long-term Vision" → `Indicative milestone shape` table positioning v1.5+ stateful testing
- `.planning/MILESTONES.md` (if present) — v1.1 close-out criteria

### Predecessor phases (must read before touching schema/spawn paths)
- `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-CONTEXT.md` — D-01/D-02 (`target.tool_name = None` semantics, type widening), D-04 (config-init deferred TO this phase), D-10..D-12 (discovery-hook + cache, reusable for `config-init`'s tool list), D-13/D-14 (`target_tool` indirect-parametrize fixture shape — guards in this phase plug into it)
- `.planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md` — D-12..D-17 (`_isolated_home`, `_build_isolated_env`, isolation contract — `config-init`'s spawn site MUST honor)
- `src/mcp_test_framework/_isolation.py` — `_build_isolated_env(home: Path) -> dict[str, str]`. Any new spawn site (incl. `config-init`) MUST use this — env allowlist constant lives here.

### Forward-compat seeds (schema reservations honored here)
- `.planning/seeds/SEED-003-dynamic-judging-protocol.md` §"When to Surface" + §"Why This Matters" — TOOLCFG-04's string-ID `judges:` is the additive seam; Phase 08 MUST keep IDs as strings resolving to constants (no inline rubric data) so v1.3 promotes additively, not breakingly.
- `.planning/seeds/SEED-004-stateful-tool-testing.md` §"Breadcrumbs" + §"Vision-Pass Addendum" — `setup:` and `depends_on:` MUST be reserved (Optional, unused) in `ToolConfig` to keep v1.5+ stateful-testing additive (D-04, D-06).
- `.planning/seeds/SEED-005-pluggable-judge-backends.md` (if present in the seeds tree) — Judge Protocol seam already shipped; `judges:` field-shape must not depend on Ollama specifics.

### Project rules (binding)
- `CLAUDE.md` §"Architecture Notes" — MCP transport stdio only via `stdio_client`; framework treats homelab-mcp as black box; ruff TID251 + sys.modules guard; session-scoped fixtures; `asyncio.timeout` around subprocess/HTTP
- `tests/conftest.py` — `pytest_plugins = ["mcp_test_framework.fixtures"]`; `pytest_configure` sys.modules black-box guard; Phase 07 `pytest_generate_tests` discovery hook (lines 124-136). `config-init` may share the `_discover_tools` helper (lifted to a module-level location) or re-implement to avoid pytest dependency in CLI path.
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP design doc (test categories, judge contract, schema-validator contract — unchanged for v1.1)
- `.python-version` + `pyproject.toml` — Python 3.14, `uv` toolchain, `pytest-asyncio` strict mode (asyncio_default_fixture_loop_scope = "session")

### Implementation seams (existing code to modify)
- `src/mcp_test_framework/models.py` — sub-model home (`OllamaConfig`/`McpServerConfig`/`TargetConfig` at lines 27/47/67). New `ToolConfig` lands here per CD-07 unless size pushes it elsewhere.
- `src/mcp_test_framework/config.py` — `Config` class at line 149: add `version: int = 1` and `tools: dict[str, ToolConfig] = {}` fields; review `extra="ignore"` at line 160 per CD-02; `_BareNameNestedEnvSource` at lines 91-146 walks per-field aliases (NOT extended for `tools.*` per D-19).
- `src/mcp_test_framework/rubrics.py` — `Rubric` base + 3 concrete subclasses; rubric-ID surface lands here per CD-03.
- `src/mcp_test_framework/cli.py` — Typer commands; new `config-init` subcommand (D-21).
- `src/mcp_test_framework/fixtures.py` — `target_tool` fixture at line 353 (the indirect-parametrize-aware version from Phase 07 D-13). Per-test guards (D-08/D-09) hook in via fixture-or-decorator (CD-05).
- `src/mcp_test_framework/mcp_client.py` — `McpTestClient.__aenter__` at line 135. `config-init`'s spawn site reuses this (D-24); does NOT open-code `stdio_client`.
- `tests/test_mcp_tool_contract.py` — TEST-05..TEST-10 bodies. `call_arguments` threading at TEST-08/09/10 (D-11); judge-skip guards at TEST-05/06/07 (D-08/D-09).
- `tests/conftest.py` — `_discover_tools` at line 68: candidate for lifting to a CLI-shareable location for D-21's `config-init` reuse (CD-08).
- `config.example.yaml` (root) — add a worked `tools:` block + `version: 1` (Phase 10 DOC-04 polishes prose; this phase ships the example).

### Phase 04.1 lifecycle invariant (do NOT regress)
- `.planning/phases/04.1-*` — Phase 04.1 owner-task + anyio.Event fixture rewrite. New per-test guards must NOT introduce anyio cancel scopes spanning the yield. `config-init` is `asyncio.run(...)` from a sync CLI command — separate loop, tears down before any session-fixture-scoped loop runs (mirrors Phase 07 discovery hook).

### v1.0 architecture context
- `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` — host-state surface (any new spawn path inherits the same isolation reasoning)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing sub-model pattern** ([models.py:27-89](src/mcp_test_framework/models.py:27)) — `OllamaConfig` / `McpServerConfig` / `TargetConfig` show the established shape: `ConfigDict(frozen=True, populate_by_name=True)`, fields with `validation_alias=AliasChoices(...)` for env routing. `ToolConfig` follows this exactly EXCEPT it adds `extra="forbid"` (D-05) and skips env aliases (D-19).
- **Phase 07 discovery seam** ([conftest.py:68-81](tests/conftest.py:68)) — `_discover_tools(config) -> list[str]` is the exact shape `config-init` needs. CD-08 covers whether to share the helper (lift to a module CLI can import) or duplicate.
- **`McpTestClient.__aenter__`** ([mcp_client.py:135](src/mcp_test_framework/mcp_client.py:135)) — Phase 06 D-16 isolation-aware. `config-init` reuses unchanged.
- **260507-j6i hint pattern** ([conftest.py:107-119](tests/conftest.py:107) + [fixtures.py:117-122](src/mcp_test_framework/fixtures.py:117)) — the "MCP server command not on PATH" hint pointing users at `MCPTF_CONFIG_FILE` / `config.example.yaml`. `config-init` discovery-failure path inherits this hint (D-23).
- **Frozen Config + custom env source** ([config.py:149-194](src/mcp_test_framework/config.py:149)) — adding `version: int = 1` and `tools: dict[str, ToolConfig] = {}` is two new field declarations; `_BareNameNestedEnvSource` walks per-field aliases and naturally ignores the new `tools` dict (D-19).
- **`AsyncExitStack` ownership pattern** ([mcp_client.py:144](src/mcp_test_framework/mcp_client.py:144)) — `config-init`'s short-lived session inherits this pattern automatically via `McpTestClient`.

### Established Patterns
- **Layered config precedence** (config.py docstring): `CLI/init kwargs > env vars > .env > YAML overlay > defaults`. New `tools:` block lives in YAML overlay or programmatic `Config(tools={...})` per D-19.
- **Black-box rule** mechanically enforced via `ruff TID251` + `sys.modules` guard. `config-init` MUST NOT import any `homelab_mcp` symbol; it reads tool names from `list_tools()` only.
- **Test-module-level `pytestmark`** ([test_mcp_tool_contract.py:48](tests/test_mcp_tool_contract.py:48)) — uniform `[pytest.mark.asyncio(loop_scope="session")]`. New per-test guards added via decorator or fixture-request must respect this loop scope.
- **`pytest.exit(returncode=2)`** ([fixtures.py:115/135/143](src/mcp_test_framework/fixtures.py:115)) — preflight-abort exit code. `config-init` failures use `typer.Exit(code=2)` (or equivalent) for symmetry with `mcp-test-framework run` exit semantics.
- **No anyio cancel scope across the yield** ([fixtures.py:179-205](src/mcp_test_framework/fixtures.py:179) docstring + Phase 04.1). Per-test judge-skip guards must respect this — `pytest.skip(reason=...)` BEFORE awaiting any fixture-owned async resource.

### Integration Points
- **Top-level `Config`** ([config.py:149](src/mcp_test_framework/config.py:149)) — two new fields (`version`, `tools`); `extra="ignore" → "forbid"` per CD-02 candidate; sources tuple unchanged.
- **`target_tool` fixture** ([fixtures.py:353](src/mcp_test_framework/fixtures.py:353)) — already indirect-parametrized per Phase 07 D-13. Per-test guards are upstream (test bodies) of this fixture; the fixture itself doesn't need to know about skip/judges.
- **TEST-08/09/10 call_tool sites** ([test_mcp_tool_contract.py:170-234](tests/test_mcp_tool_contract.py:170)) — three `mcp_client.call_tool(target_tool.name, {})` calls. Each becomes `mcp_client.call_tool(target_tool.name, tool_config.call_arguments)` where `tool_config` is resolved from `config.tools.get(target_tool.name, ToolConfig())` (default = no-op).
- **TEST-05/06/07 entry** ([test_mcp_tool_contract.py:99-162](tests/test_mcp_tool_contract.py:99)) — top-of-body or decorator gate emits `pytest.skip(...)` when the rubric ID isn't in the tool's `judges` list (D-08).
- **`config-init` CLI** — new Typer subcommand in `cli.py`; sibling to existing `run` / `list-tools` / `version`. Follows the existing `app = typer.Typer()` registration pattern.
- **`config.example.yaml`** (root) — gains a worked example block. Phase 10 DOC-04 references it.

</code_context>

<specifics>
## Specific Ideas

- **`tools:` keying.** Use the **bare tool name** as the dict key (matches the strings returned by `list_tools()`). No slugification; tool names are already shell- and YAML-safe per Phase 07's test-ID-rendering analysis.
- **Empty list vs None for `judges`.** `judges: None` (default / unset) → run all rubrics. `judges: []` (explicit) → run NO rubrics for this tool — useful for "I want this tool exercised by call_tool only, skip all judging." See D-07.
- **Warning channel for unknown tool names (D-14/D-18).** Land at session start (post-discovery), not load-time. Stderr or pytest warning system per CD-04. Visible without being a failure.
- **`config-init` output format.** YAML with comment headers explaining the structure. Tool entries are commented-out by default so `mcp-test-framework config-init > config.yaml` produces a working pass-through file (no surprise behavior change). The user uncomments + edits to opt in.
- **Worked example for `config.example.yaml` should reference real homelab-mcp tools** — minimal showcase: one tool with `skip: true` + `skip_reason`, one with `judges: [clarity]`, one with `call_arguments: {…}`. Each illustrates one knob. Phase 10 DOC-04 polishes the README prose around it.
- **Rubric-ID strings are LOCKED** as `clarity`, `disambiguation`, `parameters` (TOOLCFG-04 + D-10). These are the IDs documented in `config-init` output, README (Phase 10), and the validator's allow-list. v1.3 SEED-003 may add more; the v1.1 set is fixed.

</specifics>

<deferred>
## Deferred Ideas

- **Stateful testing fields (`setup:`, `depends_on:`) runtime semantics** — schema-only in this phase per D-06. SEED-004 / v1.5+ activates them additively. Trigger: `/gsd-new-milestone` after v1.4 lands, OR a user files a request to test a stateful tool.
- **Dynamic rubric data in `judges:`** — v1.1 stays at string-IDs-resolving-to-constants (TOOLCFG-04). SEED-003 / v1.3 promotes to rubrics-as-data additively. Trigger: v1.3 milestone open OR per-tool judge counts diverge significantly across users.
- **`extra_env` per-tool overrides** (a tool that legitimately needs the real keyring) — re-deferred from Phase 06 deferred. Adding to `ToolConfig` would be a clean home; ship only when a real use case arrives.
- **Env-var routing for `tools.*`** — explicit non-goal in v1.1 (D-19). Trigger: a user reports needing per-tool overrides in a CI environment where YAML editing is impractical.
- **Tightening top-level `Config` `extra="ignore" → "forbid"`** — CD-02 leans yes-ship-this-phase but flagged as discretion. Trigger: planner's review of impact on existing `.env` / fixtures / `config.example.yaml`.
- **Hard-fail on unknown tool names in `tools:`** — D-14/D-18 chose warning over hard-fail. Trigger: user feedback that warnings get swallowed in CI logs and silent-omission bugs return.
- **`config-init` interactive mode** (TUI prompt for skip / judges / args per tool) — out of scope for v1.1; YAML output + manual edit is sufficient. Trigger: usability complaint that hand-editing YAML is high-friction.
- **`config-init --merge`** (preserve existing config when re-emitting after server-side tool list changes) — out of scope. v1.1's `--force` overwrite + manual diff is enough. Trigger: tool-list churn becomes a real workflow problem.
- **Versioned rubric IDs** (e.g. `clarity@v2`) — SEED-003 / v1.3 territory; v1.1 IDs are bare strings.

### Reviewed Todos (not folded)

- **`2026-05-07-v1-1-isolate-test-runs-from-user-state.md`** (matched score 0.6) — reviewed but not folded. This is the source todo for Phase 06; already folded there. Reference here only because the keyword match flagged "test/user/phase/framework/config" — Phase 08's per-tool config concern is unrelated to user-state isolation.

</deferred>

---

*Phase: 08-per-tool-config-registry*
*Context gathered: 2026-05-07*
