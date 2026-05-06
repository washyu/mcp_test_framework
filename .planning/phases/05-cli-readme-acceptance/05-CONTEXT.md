# Phase 5: CLI, README & Acceptance - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship the `mcp-test-framework` Typer CLI (`run` / `list-tools` / `version`), wire clean Ctrl+C teardown of the MCP subprocess (OPS-03), write the README and a small `docs/EXTENDING.md`, and prove acceptance from a clean clone. Closes Milestone v1.0.

**In scope:**
1. `src/mcp_test_framework/cli.py` — Typer app exposing three commands: `run`, `list-tools`, `version`. Wired into `[project.scripts]` in `pyproject.toml` (already reserved, currently commented out).
2. `run` command — owns `--config PATH` only; everything after `--` forwards to `pytest.main()`. No try/except wrapping; pytest's own SIGINT handling + Phase 04.1's `AsyncExitStack`-owned `mcp_client` fixture covers OPS-03 for the `run` path.
3. `list-tools` command — owns `--config PATH` and `--json`. Default output is indented blocks (name on one line, full description indented beneath). `--json` emits a JSON array of `{name, description, inputSchema, outputSchema}` per tool (full MCP tool record). Uses `asyncio.Runner` + `AsyncExitStack` to own the `McpTestClient` lifecycle — same pattern as Phase 04.1's pure-asyncio fixture body. Does NOT invoke pytest or Ollama (CLI-02).
4. `version` command — prints package version (CLI-03). Source is Claude's discretion (recommend `importlib.metadata.version("mvp-test-framework")`; the script entry point name is `mcp-test-framework` but the package distribution name in `pyproject.toml` is `mvp-test-framework`).
5. `README.md` — quickstart-focused (~150 lines): setup (`uv sync`), commands (`run`, `list-tools`, `version`), env-var markdown table (var, default, purpose), precedence rule (CLI flag > env > .env > YAML > default), Windows troubleshooting (`taskkill /F /IM homelab-mcp.exe`), 10–15 line green-run pytest output sample, and a link to `docs/EXTENDING.md`.
6. `docs/EXTENDING.md` — recipes for adding a new rubric (subclass `Rubric`, drop in a fixture in user conftest) and swapping the judge backend (implement the `Judge` Protocol). Sibling doc; README links to it.
7. `.env.example` — already exists from Phase 1/2/2.1; Phase 5 verifies it stays in sync with the README env-var table. No new env vars added this phase.
8. `pyproject.toml` — uncomment `[project.scripts] mcp-test-framework = "mcp_test_framework.cli:app"`. No new dependencies (Typer is already transitive via `mcp[cli]`).

**Not in scope (other phases / explicit deferrals):**
- Per-config-field CLI overrides (`--ollama-url`, `--mcp-command`, etc.) — env-var override on the command line is sufficient for MVP.
- Custom test runner (replacing pytest) — explicitly seeded as a post-MVP question (Deferred Ideas).
- Automated regression test for OPS-03 — manual UAT in `/gsd-verify-work` is the agreed verification path.
- Reference-grade README (FAQ, full extension guide inline) — quickstart-focused; extension content lives in `docs/EXTENDING.md`.
- Auto-generated env-var docs from Pydantic schema — manual table + .env.example for MVP.
- `--json-fields` filter on `list-tools --json` — full tool spec is the MVP output; YAGNI.
- Interrupt message on Ctrl+C — `list-tools` exits cleanly with code 130, no message.
- `_preflight` reuse in `list-tools` — CLI-02 says "without invoking Ollama"; `list-tools` only checks MCP reachability inline (the `McpTestClient` __aenter__ + list_tools() round-trip).
- New v2-Plus capabilities (LLM-generated test inputs, multi-server runs, JSON test output, JUnit XML) — out of scope per REQUIREMENTS.md.

</domain>

<decisions>
## Implementation Decisions

### `run` command flag surface

