# Phase 1: Foundation & Pure-Data Core - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Bootstrap the project skeleton and ship the I/O-free core. Specifically:

1. `uv` install + lockfile that produces a clean Python 3.14 environment on a fresh checkout
2. `pytest-asyncio` configured strict + session loop scope
3. Mechanical lint enforcement of the black-box rule (no `import homelab_mcp` under `src/` or `tests/`)
4. `config.py` (+ `models.py`) loading config with precedence `CLI > env > YAML > defaults` via `pydantic-settings[yaml]`, returning a frozen `Config`
5. `schema_validator.py` performing the 7 deterministic structural checks from the spec, returning `list[ValidationIssue]`
6. `.env.example` and `config.example.yaml` enumerating every configurable setting

**Not in scope (other phases):** any subprocess (Phase 2), any HTTP/judge code (Phase 3), any pytest fixtures or test cases that touch live `homelab-mcp` or Ollama (Phase 4), any CLI surface (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### ValidationIssue severity model
- **D-01:** All 7 schema checks return `severity="error"`. There is no `warning` tier in MVP output.
- **D-02:** The `severity` field stays on the `ValidationIssue` Pydantic model so a `warning` tier can be added post-MVP without a schema migration. Use `Literal["error"]` (not bare `str`) to make adding `"warning"` a typed change.
- **D-03:** Phase 4 `TEST-02` (`test_tool_schema_is_structurally_valid`) asserts `validate_tool_schema(tool) == []` (empty list) — equivalent to "no errors" because errors are the only severity.
- **D-04:** Check #6 (every property has a `description`) and check #7 (every property has `type`/`oneOf`/`anyOf`) are both errors. Rationale: the framework's whole pitch is judging an MCP tool's contract quality — a tool that ships unannotated parameters fails the contract by design. For the MVP target `list_registered_servers`, these checks are likely vacuous (no input parameters), so this stricture has zero observable cost in Phase 4.
- **D-05:** Note for Phase 4: TEST-02 (full schema validity) and TEST-04 (`test_input_schema_properties_are_documented`) overlap on checks #6 and #7. This is intentional redundant coverage, not a bug — TEST-04 is a focused diagnostic, TEST-02 is the full sweep.

### Claude's Discretion
The user passed on these areas — planner/executor has flexibility within the constraints below:

- **Env var naming convention:** Default to spec-verbatim bare names (`OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, `MCP_SERVER_ARGS`, `TARGET_TOOL_NAME`, `JUDGE_TIMEOUT_SECONDS`, plus `OLLAMA_MODEL` and `OLLAMA_TIMEOUT_SECONDS` to match the YAML schema in spec §Configuration). Document in README that for collision-prone shells, users can use a `.env` file scoped to the project. Revisit if collisions bite in practice.
- **`models.py` contents:** Lives in `src/mcp_test_framework/models.py`. Contains `Config` and its sub-models (`OllamaConfig`, `McpServerConfig`, `TargetConfig`) — the cross-cutting data layer. `ValidationIssue` stays in `schema_validator.py` (domain-local) and `JudgeResult` stays in `ollama_judge.py` (domain-local). Rationale: only `Config` is consumed by *every* module; domain models stay next to their producers.
- **`tests/` directory structure:** Use `tests/unit/` for the Phase 1 pure-data unit tests (`tests/unit/test_config.py`, `tests/unit/test_schema_validator.py`) and reserve flat `tests/` for Phase 4's integration tests (`tests/test_homelab_list_registered_servers.py`). Single `conftest.py` at `tests/conftest.py` owns the session-scoped fixtures from Phase 4. `pyproject.toml` `[tool.pytest.ini_options]` `testpaths = ["tests"]` picks up both. No marker-based separation needed for MVP.
- **Lint enforcement mechanism (SETUP-03):** Use ruff's `flake8-tidy-imports` rule `TID251` (`banned-api`) configured in `[tool.ruff.lint.flake8-tidy-imports.banned-api]` to ban `homelab_mcp` and `homelab_mcp.*`. Scope to `src/` and `tests/` (the spec's wording) — repo-tooling and `docs/` are unaffected. Verify with a deliberately-failing fixture file or a doctest of the rule itself.
- **YAML config discovery:** No auto-discovery in MVP. Path comes from `--config PATH` CLI flag (Phase 5) or the `MCPTF_CONFIG_FILE` env var (Phase 1 needs to support env-var-driven path so unit tests can exercise the YAML overlay without a CLI). If neither is set, no YAML overlay is applied. Defaults + env vars suffice. Revisit if users complain.
- **`Config` immutability:** `model_config = SettingsConfigDict(frozen=True)` on the top-level `Config` model. Sub-models inherit via the same config. Required for safe session-scoped fixture sharing across async tests in Phase 4.
- **`ValidationIssue.path` representation:** JSON-Pointer-style string (e.g., `/inputSchema/properties/foo/description`) — matches `jsonschema`'s native error path output, easiest to surface in `pytest` failure diagnostics.

</decisions>

<specifics>
## Specific Ideas

- "Errors only — drop warning" was the user's explicit pick; preserving the `severity` field for forward-compat was the recommended framing they accepted.
- Spec §Configuration is the source of truth for which settings exist. Don't invent new ones in Phase 1; new settings get added in the phase that needs them.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning Phase 1.**

### Phase 1 source-of-truth specs
- `docs/mcp_test_framework_mvp_spec.md` — Authoritative MVP spec. Read §Module Layout, §Configuration, §Component Specifications/`schema_validator.py`, §Implementation Notes for Claude Code. The 7 schema checks (CORE-02) and the env-var/YAML schemas (CORE-01, DOCS-02) come from here.
- `.planning/REQUIREMENTS.md` §Project Setup, §Core Modules, §Documentation — Phase 1 requirements (SETUP-01..03, CORE-01, CORE-02, DOCS-02). These are the falsifiable acceptance items.
- `.planning/ROADMAP.md` §Phase 1 — Goal statement and the 6 success criteria the verifier will check.

### Project-wide constraints
- `.planning/PROJECT.md` §Constraints, §Key Decisions, §Out of Scope — Black-box principle, stack pin, spec exists, single-target-tool MVP.
- `.planning/STATE.md` §Accumulated Context > Decisions — Config precedence locked as `CLI > env > YAML > defaults` (overrides spec's "YAML > env" wording); `homelab-mcp` is NOT a dev dep but the lint rule still ships; Phase 0 merged into Phase 1 because both are pre-I/O.
- `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout — restates spec invariants in CLAUDE-readable form. Useful for cross-checking.

### Stack research (read before declaring deps in pyproject.toml)
- `.planning/research/STACK.md` — Recommended versions (`pytest 9.0.3`, `pytest-asyncio 1.3.0`, `pydantic-settings 2.14.0`, `jsonschema 4.26.0`), pyproject snippet, "What NOT to Use" table (no `python-dotenv` direct dep, no `pyyaml` direct dep, no Pydantic v1, no raw `subprocess.Popen`), version-compatibility matrix for Python 3.14.
- `.planning/research/ARCHITECTURE.md`, `.planning/research/FEATURES.md`, `.planning/research/PITFALLS.md`, `.planning/research/SUMMARY.md` — Background on the integration shape and known gotchas; consult if planning surfaces ambiguity.

### Locked decisions inherited from earlier work (don't re-derive)
- Stack: `uv`, `pytest 9.x`, `pytest-asyncio 1.x` strict + session loop scope, `pydantic-settings[yaml]`, `jsonschema` (Draft auto-detected via `validator_for`), `httpx`, `typer`. Source: `.planning/research/STACK.md`.
- Module layout per `docs/mcp_test_framework_mvp_spec.md` §Module Layout, plus `judge_protocol.py` from REQUIREMENTS CORE-04 (Phase 3, not Phase 1, but locked).
- Black-box principle enforced via ruff (SETUP-03) — see "Claude's Discretion" decision above for mechanism.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml` (existing) — Currently a stub from `uv init`. Has `name = "mvp-test-framework"` (note: hyphen, not underscore — the package directory will be `mcp_test_framework` per spec, distinct from the project name). Phase 1 will rewrite this substantially: add deps, add `[tool.pytest.ini_options]`, add `[tool.ruff.lint.flake8-tidy-imports.banned-api]`, add the `[project.scripts]` entry point (`mcp-test-framework = "mcp_test_framework.cli:app"` — wired in Phase 5 but the entry point can land here harmlessly).
- `.python-version` (existing) — Pins `3.14`. Don't touch.
- `main.py` (existing) — Hello-world stub. Delete during Phase 1 once `src/mcp_test_framework/__init__.py` lands. Nothing depends on it.

### Established Patterns
- None yet — greenfield project, Phase 1 establishes the patterns the rest of the codebase follows. Specifically:
  - Pydantic v2 `BaseModel` for every cross-module data shape (`Config`, `ValidationIssue`, `JudgeResult`)
  - `pydantic-settings` `BaseSettings` for `Config` only — domain models use plain `BaseModel`
  - JSON-Pointer-style strings for any "where in the schema" path field
  - All public APIs that touch I/O are async (locks in for Phase 2/3)

### Integration Points
- `Config` is the only Phase 1 export consumed by downstream phases (Phase 2 `McpTestClient` reads `config.mcp_server.{command, args}`; Phase 3 `OllamaJudge` reads `config.ollama.{base_url, model, timeout_seconds}`; Phase 4 fixtures read `config.target.tool_name`). Treat the `Config` schema as a stable contract starting Phase 1.
- `validate_tool_schema(tool)` is consumed by Phase 4 TEST-02 only. `tool` is the `mcp.types.Tool` from the SDK — Phase 1 should accept the SDK type signature now (don't re-invent a `Tool` shim) so Phase 4 doesn't need a translation layer.

</code_context>

<deferred>
## Deferred Ideas

- **Add `warning`/`info` severity tiers** — `ValidationIssue.severity` is typed `Literal["error"]` for now. Add new literal values (and `Draft202012Validator`-derived softer checks) in a post-MVP phase if real tools surface non-blocking quality issues that deserve their own tier.
- **Auto-discover `config.yaml` in cwd** — MVP requires `--config` or `MCPTF_CONFIG_FILE`. Add cwd auto-discovery if users complain in practice.
- **Prefixed env vars (`MCPTF_*`)** — Stay with spec-verbatim bare names. Reconsider if collisions with co-installed Ollama/MCP tooling bite users.

</deferred>

---

*Phase: 01-foundation-pure-data-core*
*Context gathered: 2026-05-04*
