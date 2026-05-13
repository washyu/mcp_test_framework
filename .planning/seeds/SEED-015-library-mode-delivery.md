---
id: SEED-015
status: dormant
planted: 2026-05-11
planted_during: v1.2 / post Phase 15 code-review gate (after WR-02 surfaced README sample-green-run drift)
trigger_when: When the operator-vs-CLI mental model starts feeling like a leak from framework-author ergonomics into the operator surface. Specifically surface during /gsd-new-milestone if the next milestone mentions: "library mode", "pytest plugin", "importable framework", "drop-in tests", "pyproject integration", "embedded testing", "operator adoption friction", "first-run UX", "no separate CLI", or any framing that treats `mcp-test-framework run` as one delivery channel among several. Also reconsider whenever a doc update is needed to the README "Sample green run" section — that section is the canary for the CLI-first model and the most-touched victim of every operator-surface change.
scope: Large
target_milestone: v1.3+ (could land as v1.3 milestone theme, or deferred to v2.0 if v1.3 takes another pass at operator UX polish)
---

# SEED-015: Library-mode delivery — `mcp_test_framework` as importable pytest contract library

Reframe the framework's primary delivery model from "external CLI runner the operator invokes against their MCP server" to "importable Python package the operator adds to their MCP server's own `tests/`". The operator writes three lines in their existing `tests/conftest.py`, runs `pytest` like they already do, and the framework becomes invisible — pure black-box contract validation that disappears into the operator's existing test workflow.