- **D-cli-flags-1:** `run` owns ONLY `--config PATH`. No per-Config-field override flags (`--ollama-url`, `--mcp-command`, etc.) — users override individual settings via env vars on the command line (e.g., `OLLAMA_BASE_URL=http://other:11434 uv run mcp-test-framework run`). Honors PROJECT.md's "CLI flags = highest precedence" semantically (the only CLI-owned setting IS `--config`); avoids growing a second source of truth that has to mirror `models.py`.
- **D-cli-flags-2:** Pytest flags reach pytest via the `--` separator. Canonical invocation: `mcp-test-framework run --config foo.yaml -- -x --lf -k pattern`. Typer is configured with `context_settings={"allow_extra_args": False}` for the `run` command's primary surface, but everything after `--` is collected and passed straight to `pytest.main([test_dir, *forwarded])`. Future-proof against CLI flag collisions; matches git/cargo/npm conventions.
- **D-cli-flags-3:** `run` does NOT wrap `pytest.main()` in try/except. pytest's own SIGINT handling cancels the test, finalizers run, the session-scoped `mcp_client` fixture's `AsyncExitStack` (Phase 04.1) unwinds, and `stdio_client` terminates `homelab-mcp.exe`. The CLI just calls `pytest.main([test_dir, *forwarded])` and returns its exit code. Fewest moving parts; OPS-03 falls out for free on the `run` path.

### `list-tools` command output

- **D-list-1:** Default text output is indented blocks: tool name on its own line, full description (wrapped) indented beneath. No schemas, no parameters in default mode. Matches CLI-02 spec literally ("tools with their descriptions").
- **D-list-2:** `--json` flag emits a JSON array of full MCP tool records: `[{name, description, inputSchema, outputSchema}, ...]`. Maximum scriptability — directly consumable by future LLM-test-generator work (SEED-001 / GEN-01) without re-fetching.
- **D-list-3:** Default text output renders the FULL description (wrapped to terminal width or a fixed ~80 col), not a one-line truncation. Multi-line descriptions print their full body indented under the name. List-tools is for human discovery, not pipeable summaries.
- **D-list-4:** Sort order in both text and JSON output is Claude's discretion (recommend alphabetical by name for stability across runs; the MCP `list_tools` response order is server-defined and may not be stable).

### `list-tools` lifecycle and Ctrl+C

- **D-teardown-1:** `list-tools` body uses `asyncio.Runner` (3.11+) + `AsyncExitStack` to own the `McpTestClient` lifecycle. Default asyncio behavior on SIGINT raises `KeyboardInterrupt` inside the running task; `AsyncExitStack.__aexit__` runs and `stdio_client` cleans up the subprocess. Same pattern as Phase 04.1's pure-asyncio fixture body — reuses lessons learned, avoids re-introducing the cancel-scope teardown bug at the CLI surface.
- **D-teardown-2:** OPS-03 verified by manual UAT in `/gsd-verify-work`. Verifier runs `mcp-test-framework list-tools` in one terminal, hits Ctrl+C mid-call, then runs `Get-Process homelab-mcp` in another and asserts no matches. Documented as a UAT step. Matches Phase 04.1's manual-verification pattern; avoids the cross-platform process-enumeration flakiness an automated regression test would carry.
- **D-teardown-3:** No partial-output message on Ctrl+C. `list-tools` exits cleanly with code 130 (standard SIGINT). No "Interrupted before tools could be listed" line printed. Subprocess teardown is the only hard requirement.

### README and extension docs

- **D-readme-1:** README is quickstart-focused, ~150 lines. Sections: project one-liner → prerequisites (Python 3.14, `uv`, Ollama at the configured base_url, `homelab-mcp` runnable via `uvx`) → setup (`uv sync`) → commands (`run`, `list-tools`, `version` each with one-shot example) → configuration (env-var table + precedence rule + `.env.example` reference + YAML overlay note) → 10–15 line green-run pytest output sample → Windows troubleshooting (`taskkill /F /IM homelab-mcp.exe`, the cancel-scope history, where logs go) → links to `docs/mcp_test_framework_mvp_spec.md` and `docs/EXTENDING.md`. No FAQ, no "how to extend" body.
- **D-readme-2:** Extension recipes (add a new rubric, swap the judge backend) live in a separate `docs/EXTENDING.md`. README links to it. Two recipes for MVP: (1) "Add a new description-quality rubric" — subclass `Rubric`, define a session-scoped fixture in user conftest, write `test_x(judge, target_tool, your_rubric)`; (2) "Swap the judge backend" — implement the `Judge` Protocol from `judge_protocol.py`, override the `judge` fixture in user conftest. Cleanest path if extension docs grow over time.
- **D-readme-3:** README includes a 10–15 line sample of the typical green pytest terminal output (the 10 PASSED lines + summary). Sets first-run expectations for SC#6 ("standard pytest terminal output and exits 0") so acceptance is unambiguous. Sample comes from a real green run — not synthetic — captured during planning or execution.
- **D-readme-4:** Env vars are documented in TWO places: the README's markdown table (var, default, purpose) AND `.env.example` (copy-paste starter, already shipped). Discipline keeps them in sync — the README table is the human-readable index, `.env.example` is the executable copy-paste form. No auto-generation from the Pydantic model for MVP (Plant-Seed candidate if drift becomes painful).

### Claude's Discretion

The user passed on these — planner/executor has flexibility within the constraints below:

- **`version` source:** Recommend `importlib.metadata.version("mvp-test-framework")` (the package's distribution name in `pyproject.toml`, distinct from the `mcp-test-framework` script name). Falls back to a hardcoded constant only if `metadata` lookup fails. Don't parse `pyproject.toml` at runtime.
- **`--config` error handling:** When `--config PATH` doesn't exist or fails to parse, propagate the Pydantic / file-not-found error with a clean one-line CLI diagnostic. Don't catch and re-wrap — Pydantic's own messages are good enough for MVP. Exit code 2 (usage error) on config failure to mirror pytest's own conventions and Phase 4 D-markers-2.
- **Typer app shape:** Recommend `app = typer.Typer(no_args_is_help=True, add_completion=False)` so `mcp-test-framework` with no command prints help instead of exiting silently. `add_completion=False` keeps the CLI surface predictable (no `--install-completion` clutter).
- **`run` command body internals:** Whether to call `Config()` at the top of `run` (and bail early on config errors) or let `pytest.main()` trigger config loading via the session-scoped `config` fixture. Recommend loading at the CLI level so config errors fail BEFORE pytest's plugin chain gets involved (clearer diagnostics, no "INTERNALERROR" spam).
- **`list-tools` Config/timeout sourcing:** Use the same `Config()` loader as `run` — sets `MCPTF_CONFIG_FILE` env var if `--config PATH` is provided, then instantiates `Config()`. Wire `McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds)` exactly as the `mcp_client` fixture does. Keep this DRY by delegating to a small helper function (`_load_config(path: Path | None) -> Config`) used by both commands.
- **Sort and width for default `list-tools` output:** Alphabetical by name. Text wrapping at terminal width via `shutil.get_terminal_size()`, falling back to 80 columns. Don't add `rich` as a dependency — `textwrap.indent` + `textwrap.fill` from stdlib is sufficient.
- **`--json` output formatting:** `json.dumps(tools_array, indent=2, default=str)` for indented pretty-print. Trailing newline so it composes with shell pipelines. Tool order matches the default text output (alphabetical by name).
- **`docs/EXTENDING.md` structure:** Two H2 sections: "Add a new description-quality rubric" and "Swap the judge backend". Each contains a minimal code example (the subclass + the override fixture) and a one-paragraph "why" pointer. ~80–120 lines total. No deep-dive; surface-level recipe with file paths.
- **Sample-green-output capture:** Run the suite locally during execution, capture `pytest tests/` stdout, paste a 10–15 line excerpt into README. Don't manufacture the output — use a real run so the sample stays truthful.
- **README badge row:** Out of scope for MVP — no CI badges (no CI yet), no PyPI badge (not published). Skip the badge row entirely. Future addition once a CI lands.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before planning Phase 5.**

### Phase 5 source-of-truth specs
- `docs/mcp_test_framework_mvp_spec.md` §CLI / §Configuration / §Acceptance Criteria — Three-command CLI surface (`run`, `list-tools`, `version`), config precedence (CLI > env > YAML > default), and the 6 acceptance criteria SC#6 hinges on.
- `.planning/REQUIREMENTS.md` §CLI (CLI-01..CLI-03), §Operational (OPS-03), §Documentation (DOCS-01) — falsifiable acceptance for every Phase 5 deliverable; DOCS-02 (`.env.example` / `config.example.yaml`) is already complete from Phase 1.
- `.planning/ROADMAP.md` §Phase 5 — Goal statement and the 6 success criteria the verifier checks.
- `.planning/PROJECT.md` §Constraints, §Key Decisions, §Out of Scope — black-box principle (CLI never imports `homelab_mcp`), single-server / single-tool MVP scope, "pytest default output for MVP, no JSON/JUnit" applies to TEST output, NOT to `list-tools` output (different surface; `--json` is for the tool list, not test results).

### Project-wide constraints
- `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout — `cli.py` lives at `src/mcp_test_framework/cli.py`; Typer is the CLI framework (already transitive via `mcp[cli]`); MCP transport is stdio-only; `asyncio.timeout` wraps subprocess/HTTP calls.
- `.planning/STATE.md` §Accumulated Context > Decisions — pytest-asyncio strict + `asyncio_default_fixture_loop_scope=session`; Pydantic v2 frozen models; env-var bare-name convention. Phase 5 introduces no new env vars.
- `pyproject.toml` — `[project.scripts]` line is currently commented; Phase 5 uncomments it. `[tool.pytest.ini_options]` (`addopts = "-m 'not live_homelab and not live_ollama'"`) stays untouched — Phase 4 D-markers-3 contract.
- `.env.example` — canonical env-var copy-paste source; Phase 5 README table mirrors its content.

### Phase 1 prior decisions Phase 5 inherits
- `.planning/phases/01-foundation-pure-data-core/01-CONTEXT.md` — `Config()` shape (frozen sub-models, `OllamaConfig` / `McpServerConfig` / `TargetConfig`); env > .env > YAML > default precedence inside the loader; `MCPTF_CONFIG_FILE` env var as YAML overlay pointer.
- `.planning/phases/01-foundation-pure-data-core/01-LEARNINGS.md` — silent-default-fallback discipline (Phase 5 surfaces config failures with clean diagnostics, doesn't paper over them).
- `src/mcp_test_framework/config.py` `Config()` — Phase 5 CLI loads it directly (or via small helper) for both `run` and `list-tools`. `--config PATH` flag sets `MCPTF_CONFIG_FILE` env var before instantiation.

### Phase 2 prior decisions Phase 5 mirrors
- `.planning/phases/02-mcp-client-wrapper/02-CONTEXT.md` D-04..D-08 — `McpTestClient(command, args, timeout_seconds)` constructor; `__aenter__`/`__aexit__` lifecycle; `list_tools()` returns the tool list. Phase 5 `list-tools` instantiates this directly inside an `AsyncExitStack`.
- `src/mcp_test_framework/mcp_client.py` — `McpTestClient` API surface; `ToolNotFoundError` (not used by `list-tools` — only `target_tool` fixture catches that).
- `tests/smoke/test_smoke_homelab_mcp.py` — Reference shape for `list-tools` lifecycle (Config + AsyncExitStack + `McpTestClient` + `list_tools()` round-trip). Same scaffolding, different surface (CLI vs test).

### Phase 3 prior decisions Phase 5 inherits
- `src/mcp_test_framework/judge_protocol.py` — `Judge` Protocol. `docs/EXTENDING.md` "Swap the judge backend" recipe references this.
- `.planning/phases/03-ollama-judge/03-CONTEXT.md` D-05..D-10 — `OllamaJudge` constructor signature (referenced by `docs/EXTENDING.md` only; CLI never imports it).

### Phase 4 prior decisions Phase 5 inherits
- `.planning/phases/04-fixtures-test-cases/04-CONTEXT.md` D-markers-3 — `mcp-test-framework run` invokes `pytest.main([test_dir, *user_flags])` with NO extra `-m` flag. Default `addopts = "-m 'not live_homelab and not live_ollama'"` from `pyproject.toml` stays in effect. Phase 4 unmarked tests run by default. **This is the contract `run` must honor.**
- `.planning/phases/04-fixtures-test-cases/04-CONTEXT.md` D-layout-1 — `pytest_plugins = ["mcp_test_framework.fixtures"]` registration is in `tests/conftest.py`. `run` only needs to point pytest at `tests/`; fixture loading is automatic.
- `src/mcp_test_framework/fixtures.py` — session-scoped `mcp_client` fixture owns its `AsyncExitStack`; `pytest.main()` SIGINT handling unwinds it cleanly. **D-cli-flags-3** depends on this contract.
- `docs/EXTENDING.md` "Add a new rubric" recipe references Phase 4's `Rubric(BaseModel)` base class in `src/mcp_test_framework/rubrics.py` and the rubric-as-fixture pattern (D-rubrics-1, D-rubrics-2).

### Phase 04.1 prior decisions Phase 5 reuses (load-bearing for OPS-03)
- `.planning/phases/04.1-mcp-client-teardown-fix/04.1-CONTEXT.md` — owner-task + `anyio.Event` fixture-body driver; `AsyncExitStack` ownership pattern; pure-asyncio teardown semantics. **D-teardown-1 reuses this verbatim** for `list-tools`'s `McpTestClient` lifecycle.
- `.planning/phases/04.1-mcp-client-teardown-fix/04.1-01-SUMMARY.md` — verification status: "EXIT_CODE=0, 10 passed in 14.95s, no leftover homelab-mcp.exe". OPS-03 for the `run` path falls out for free; `list-tools` must apply the SAME pattern.
- `tests/smoke/test_smoke_homelab_mcp.py` regression smoke (added 04.1-01) — confirms full `mcp_client` lifecycle clean teardown. Reference shape for `list-tools` Ctrl+C UAT (manual reproduction of "no leftover process after Ctrl+C").

### Pitfalls research (mandatory pre-implementation read)
- `.planning/research/PITFALLS.md` Pitfall 1 — anyio cancel-scope teardown. `list-tools` body MUST use the Phase 04.1 pattern (asyncio.Runner + AsyncExitStack-owned `McpTestClient`). Re-introducing the cancel-scope bug at the CLI surface is the most likely Phase 5 regression.
- `.planning/research/PITFALLS.md` Pitfall 4 — Windows ProactorEventLoop subprocess cleanup. `list-tools` SIGINT path MUST verify on Windows specifically; OPS-03 manual UAT runs on the dev machine (Windows 11).
- `.planning/research/PITFALLS.md` Pitfall 5 — Undetected stdio termination. `asyncio.timeout()` already wraps every SDK call inside `McpTestClient` (Phase 2). `list-tools` inherits.
- `.planning/research/PITFALLS.md` Pitfall 8 — Black-box coupling via the backdoor. CLI must NOT import from `homelab-mcp` source — only via the `McpTestClient` subprocess.

### Stack research
- `.planning/research/STACK.md` — Typer (already transitive via `mcp[cli]`) is the locked CLI framework; no new dependency needed. `httpx` / `pydantic` / `pydantic-settings` / `mcp` SDK already locked. `importlib.metadata` (stdlib) for the version source.

### Seeds (informational, not Phase 5 deliverables)
- `.planning/seeds/SEED-001-agentic-tool-use-judge.md` — Trigger fired Phase 3 (dormant). `list-tools --json` output (full tool spec including `inputSchema` and `outputSchema`) is the natural input shape for an LLM-test-generator (GEN-01) — D-list-2 deliberately ships the full record so the seam is in place.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mcp_test_framework/config.py` `Config()` — Phase 5 CLI loads it for both `run` and `list-tools`. `--config PATH` sets `MCPTF_CONFIG_FILE` env var before instantiation; Pydantic-settings handles the rest. No new loader code needed.
- `src/mcp_test_framework/models.py` `OllamaConfig` / `McpServerConfig` / `TargetConfig` — Phase 5 reads these. Adds nothing.
- `src/mcp_test_framework/mcp_client.py` `McpTestClient` — Phase 5 `list-tools` instantiates directly. `__init__(command, args, timeout_seconds)`, `__aenter__` / `__aexit__`, `list_tools()` are the surface. `ToolNotFoundError` not used by CLI.
- `src/mcp_test_framework/fixtures.py` (Phase 4) — pytest discovers via `pytest_plugins = ["mcp_test_framework.fixtures"]` in `tests/conftest.py`. Phase 5 `run` doesn't touch fixtures directly; `pytest.main()` chain handles it.
- `pyproject.toml` `[project.scripts]` — Already reserved (commented): `mcp-test-framework = "mcp_test_framework.cli:app"`. Phase 5 uncomments and ensures the entry point resolves after `uv sync`.
- `pyproject.toml` `[tool.pytest.ini_options]` — `addopts = "-m 'not live_homelab and not live_ollama'"` stays untouched. **D-cli-flags-1's load-bearing contract.**
- `.env.example` — already comprehensive (Phase 1/2/2.1). Phase 5 README env-var table mirrors its content.
- `tests/smoke/test_smoke_homelab_mcp.py` — reference shape for `list-tools`'s Config + `McpTestClient` + `AsyncExitStack` body. Same scaffolding pattern, CLI surface instead of test surface.
- Existing `README.md` (12-line stub) — Phase 5 fully replaces this. Stub mention of "Phase 5" is the trigger that this section lands here.

### Established Patterns (from Phases 1–4)
- Pydantic v2 `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)` for cross-cutting models. `Config` already follows this; no new models needed in Phase 5.
- Async I/O lifecycle owned by `AsyncExitStack`. **MUST apply** to `list-tools` body (D-teardown-1 inherits from Phase 04.1).
- Domain-local types in their owning module (CLI logic stays in `cli.py`; small helpers like `_load_config(path)` can live there too — don't promote to `models.py` or a shared utility module without a second caller).
- `asyncio.timeout()` wraps every SDK call inside `McpTestClient`. Phase 5 inherits — `list-tools` doesn't add timeouts, just consumes the wrapped client.
- "Permanent live tests under `tests/smoke/` carry `live_<thing>` markers; integration tests are unmarked and gated by `_preflight`" (Phase 4 D-markers-1). Phase 5 doesn't change marker policy.
- Module entry points use `app = typer.Typer(...)` then `if __name__ == "__main__": app()`. `[project.scripts]` points at `mcp_test_framework.cli:app` (the Typer instance, not a function — Typer apps are callable).

### Integration Points
- `pytest.main([test_dir, *forwarded])` in `run` is the pytest seam. `forwarded` = the list of args after `--`. `test_dir` resolves from `Config()` or defaults to `"tests"` (whichever the planner picks; recommend `Config.test_dir` if it exists, else hardcode `"tests"`).
- `Config()` loading is shared between `run` and `list-tools`. Recommend a small `_load_config(config_path: Path | None) -> Config` helper in `cli.py` — sets `MCPTF_CONFIG_FILE` env var if path provided, then instantiates. Both commands call it.
- `McpTestClient` is the ONLY MCP entry point. CLI never imports `homelab_mcp` — black-box principle inherited.
- `.env.example` ↔ README env-var table is a manual sync point. Plan/execute should diff them before commit.
- `docs/EXTENDING.md` references `judge_protocol.py` and `rubrics.py` paths — those paths are stable from Phases 3 and 4. Recipe code samples can be tested by copy-pasting into a scratch conftest.

</code_context>

<specifics>
## Specific Ideas

- **"Are we just talking about being able to allow users to use the other pytest CLI arguments? what arguments are we tacking on that are custom?"** was the user's framing for the flag-surface discussion. Drove D-cli-flags-1: only `--config` is custom; `-k` and `-v` already exist in pytest and work for free via the `--` forward.
- **"I have just been thinking we are using pytest currently for the MVP for simplicity should we look at making it our own test executor after the mvp?"** was the user's open question about long-term direction. Captured as a Plant-Seed in Deferred Ideas (re-evaluate runner post-MVP). Recommendation in-thread: stay on pytest indefinitely; if a non-Python authoring surface is wanted, build a declarative layer (YAML conformance packs, LLM-generated specs) that compiles INTO pytest cases — don't replace the runner.
- **"Lets do 1 and add a seed to revalue pytest or just wrap it and add a pytest config file or go with our own or just leave it"** — explicit instruction to plant the seed with three concrete options (custom runner / wrap + pytest.ini / leave as-is).
- **`asyncio.Runner` + `AsyncExitStack` for `list-tools`** mirrors the Phase 04.1 pure-asyncio fixture-body driver. The user has already proven this pattern teardown-clean on Windows for the test path; reusing it for the CLI path means OPS-03's hardest case (`list-tools` Ctrl+C teardown) reuses a tested shape rather than introducing a new lifecycle pattern at the CLI surface.
- **Quickstart-focused README + separate `docs/EXTENDING.md`** — explicit user choice. Keeps the README readable in one sitting; extension docs live where they can grow without polluting the first-run path.
- **Sample green-run output in the README** — explicit user choice. Disambiguates SC#6 ("standard pytest terminal output and exits 0") and gives first-run users a concrete expectation to match against.

</specifics>

<deferred>
## Deferred Ideas

- **Re-evaluate the test runner post-MVP** *(seeded explicitly during this discussion)*. Three options to weigh after green: (1) replace pytest with a custom executor (declarative test specs, language-agnostic runner — huge build); (2) wrap pytest tightly + ship a `pytest.ini` and treat the framework's CLI as the only blessed entry point; (3) leave as-is — pytest stays the runner, the framework's value is the MCP-specific assertions + judge + black-box pattern. **Trigger:** when an external user (non-Python or non-pytest-fluent) needs to author MCP conformance tests OR when REQUIREMENTS v2 `CONFORM-01` / `GEN-01` / `PROP-01` lands. **Recommended path:** option 3 (stay on pytest), with a higher-level declarative layer compiling INTO pytest cases for those v2 requirements.
- **Per-config-field CLI overrides** (`--ollama-url`, `--ollama-model`, `--mcp-command`, `--target-tool`). Phase 5 uses env-var override on the command line for MVP. Add explicit CLI flags only when env-var ergonomics break down (e.g., scripting needs typed CLI args, or a future `--dry-run` workflow needs to inject values without env mutation).
- **Auto-generate env-var docs from the Pydantic Config model.** Phase 5 maintains README env-var table + `.env.example` manually. If/when the field count grows past ~10 or drift causes a real bug, build a small generator that emits the README table from `Config.model_fields`.
- **`--json-fields name,description` filter on `list-tools --json`.** MVP emits the full tool record. Add the filter when a real consumer needs a leaner output.
- **`rich`-formatted `list-tools` output / colored CLI output.** `rich` is not added as a dependency for MVP. Only consider when a non-trivial visual surface lands (multi-line summaries, per-test progress bars, etc.).
- **Automated regression test for OPS-03.** Phase 5 verifies via manual UAT (subprocess teardown after Ctrl+C). An automated test would spawn the CLI, send SIGINT cross-platform, then assert no `homelab-mcp.exe` matches via `Get-Process` / `pgrep`. Defer until OPS-03 regresses or until CI lands and has stable cross-platform process-enumeration.
- **CI badges / PyPI publish + badge row in README.** Skipped — no CI yet, package not published. Add when CI lands.
- **`mcp-test-framework lint` / schema-only command** that runs the Category 1 deterministic checks WITHOUT Ollama. Useful for "does this server's tool surface even meet the schema bar" quick checks. Currently covered by `uv run pytest tests/ -k schema` via the `--` forward, so YAGNI for MVP.
- **`docs/EXTENDING.md` deeper recipes** — adding a custom transport (when HTTP/SSE land in v2), parametrizing across multiple target tools (MULTI-01), running against a non-`homelab-mcp` server (the conformance-pack direction). MVP ships the two minimum recipes; deeper recipes accrete as v2 features land.
- **Interrupt message on Ctrl+C for `list-tools`.** D-teardown-3 chose silent exit code 130. If users find the silent exit confusing, add a single-line "Interrupted." message at the CLI top level — cheap retrofit.

### Reviewed Todos (not folded)

None — `gsd-sdk query todo.match-phase 5` returned `todo_count: 0`.

</deferred>

---

*Phase: 05-cli-readme-acceptance*
*Context gathered: 2026-05-06*