The motivating reframe (user's words, 2026-05-11, during Phase 15 close-out):

> "I wonder if we went the correct way for splitting out the tests. Rather, made this an importable Python package to add tests to an existing package, instead of trying to run this as an external package. This breaks the seed that a person vibecoded the app and it would just be a blackbox test."

## Why This Matters

**The CLI-first model leaks framework-author ergonomics into the operator surface.** The current v1.x story:

1. Operator clones `mcp_test_framework` (or installs it as a standalone tool)
2. Operator writes a `config.yaml` pointing at their MCP server command + tool allowlist
3. Operator runs `mcp-test-framework run` (or `--with-framework`, or `--raw`, or `list-tools`...)
4. Operator parses output from a custom domain UI that doesn't look like anything they've seen
5. Operator wires the CLI into their CI separately from their existing pytest pipeline

Every step is something the operator has to learn that exists *because the framework is a separate tool*, not because MCP contract testing is intrinsically complex. The vibe-coded persona memory (project_vibe_coded_persona) reframes the operator as someone who may not even know their SUT internals — every line of new tooling friction is hostile to that persona.

**The library-mode story:**

1. Operator adds `mcp-test-framework` to their MCP server's `pyproject.toml` dev-deps
2. Operator's existing `tests/conftest.py` gains three lines:
   ```python
   from mcp_test_framework.contracts import register

   register(
       server_command=["uvx", "my-mcp"],
       tools=["foo", "bar"],
       judge="ollama://127.0.0.1:11434/qwen3:0.6b",
   )
   ```
3. Operator runs `pytest` — the same command they ran yesterday — and now their MCP server has ~20 contract tests per tool exercising it
4. Output is pytest's native output (they already know it) plus optional `mcp_test_framework.report` plugin for the domain UI
5. CI is free — `pytest` is already wired

The framework's value proposition stays identical (schema validation + call shape + judge-scored description quality), but the delivery surface compresses to "an `import` and a `register()` call" — three lines in a file the operator already has.

**This breaks fewer things than it sounds like.** The contract-test logic in `tests/contract/test_mcp_tool_contract.py` is already a parametrized pytest test that takes `target_tool` and `mcp_client` fixtures. Moving it into `src/mcp_test_framework/contracts.py` as a `register()` function that calls `pytest.mark.parametrize` programmatically (or via a `pytest_plugin` entry point) is a refactor, not a rewrite. The framework's session-scoped fixtures (`mcp_client`, `judge`, `config`, `target_tool`) become pytest plugin fixtures that the operator's conftest pulls in automatically once they import.

## What Changes — Concrete Surface Sketch

**Operator's repo (their MCP server) — new state:**

```
my-mcp-server/
├── pyproject.toml          # adds [dev-dependencies] mcp-test-framework
├── src/my_mcp/...
└── tests/
    ├── conftest.py         # adds: from mcp_test_framework.contracts import register; register(...)
    ├── test_my_business_logic.py  # operator's existing tests, unchanged
    └── (contract tests are auto-injected by the register() call — no new files)
```

**Operator runs:** `uv run pytest` — the same command they already use. Their `test_my_business_logic.py` tests run alongside the framework-injected contract tests; they distinguish via pytest's `-k contract` or `-k not contract` selectors.

**This framework's repo — what stays / what moves:**

- `tests/contract/test_mcp_tool_contract.py` — **moves into `src/mcp_test_framework/contracts/`** as a function-call-driven test-injector. The pytest assertions are unchanged; the parametrize machinery moves from a static test file to a runtime `register()` API. The framework's own `tests/` folder keeps a small "dogfood" suite that calls `register()` against a fixture MCP server to prove the importable surface works.
- `tests/framework/` — **stays as-is.** Framework self-tests are an internal concern; they don't ship to operators.
- `src/mcp_test_framework/cli.py` (the `mcp-test-framework run` CLI) — **demotes to optional convenience.** Useful for operators who want a one-liner without touching `tests/conftest.py`, useful for CI scripts that want a single exit code, useful for `list-tools` / `config-init` / future maintenance commands. But not the *primary* surface.
- `src/mcp_test_framework/_runner.py` — **stays.** The CLI's pytest subprocess machinery is still needed for the CLI mode. Library mode bypasses it entirely (pytest runs natively in the operator's process).
- `config.yaml` schema — **stays for CLI mode, becomes optional for library mode.** Library-mode operators pass config as kwargs to `register()`; CLI-mode operators keep using `config.yaml`. Both paths land on the same `Config` Pydantic model.
- The domain UI (Phase 14's hybrid renderer) — **stays available, becomes an opt-in pytest plugin.** Operator who wants the domain UI adds `pytest --mcp-domain-ui` or sets it in their `pyproject.toml`'s `[tool.pytest]` section. Default pytest output is what most operators will see (and want — they already know how to read it).

**API surface — what's stable, what's experimental:**

| Surface | Stability target | Notes |
|---------|-----------------|-------|
| `mcp_test_framework.contracts.register(...)` | Stable v1.3+ | The primary entry point. Kwargs match `config.yaml` keys 1:1. |
| `mcp_test_framework.contracts.scoped_register(...)` | Stable v1.3+ | Same as `register()` but returns a fixture-scoped context manager for nested test classes. |
| Session fixtures (`mcp_client`, `judge`, `config`, `target_tool`) | Stable v1.3+ | Already plugin-fixture-shaped; auto-loaded once the operator imports anything from the package. |
| `mcp_test_framework.cli` (the `mcp-test-framework` command) | Maintained but secondary | Doesn't grow new flags unless library mode also benefits. |
| Domain UI plugin (`mcp_test_framework.report`) | Experimental v1.3, stable v1.4 | Naming TBD. Phase 14's parametrize-id-leak issue resolves naturally because the renderer is now reading test-node-ids from pytest's collection, not parsing JUnit XML. |

### Sub-item: Codegen output path must become configurable

**Surfaced 2026-05-13 during Phase 17 live UAT.** Phase 17's `gen-sdet-classes` command hard-codes the output root to `src/mcp_test_framework/sdet/generated/<server_slug>/` (locked by Phase 17 CONTEXT.md D-08 + REQUIREMENTS.md CODEGEN-01). That works for single-project dogfooding, but library-mode delivery breaks it:

- `pip install`'d `mcp_test_framework` lives in the consumer's `site-packages/` — usually read-only, blown away on upgrade, invisible to the consumer's IDE/test runner.
- Generated code must instead land in the consumer's own project tree (typical layout: `tests/_generated/<server_slug>/` next to their existing tests).
- Operators in library mode would want one of: (a) a config key like `sdet.generated_root: tests/_generated`, (b) a `--output-dir` CLI override, (c) auto-detection of "we're installed as a package vs. running from source", or (d) default to `tests/_generated/` whenever cwd has a `tests/` directory.

**Operator quote (2026-05-13):** "When we make this an importable package into an actual code folder they would probably want this to be in a test folder, not just the root."

**Design notes for the eventual implementation:**
- Whatever shape the override takes, D-09 (`tool("name")` is stringly-typed) means consumers must still import from a known module path. So the `register()` API (or its successor) needs to accept either an absolute import path or a filesystem path it can convert. Cleanest: config key holds the filesystem path, codegen writes there, and `register()`/`mcp_session` learns the same path so `_REGISTRIES[slug]` can be populated from it at test-collection time without operator-side import gymnastics.
- The wipe-and-write idempotence guarantee MUST be preserved for the new location — destination resolved at runtime, but blast radius still locked to `<resolved_root>/<server_slug>/` only.
- Decision D-08's spirit ("no `--output-dir` for v1.3") was about CLI flag complexity for the homelab-mcp dogfood case. Library-mode is the trigger for revisiting it.

## When to Surface

**Trigger:** When the operator-vs-CLI mental model starts feeling like a leak from framework-author ergonomics into the operator surface. Specifically:

- Whenever a doc update touches the README "Sample green run" section — that's the canary; if the sample needs to be redrafted yet again, the underlying delivery model is the real source of churn.
- Whenever an operator gives feedback about "this is too much tooling for what I want" or "why isn't this just a pytest thing?"
- During `/gsd-new-milestone` if the next milestone mentions: "library mode", "pytest plugin", "importable framework", "drop-in tests", "pyproject integration", "embedded testing", "operator adoption friction", "first-run UX", "no separate CLI"
- Whenever a v1.2+ plan proposes changing the CLI surface in a way that doesn't map cleanly to library mode — that's evidence the CLI is acquiring features that don't belong on it.

**Pairs naturally with:**

- **SEED-007 (vibe-coded-mcp-persona)** — this seed is the structural answer to the persona that SEED-007 named. The two should be cited together in any milestone planning.
- **SEED-009 (doc-and-example-cleanup)** — library mode reshapes the README from "how to run the CLI" to "how to add the library to your repo". The doc cleanup work should anticipate this if it lands first.
- **SEED-010 (operator-vs-framework-test-surface)** — Phase 15 split contract from framework *within this repo*. Library mode takes the next step: the contract surface leaves this repo entirely and ships as importable code.
- **SEED-011 (hybrid-runner-domain-ui)** — Phase 14 work. The domain UI becomes a pytest plugin in library mode rather than the CLI's render pass; the rendering logic is the same, the invocation seam changes.
- **SEED-014 (programmatic-sdet-test-authoring)** — library mode is the natural home for SDET-authored tests. The operator's `tests/` directory hosts both contract tests (injected by `register()`) and SDET-authored scenario tests (written by hand). The two flow through the same pytest collection.
- **SEED-006 (config-loading-safety)** — library mode bypasses much of the CLI's config-discovery machinery (the operator passes kwargs in code). But CLI mode still exists, so config-safety work doesn't go away.

## Scope Estimate

**Large** — milestone-sized. The pieces:

1. **`register()` API design (small plan).** The kwargs shape, validation, error messages. Probably mirrors `config.yaml` keys 1:1 so operators can switch between CLI mode and library mode without rewriting their config logic.

2. **Contract-test extraction (medium plan).** Pull the parametrize/assertion logic out of `tests/contract/test_mcp_tool_contract.py` into `src/mcp_test_framework/contracts/` as a function that programmatically injects parametrized tests into the calling test module. pytest's `pytest_collection_modifyitems` hook or a parametrize-builder helper. Test file becomes a 5-line dogfood: `from mcp_test_framework.contracts import register; register(server_command=[...], tools=[...])`.

3. **Pytest plugin entry point (small plan).** Register `mcp_test_framework` as a pytest plugin via `pyproject.toml`'s `[project.entry-points.pytest11]`. Auto-discovery means the operator's pytest picks up the framework's fixtures and CLI options without explicit conftest imports.

4. **Domain UI as plugin option (medium plan).** Phase 14's renderer currently runs as the CLI's post-pytest pass on a JUnit XML file. Library mode needs the renderer to attach to pytest as a reporter plugin — collecting events live, emitting domain-UI lines as tests complete. Phase 14's `_render_per_tool_rows` logic ports cleanly because it's already data-driven; the input changes from JUnit XML to pytest's `TestReport` objects.

5. **Migration story (small plan).** v1.3 ships both modes. Existing CLI users keep working. New users land on the library-mode README. v1.4 or v2.0 deprecates the CLI's primary-mode status (but doesn't remove the CLI — it stays for convenience scripts and CI one-liners).

6. **Doc rewrite — README + spec (medium plan).** README leads with "Add to your `pyproject.toml`, write three lines in `conftest.py`, run pytest." Spec gets a new top section explaining the two delivery modes and when to pick each. The current operator-CLI-flow language demotes to a "CLI usage" appendix.

7. **Phase 15 cleanups that get redirected here (small follow-ups).** Code review WR-02 (the README "Sample green run" sample, which would be rewritten in library mode rather than fixed in CLI mode). Any future operator-surface friction that surfaces as CLI bloat.

Could realistically land as v1.3 if v1.3 is dedicated to it. If v1.3 is another operator-UX polish pass instead, push to v1.4 or v2.0.

## Breadcrumbs

Related code (current v1.x — what library mode would build on):

- `src/mcp_test_framework/fixtures.py` — session-scoped pytest fixtures. Already shaped like a pytest plugin internally; library mode formalizes the plugin entry point.
- `src/mcp_test_framework/mcp_client.py::McpTestClient` — the async stdio client. Used by both modes unchanged.
- `src/mcp_test_framework/ollama_judge.py::OllamaJudge` — the judge. Used by both modes unchanged.
- `src/mcp_test_framework/schema_validator.py` — deterministic schema checks. Used by both modes unchanged.
- `tests/contract/test_mcp_tool_contract.py` — the parametrized contract test that becomes the import target. The assertions inside are the API contract; the file structure changes (function call instead of static test class).
- `src/mcp_test_framework/cli.py` — the CLI. Stays. Becomes the secondary entry point rather than the primary.
- `src/mcp_test_framework/_runner.py::ParsedRun` / `ToolVerdict` — Phase 14's domain model. Library mode's pytest reporter populates the same model from pytest events; the renderer is unchanged.
- `tests/conftest.py` (this repo's own) — the tool-discovery cache machinery. Library mode needs an equivalent that runs in the operator's repo without their having to copy-paste this file. Probably becomes another auto-injected fixture from the plugin.

Related decisions / constraints (must honor):

- **Black-box rule (CLAUDE.md):** No change. Library mode still treats the SUT as a stdio subprocess; the operator's `register()` call is configuration, not framework-internal coupling.
- **MCP transport contract:** stdio-only via `stdio_client` context manager. Unchanged.
- **Async discipline:** All tests stay async with `@pytest.mark.asyncio` markers in strict mode. The operator inherits this through the plugin's `pytest_asyncio` integration.
- **Operator-first design (v1.2 milestone theme):** This seed is the structural fulfillment of that theme. v1.2 sharpened the operator persona; v1.3+ delivers the persona-fit surface.
- **Memory item: project_dotenv_silently_beats_config** — library mode sidesteps most of the env/.env precedence confusion because the operator passes config as Python kwargs (no precedence puzzle). The CLI mode keeps the existing precedence rules.
- **Memory item: project_mcptf_config_file_silent_fail** — same. Library mode operators don't typo a config path because they don't have a config path; they have a `register(...)` call. The CLI mode's typo problem stays a CLI-mode concern.

Related seeds + planning artifacts:

- SEED-007 (vibe-coded-mcp-persona) — the persona this seed serves.
- SEED-009 (doc-and-example-cleanup) — README pivot work should be aware of library-mode direction.
- SEED-010 (operator-vs-framework-test-surface) — Phase 15. Establishes the contract/framework boundary that library mode formalizes as a package boundary.
- SEED-011 (hybrid-runner-domain-ui) — Phase 14. The renderer moves from CLI post-pass to pytest plugin.
- SEED-014 (programmatic-sdet-test-authoring) — library mode is the natural home for SDET tests.
- `docs/mcp_test_framework_mvp_spec.md` § "Future Work" — mentions "pluggable backends" and "broader tool surfaces" but doesn't articulate delivery mode. This seed fills that gap.
- Phase 15 `15-REVIEW.md` WR-02 — the README "Sample green run" sample that surfaced this question. The fix for WR-02 should be deferred to when this seed germinates.

## Notes

**Why this is a seed, not a Phase 16 plan:** Three reasons.

1. **v1.2 is mid-flight.** Phase 12, 13, 14, 15 are all operator-surface polish on the CLI model. Pivoting delivery mode while the CLI is still being refined creates a confusing "what's the source of truth right now" state. Finish v1.2 on the CLI model; pivot in v1.3 or later when the question is the milestone, not a Phase 15 sidebar.

2. **The pivot has irreversible doc churn.** README, spec, examples, config docs — all of it gets rewritten. Doing that twice (once for v1.2 polish, again for v1.3 pivot) is the worst of both worlds. Better to finish v1.2 doc state, then rewrite once for the pivot.

3. **The framework's own dogfooding loop needs to land alongside.** The library mode's contract surface should self-test (the framework's own `tests/` invokes `register()` against a fixture MCP server and asserts the right tests get injected and pass). That self-test is non-trivial — it's effectively a meta-pytest-on-pytest setup. Building it as part of the pivot, not bolted on after, is the only way it stays maintained.

**Open design questions to revisit when this germinates:**

- **CLI vs library mode coexistence policy.** Both modes stay forever, or library deprecates CLI on a long fuse, or CLI gets renamed (`mcp-test-framework-cli`?) to make the relationship clear? Probably both stay, no rename.
- **`register()` vs `register()`-like alternatives.** Could be a decorator (`@mcp_test_framework.contracts(server=..., tools=...)`), a fixture factory, an autouse plugin reading `pyproject.toml`. Each has UX tradeoffs. Start with `register()` (most explicit, hardest to misuse).
- **Plugin namespace.** `mcp_test_framework.contracts`? `mcp_test_framework.testing`? `mcp_test_framework.api`? The name signals to users where to find things. `contracts` aligns with the SEED-010 split language and is most descriptive of what the function does.
- **Discovery / list-tools surface in library mode.** Operator doesn't have a CLI in library mode. Do they call `mcp_test_framework.list_tools(server=...)` programmatically? Or do they keep using the CLI for ad-hoc discovery and library for testing? Probably both — the CLI's `list-tools` subcommand is genuinely useful for exploration and doesn't need to die.
- **Config schema versioning.** Library mode's `register()` kwargs are a Python API surface that needs semver discipline. The current YAML config has been changing freely; locking the API requires explicit versioning thinking.
- **CI ergonomics.** The current CLI has a clean exit code, a single command, fits into any CI step. Library mode requires the operator to wire pytest into their CI (most have already). Are there scenarios where the CLI is materially better for CI than library mode? Probably "smoke-test-only", which is a `pytest -k smoke` away in library mode anyway.
- **Naming the two modes for docs.** "Library mode" vs "CLI mode" works but is implementation-y. "Embedded mode" vs "Standalone mode"? "Plugin mode" vs "CLI mode"? Docs should name modes consistently from day one.

**If a user starts asking for library-mode surface before this seed germinates:** the right answer is "let's plan the v1.3 pivot now, this seed has the framing" — but the seed surfacing here will give the right framing for that conversation.
