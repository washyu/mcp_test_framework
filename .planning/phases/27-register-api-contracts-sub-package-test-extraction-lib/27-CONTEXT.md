# Phase 27: `register()` API + contracts sub-package + test extraction (LIB) - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

> ⚠️ **PHASE TITLE AND REQUIREMENTS SUPERSEDED BY THIS CONTEXT.**
> Discussion pivoted the load-bearing v1.4 technical bet away from `register()` to a pytest-native ini-driven config route. The roadmap title, REQUIREMENTS.md LIB-01..08 + CFG-01..02, and downstream Phase 28 + Phase 30 scope all need amending to match — see `<downstream_impact>` below. Planning should proceed against the decisions in this CONTEXT.md (which is what the operator-as-visionary chose), not against the now-stale roadmap/requirements text.

<domain>
## Phase Boundary

Operator's library-mode flow becomes **one line in `pyproject.toml`, no Python written**:

```toml
# operator's pyproject.toml — one line added
[tool.pytest.ini_options]
mcp_config_file = "./config.yaml"
```

```yaml
# operator's config.yaml — today's v1.3 schema, completely unchanged
mcp_server:
  command: uvx
  args: [homelab-mcp]
ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
tools:
  list_registered_servers:
    call_arguments: {include_metadata: true}
```

```bash
$ uv add mcp-contracts
$ pytest                        # contract tests appear, no conftest.py edits
```

**What ships in Phase 27:**

1. **`mcp_config_file` ini option** registered via `parser.addini()` in `src/mcp_test_framework/_plugin.py` (fills the Phase 26 hook skeleton).
2. **Plugin's `pytest_configure`** reads the ini value; if set, loads YAML → `Config`, stashes on `config._mcp_contracts_config`, invokes relocated black-box guard. If unset, no-op (operator opted out).
3. **Plugin's `pytest_collect_file`** (or `pytest_collection_modifyitems`) synthesizes a virtual `_ContractsModule` from extracted test bodies in `src/mcp_test_framework/contracts/_tests.py`, parametrized over `config.tools.keys()` per Phase 13 SAFE-01 opt-in semantics. Nodeids render as `<mcp-contracts>::test_<name>[<tool>]` via `nodeid` override on the synthesized Module.
4. **`mcp_contract` marker** applied at injection time (marker itself was registered in Phase 26 P26-02).
5. **Test bodies move** from `tests/contract/test_mcp_tool_contract.py` → `src/mcp_test_framework/contracts/_tests.py`. The framework's CI is rewired to run contract tests *only* through the library-mode injection path — see "Move + dogfood" decision below.
6. **Black-box guard relocation** per LIB-08: the `sys.modules` `homelab_mcp` check moves from `tests/conftest.py:pytest_configure` → `src/mcp_test_framework/_black_box_guard.py`, invoked from the plugin's `pytest_configure` (not from a `register()` call site, since `register()` is gone).
7. **`_preflight` predicate flip per LIB-07:** fires only when `mcp_config_file` ini value is set AND items carrying `@pytest.mark.mcp_contract` are collected. Replaces the live-prefix path allowlist in `fixtures.py:_session_needs_preflight`.
8. **`MCPTF_CONFIG_FILE` env var killed entirely** with a one-milestone deprecation warning. CLI mode (`mcp-contracts run --config PATH`) internally subprocesses `pytest -o "mcp_config_file=PATH"` — one route across CLI and library mode.
9. **`mcp-contracts run` rewiring** to use `pytest -o "mcp_config_file=PATH"` instead of setting the env var.

**Out of scope (deferred to later phases or v1.5):**

- `register()` API surface — **dropped entirely.** No `mcp_test_framework.contracts.register()` ships. `contracts/__init__.py` documents the ini-based route instead. (The Phase 26 stub stays; its docstring updates.)
- `RegistrationError`, frame validation, double-call detection (LIB-05 mechanics) — all moot with `register()` gone.
- Multi-config (list of paths) — v1.5.
- URL-style judge config (`judge="ollama://..."`) — moot; YAML uses today's nested `ollama.base_url`/`ollama.model`.
- `xdist`-parallel test execution — v1.5 (`_REGISTRATIONS` module-globals concern is also moot).
- Tool auto-discovery (operator omits `tools:`) — v1.5; v1.4 retains opt-in allowlist semantics from Phase 13 SAFE-01.
- Production PyPI publish — Phase 30.
- README rewrite leading with library mode — Phase 30.
- Codegen output path defaults (`tests/_generated/<server_slug>/`, refuse-to-write-under-site-packages) — Phase 28.
- `MCPTF_CONFIG_FILE` deprecation-shim removal — v1.5 cleanup phase.

</domain>

<decisions>
## Implementation Decisions

### Approach pivot — pytest-native ini config (replaces `register()`)

- **D-01:** The "three lines in `conftest.py`" `register()` API specified by LIB-01..08 is **dropped**. The library-mode entry point becomes a single `mcp_config_file` ini value in `[tool.pytest.ini_options]` (or `pytest.ini`, `tox.ini`, `setup.cfg` — any pytest config surface accepting `addini` values). Driver: operator-as-visionary call that the simpler indirection ("just point at the YAML") fits the vibe-coded operator persona better than a Python registration API. Memory traceability: `project_vibe_coded_persona`, `project_dotenv_silently_beats_config` (anti-env-var-magic bias), `feedback_option_presentation_with_context`. The phase title and REQUIREMENTS.md LIB-01..08 + CFG-01..02 need amending to match — handled by `<downstream_impact>` planning task, NOT Phase 27 implementation scope.

### Ini key name

- **D-02:** Ini key is `mcp_config_file` (lowercase + underscores per pytest convention). Registered via `parser.addini("mcp_config_file", type="string", help="Path to MCP test framework YAML config; absent = library mode opted out.")`. Path is resolved relative to `pyproject.toml`'s directory (pytest's standard `inipath`-relative semantics).

### Config file format

- **D-03:** `config.yaml` schema is **today's v1.3 schema, unchanged.** `mcp_server.{command,args,timeout_seconds}`, `ollama.{base_url,model,timeout_seconds}`, `tools: dict[str, ToolOptions]` (skip / call_arguments / judges / skip_reason), `test_code.generated_root`. Loaded via existing `pydantic-settings` machinery; library mode hands the file path to the existing loader and trusts its output. No new schema; no migration burden on operators.

### Contract-test body extraction — Move + dogfood

- **D-04:** Test bodies physically move from `tests/contract/test_mcp_tool_contract.py` → `src/mcp_test_framework/contracts/_tests.py`. The 10 test bodies are extracted verbatim (TEST-01..TEST-10); v1.3 assertion semantics unchanged.
- **D-05:** `tests/contract/test_mcp_tool_contract.py` is **deleted**. `tests/conftest.py:pytest_generate_tests` is **deleted** (the plugin's `pytest_collect_file` is now the sole parametrization path).
- **D-06:** Framework's own `pyproject.toml` `[tool.pytest.ini_options]` sets `mcp_config_file = "./config.test.yaml"` (or whatever the existing test config file is named — planner verifies). Framework's CI now runs contract tests *exclusively* through the library-mode injection path. This is the strongest possible regression test: every framework CI run is a live operator simulation.
- **D-07:** Phase 30 CLOSE-01 ("Framework's own `tests/contract/conftest.py` calls `register(config=Config())`") is **pre-empted** by D-04..D-06 — Phase 30's dogfood goal is already achieved here. Phase 30 CLOSE-01 needs amending to "framework's pyproject already uses `mcp_config_file`, verify still green at v1.4 close."

### Nodeid shape

- **D-08:** Injected contract tests render in pytest output as `<mcp-contracts>::test_<name>[<tool>]` — synthetic literal, not a real file path. Implemented by overriding `nodeid` on the synthesized Module returned from `pytest_collect_file`. Rationale: clean output, immediately distinguishes framework-injected tests from operator-authored ones at a glance, avoids the noisy `.venv/lib/python3.14/site-packages/...` prefix that would otherwise show on installed wheels. Operators who want to read source: `python -c "import mcp_test_framework.contracts._tests; print(_tests.__file__)"`.

### `MCPTF_CONFIG_FILE` env var fate

- **D-09:** Env var **killed entirely.** Phase 27 emits a one-time per-process `DeprecationWarning` when `MCPTF_CONFIG_FILE` is set in the environment (regardless of mode), pointing operators at `[tool.pytest.ini_options] mcp_config_file = ...`. Removal in v1.5 alongside every other Phase 25 + Phase 26 deprecation shim.
- **D-10:** Library mode **ignores** `MCPTF_CONFIG_FILE` entirely (does not read it). The deprecation warning fires from a single check at plugin `pytest_configure` time.
- **D-11:** CLI mode (`mcp-contracts run --config PATH`) rewires from `os.environ["MCPTF_CONFIG_FILE"] = PATH` to subprocessing `pytest -o "mcp_config_file=PATH"`. pytest's `-o key=value` flag overrides ini values at runtime — same mechanism as library mode, just driven by Typer instead of the operator's `pyproject.toml`. One config route across the whole framework.
- **D-12:** Today's `Config()` loader machinery (pydantic-settings env-driven path resolution) is rewired or wrapped: in library/CLI mode the path comes from the ini value (or `-o` override), not the env var. Planner picks: rewrite the loader to accept an explicit path argument, OR keep the env-driven loader and have the plugin set the env var internally just before construction (less clean; defer to research).

### Failure modes (fail-loud-or-silent matrix)

- **D-13:** `mcp_config_file` ini value **unset** → silent no-op. Plugin registers hooks but contract tests are not injected; operator's other tests run as normal. This is the "opted out / not yet onboarded" state. No warning (would be noisy for operators who installed `mcp-contracts` solely to use `gen-test-classes`).
- **D-14:** `mcp_config_file` set, **path does not exist** → fail loud at session start. `pytest.exit(f"mcp_config_file points at {path!r} which does not exist", returncode=2)`. Operator-tone error per `docs/ERROR-STYLE.md`; same returncode=2 convention as the existing preflight (distinguishes setup error from pass/fail).
- **D-15:** `mcp_config_file` set, file exists, **YAML malformed or schema validation fails** → fail loud at session start. Operator-tone error naming the file path, the field that failed, and a pointer at `config.example.yaml` / `mcp-contracts config-init` if the existing scaffolder is still alive (planner verifies).
- **D-16:** `mcp_config_file` set, YAML valid, **`tools:` dict empty** → silent no contract tests injected. Matches Phase 13 SAFE-01 opt-in semantics (unlisted tools are excluded; empty list = nothing selected). No warning — explicit empty is a legitimate state (operator scaffolding before adding tools).
- **D-17:** Operator's `tests/conftest.py` requires **zero ceremony.** No `pytest_plugins=[...]` line (Phase 26 entry-point handles auto-load). No `register()` call (gone). No imports from `mcp_test_framework`. The operator's `conftest.py` is whatever it already was; the plugin's behavior is entirely driven by the pyproject ini value.

### Black-box guard relocation (LIB-08)

- **D-18:** The `sys.modules` `homelab_mcp` runtime guard moves from `tests/conftest.py:pytest_configure` → new file `src/mcp_test_framework/_black_box_guard.py` (single function `check_black_box() -> None` raising `RuntimeError` on leak). Invoked from the plugin's `pytest_configure` (not from `register()`, since register is gone). The wheel-introspection AST-walk CI test (PACK-04 territory, Phase 26 D-04 / Plan 26-04) extends to fail on banned SUT imports anywhere inside `src/`.

### `_preflight` predicate (LIB-07)

- **D-19:** `_session_needs_preflight()` in `fixtures.py` flips from path-prefix detection (`tests/contract/`, `tests/test_code/`, `tests/sdet/`) to marker-based detection: returns `True` iff `mcp_config_file` ini value is set AND any collected item carries `pytest.mark.mcp_contract`. The marker is auto-applied to every injected contract test (D-08), so the predicate is equivalent for the contract path. Test-code-author tests (`tests/test_code/`) do NOT carry the marker — they use the SDET surface and don't need the framework's preflight to fire. Planner verifies the test-code-author path's preflight expectations and adjusts the marker logic if test-code tests also need preflight (likely they do — see deferred).

### Claude's Discretion

- **Plugin hook choice — `pytest_collect_file` vs `pytest_collection_modifyitems`:** the synthesized virtual module approach historically uses `pytest_collect_file` (returns a pytest `Module` for a fictional path). `pytest_collection_modifyitems` runs later and can add items but the items still need to come from somewhere. Planner picks the approach that yields the synthetic `<mcp-contracts>` nodeid cleanly. Suggested: `pytest_collect_file` with a fake `Path("<mcp-contracts>")` argument and a custom `Module` subclass overriding `nodeid`.
- **`Config()` loader rewiring:** D-12 leaves the choice between (a) refactoring the pydantic-settings loader to accept an explicit path argument vs (b) having the plugin set `os.environ["MCPTF_CONFIG_FILE"]` internally just before constructing `Config()` (uses the existing env-driven loader; ugly but minimal-change). Planner picks based on research findings — option (a) is cleaner long-term; option (b) is the smallest diff but reintroduces the env-var-magic the user just killed (likely a no-go on principle).
- **`_session_needs_preflight()` marker-detection mechanics:** can be a path-prefix check on `item.nodeid.startswith("<mcp-contracts>::")` (relies on D-08 nodeid stability) OR an iteration through `item.iter_markers("mcp_contract")` (relies on D-08 marker stability). Planner picks; both are defensible. Suggested: marker iteration is more semantically honest.
- **Deprecation copy for `MCPTF_CONFIG_FILE`:** mirror Phase 25 D-05 + Phase 26 D-07 pattern. Literal copy template: `"MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be removed in v1.5 — use `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml or pass `--config PATH` to mcp-contracts run instead."` Hardcoded per call site (single site: plugin `pytest_configure`).
- **Codegen `gen-test-classes` CLI integration:** today's command reads `MCPTF_CONFIG_FILE`. Phase 27 rewires it to read from the same ini route (or accept `--config PATH` explicitly). Phase 28 owns codegen-output-path policy (CODEGEN-LIB-01/02); Phase 27 only handles the input-config path. Planner decides whether to do the `gen-test-classes` rewire in Phase 27 (consistent kill of env var) or punt to Phase 28.

</decisions>

<downstream_impact>
## Downstream Impact (not Phase 27 implementation scope, but planner must surface as separate work)

The pivot in D-01 invalidates significant chunks of REQUIREMENTS.md and ROADMAP.md. These need amending — either inside Phase 27 plans (as a documentation plan) or as a separate decimal/quick task before Phase 28 starts.

### REQUIREMENTS.md amendments

- **LIB-01..08** — rewrite around the ini-driven route. LIB-01 ("three lines in `conftest.py`") → "one line in `[tool.pytest.ini_options]`". LIB-02 nodeid shape preserves but with `<mcp-contracts>` prefix per D-08. LIB-03 test-extraction language preserved (move-and-dogfood per D-04..D-07). LIB-04 marker semantics preserved. **LIB-05** (RegistrationError, frame validation, double-call) → **removed entirely**, no register() to validate. LIB-06 fixture prefixes already landed in Phase 26. LIB-07 `_preflight` predicate flip preserved per D-19. LIB-08 black-box-guard relocation preserved per D-18.
- **CFG-01** — "library mode IGNORES `MCPTF_CONFIG_FILE`" generalizes to "framework KILLS `MCPTF_CONFIG_FILE` in v1.4 with one-milestone deprecation, removes in v1.5." Precedence ladder becomes: `pytest -o "mcp_config_file=..."` > `[tool.pytest.ini_options]` > defaults. (No env var, no register() kwargs.)
- **CFG-02** — `register(config_file=PATH)` escape hatch → **removed entirely**. The ini value IS the explicit escape hatch. Move to deferred / v1.5 if a real escape-hatch use case emerges.

### ROADMAP.md amendments

- **Milestone goal text** — "three lines in `conftest.py` — Playwright-for-MCPs" rephrases to "one line in `pyproject.toml` — pytest-native MCP contract testing" (or similar; user-as-visionary picks the new pitch).
- **Phase 27 title** — currently `register() API + contracts sub-package + test extraction (LIB)`. New title candidates: `pytest-native ini config + contracts test injection + dogfood (LIB)`, or shorter. Planner proposes; user approves.
- **Phase 27 Success Criteria** — SC1 "writes `register(...)` in `tests/conftest.py`" → "sets `[tool.pytest.ini_options] mcp_config_file = PATH` in `pyproject.toml`". SC2 nodeid shape unchanged. SC3 marker selection unchanged. SC4 (double-call / frame-validation) **removed**. SC5 wheel-introspection AST-walk preserved.
- **Phase 28 scope shrinks significantly** — CFG-01/CFG-02 collapse (env var already killed; no register() to design). Phase 28 retains CODEGEN-LIB-01/02 (codegen output path policy) + final `MCPTF_CONFIG_FILE`-deprecation-removal cleanup (if v1.4 still has the warning shim — actually that goes to v1.5).
- **Phase 30 CLOSE-01** — "Framework's own `tests/contract/conftest.py` calls `register()`" → "Framework's pyproject already uses `mcp_config_file = ...`; verify still green at v1.4 close." Dogfood is done in Phase 27, not 30.

### Future-deferred items to revise

- "URL-style judge kwarg sugar" — moot (no kwargs).
- "`register()` accepting `tools=None` for auto-discovery" → "config.yaml accepting `tools:` omitted (or empty `{}`) for auto-discovery" — still v1.5 deferred.
- "`scoped_register()` context manager" → moot (no register).
- Removal of deprecation aliases — `MCPTF_CONFIG_FILE` joins the v1.5 cleanup list.

</downstream_impact>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & roadmap

- `.planning/PROJECT.md` — Vibe-coded operator persona (key driver of D-01 pivot), v1.4 milestone goals (NOTE: goal text references "three lines in conftest.py — Playwright-for-MCPs" which is now stale per D-01; planner must amend during planning).
- `.planning/ROADMAP.md` §"v1.4 Library Mode Delivery" Phase 27 line + SC1..5 — NOTE: title, SC1, SC4 stale per D-01 + D-08 + downstream_impact section above; amend during planning.
- `.planning/REQUIREMENTS.md` LIB-01..08, CFG-01..02 — NOTE: text stale per D-01 + downstream_impact; amend during planning. LIB-05 removes entirely.
- `.planning/STATE.md` — Phase position, milestone counters.

### Phase 26 carry-forward (the substrate Phase 27 fills)

- `.planning/phases/26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s/26-CONTEXT.md` — Plugin entry-point + fixture rename + contracts subpackage stub. Phase 27 fills `pytest_configure` and `pytest_collect_file` bodies in the Phase 26 `_plugin.py` skeleton.
- `src/mcp_test_framework/_plugin.py` — current skeleton: hooks declared with no-op bodies, `mcp_contract` marker registered in `pytest_configure`, `--mcp-*` option group reserved in `pytest_addoption`. Phase 27 extends these in place.
- `src/mcp_test_framework/contracts/__init__.py` — current docstring states `register()` lands in a "future library-mode milestone"; rewrite during Phase 27 to document the ini-route instead.
- `src/mcp_test_framework/contracts/py.typed` — PEP 561 marker; already shipping per Phase 26 D-13.
- `.planning/phases/26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s/26-04-PLAN.md` — wheel-introspection regression gate (PACK-04). Phase 27 extends it for the black-box AST-walk per D-18.

### Phase 25 carry-forward (deprecation pattern)

- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-CONTEXT.md` §"Deprecation mechanics" — stdlib `DeprecationWarning`, `stacklevel=2`, once-per-process via default Python warning filter, hardcoded "v1.5" removal copy. Phase 27 inherits verbatim for the `MCPTF_CONFIG_FILE` shim per D-09.
- `pyproject.toml` `[tool.pytest.ini_options] filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` — Phase 25 D-03; Phase 27's new env-var-deprecation warning is caught by the same filter.

### Phase 13 carry-forward (opt-in tool semantics)

- `.planning/phases/13-config-safety-and-opt-in-tool-selection/` — SAFE-01 opt-in allowlist semantics. Phase 27 preserves these verbatim: unlisted tools are excluded at parametrize time, never via `pytest.skip()` at runtime (the v1.1.1 hotfix invariant). The plugin's `pytest_collect_file` parametrizes over `config.tools.keys()` (those with `skip=False`).

### Seeds & vision

- `.planning/seeds/SEED-015-library-mode-delivery.md` — NOTE: the "three lines in conftest.py" framing is now stale per D-01. Read for the underlying motivation (Playwright-for-MCPs vibe, CLI demotion, fixture-surface preview) but treat the API-shape proposal as superseded.
- `.planning/seeds/SEED-022-framework-primitives-sdet-safety-principle.md` — Framework-primitives principle (memory `project_framework_primitives_sdet_safety_principle`). Phase 27's plugin must not introduce SUT-aware logic; `_tests.py` is generic across MCP servers.
- `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md` — Background on Phase 25's rename; API surface freeze rationale applies to Phase 27's ini key (`mcp_config_file` is now part of the public surface frozen before v1.5).

### Codebase landmarks (Phase 27 will touch)

- `src/mcp_test_framework/_plugin.py` (Phase 26 skeleton) — Phase 27 fills `pytest_configure` (read ini, load YAML, invoke black-box guard), `pytest_collect_file` (synthesize virtual module), preserves `pytest_addoption` (extend `--mcp-*` group later in Phase 29).
- `src/mcp_test_framework/contracts/__init__.py` — rewrite docstring; export nothing public (operators don't import from here in the ini route).
- `src/mcp_test_framework/contracts/_tests.py` (NEW per D-04) — destination for the 10 contract-test bodies; verbatim copy from `tests/contract/test_mcp_tool_contract.py` with fixture parameters preserved (`mcp_target_tool`, `mcp_judge`, `mcp_client`, `mcp_rubric_*`, `tool_config`).
- `src/mcp_test_framework/_black_box_guard.py` (NEW per D-18) — destination for the `sys.modules` `homelab_mcp` check moved from `tests/conftest.py`.
- `src/mcp_test_framework/fixtures.py:_session_needs_preflight` — predicate flip per D-19 (path-prefix → marker-based).
- `src/mcp_test_framework/cli.py` — CLI mode's `run` command rewires from `os.environ["MCPTF_CONFIG_FILE"] = PATH` → subprocess `pytest -o "mcp_config_file=PATH"` per D-11. Planner verifies the exact site in `_runner.py` or `cli.py`.
- `src/mcp_test_framework/config.py` — `Config()` loader; D-12 punts the choice between refactoring it to accept an explicit path argument vs the env-var-internal-set workaround.
- `tests/contract/test_mcp_tool_contract.py` — DELETED per D-05.
- `tests/conftest.py` — `pytest_plugins` line, `pytest_configure` black-box guard, and `pytest_generate_tests` all DELETED per D-05 + D-18. File becomes a docstring-only no-op (or is deleted if pytest tolerates it).
- `pyproject.toml` `[tool.pytest.ini_options]` — Phase 27 adds `mcp_config_file = "./<framework's existing test config>"` per D-06. Planner verifies the existing test config path (`config.test.yaml` likely; verify against tree).

### Python/pytest references (researcher should fetch)

- pytest `parser.addini` docs — type values, default behavior, `inipath`-relative path resolution. https://docs.pytest.org/en/stable/reference/reference.html#pytest.Parser.addini
- pytest `pytest_collect_file` hook docs — synthesizing virtual modules, `Module` subclass conventions, `nodeid` override. https://docs.pytest.org/en/stable/how-to/writing_plugins.html
- pytest `-o key=value` flag docs — runtime ini overrides; the mechanism CLI mode uses internally per D-11.
- pydantic-settings — the existing `Config()` loader; researcher verifies whether `model_validate` accepts an explicit path argument cleanly or whether the env-driven loader pattern requires the env-var workaround.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Phase 26 `_plugin.py` skeleton** — `pytest_configure`, `pytest_collection_modifyitems`, `pytest_addoption` declared with no-op bodies + `mcp_contract` marker registered + `--mcp-*` option group reserved. Phase 27 fills the bodies in place; no new file creation needed for the plugin entry point.
- **Phase 26 `contracts/` subpackage stub** — `__init__.py` + `py.typed` already ship. Phase 27 adds `_tests.py` (extracted test bodies) and rewrites `__init__.py`'s docstring.
- **Phase 26 fixture-rename surface** — `mcp_config`, `mcp_judge`, `mcp_client`, `mcp_target_tool`, three `mcp_rubric_*` fixtures, plus `_preflight`, `_isolated_home`, `tool_config` — all referenced by the extracted test bodies. Phase 27's `_tests.py` uses the prefixed names directly (no deprecated aliases inside framework's own test code).
- **Existing `pydantic-settings` `Config()` loader** in `src/mcp_test_framework/config.py` — loads YAML via `YamlConfigSettingsSource`, reads env vars, applies field defaults. Phase 27 needs to drive it with an explicit path argument (D-12).
- **Phase 13 SAFE-01 opt-in allowlist semantics** in `tests/conftest.py:_resolve_tool_names` — Phase 27's `pytest_collect_file` adopts identical semantics: parametrize over `config.tools` entries with `skip=False`; unlisted tools and skip=True tools are excluded at injection time (never via runtime `pytest.skip()`).
- **`_runner.py` `_DISCOVERED_TOOL_NAMES` cache** — currently lives in production code (Phase 14 Plan 05 relocation). Phase 27's `pytest_collect_file` does its own discovery (brief MCP handshake to `list_tools`) and replaces the cache mechanism, OR keeps the cache for CLI-mode wrapper compat. Planner decides; suggested: keep `_runner.py` cache for CLI wrapper-side header counts, and have the plugin re-discover (one short subprocess) — the two paths are short-lived and rarely in the same process.
- **Operator-tone error helper** in `cli.py` (`_emit_operator_error`) + `fixtures.py` (`_pytest_exit_operator_tone`) — Phase 27 reuses `_pytest_exit_operator_tone` for D-14, D-15 fail-loud paths. `docs/ERROR-STYLE.md` is the style anchor.
- **Existing `tests/contract/test_mcp_tool_contract.py`** — 10 test bodies, fully parametrized via `tests/conftest.py:pytest_generate_tests`. Phase 27's `_tests.py` is a verbatim move; v1.3 assertion semantics + fixture dependencies (`mcp_target_tool`, `mcp_judge`, `mcp_client`, `mcp_rubric_*`, `tool_config`) preserved.

### Established Patterns

- **Phase 25 deprecation pattern** — stdlib `DeprecationWarning`, `stacklevel=2`, once-per-process via default warning filter, hardcoded "v1.5" removal copy. Phase 27's `MCPTF_CONFIG_FILE` shim follows this verbatim (D-09).
- **Fixture-prefix convention** — Phase 26 D-15..D-19 established `mcp_*` prefix for public framework fixtures with unprefixed deprecation aliases. Phase 27's extracted test bodies use the prefixed names exclusively.
- **Banned-imports + `sys.modules` guard** — Phase 27 relocates the runtime half into `_black_box_guard.py` (D-18); the ruff TID251 static half stays in `pyproject.toml`. Wheel-introspection AST-walk extends to fail on banned imports inside `src/` (Phase 26 PACK-04 + Phase 27 D-18).
- **Strict pytest-asyncio mode** + `asyncio_default_fixture_loop_scope = "session"` + `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` on contract tests — preserved verbatim in `_tests.py`.
- **opt-in allowlist semantics (Phase 13 SAFE-01)** — Phase 27's plugin parametrize logic matches `_resolve_tool_names` semantics exactly.

### Integration Points

- **Plugin `pytest_configure` ↔ Phase 26 marker registration** — Phase 26 already registers `mcp_contract`; Phase 27 extends the same body to read ini, load Config, invoke black-box guard. Two passes through `pytest_configure` (one from `tests/conftest.py` historically, one from the plugin) become one (plugin only) after D-18 + D-17.
- **Plugin `pytest_collect_file` ↔ pytest's standard `Module` collection** — Phase 27 returns a custom `Module` subclass from a synthetic path; pytest treats injected items as normal tests downstream (selection, markers, fixtures all work).
- **`mcp_config_file` ini value ↔ pyproject.toml** — pytest's `inipath`-relative resolution applies; the value is a string treated as a path. Operator runs `pytest` from anywhere in their project tree and the path resolves consistently.
- **CLI mode `mcp-contracts run --config PATH` ↔ pytest `-o "mcp_config_file=PATH"`** — Phase 27 D-11 rewires the subprocess call. The `-o` flag overrides ini values at runtime, so CLI mode injects config the same way library mode does.
- **`_session_needs_preflight()` ↔ `mcp_contract` marker** — D-19 flips the predicate from path-prefix to marker-based, naturally aligning with the injection mechanism.

</code_context>

<specifics>
## Specific Ideas

- **The conversational pivot driver** — user reframed the choice as "I never saw the need for CLI args in the first place" (extending to: "I never saw the need for this register() API either — can we just point at a YAML?"). This is the visionary-as-founder call that the whole library-mode delivery has been hunting for: simpler indirection over more clever Python.
- **One-mechanism principle** — D-09 + D-11 + D-12 converge on a single config-resolution route across CLI mode and library mode. The user has been bitten three times by precedence ambiguity (memories: `project_dotenv_silently_beats_config`, `project_mcptf_config_file_silent_fail`, `feedback_option_presentation_with_context`); Phase 27 closes the door on precedence-confusion by removing the second mechanism.
- **Move-and-dogfood (D-04..D-07) is a strong v1.4 close-state proof** — by the end of Phase 27, the framework's CI exercises every code path an operator hits in library mode. Phase 30 dogfood deliverable is already done.
- **Synthetic nodeid `<mcp-contracts>::...` is brand-aligned** — matches the dist name (`mcp-contracts` per Phase 26 D-01) and signals "framework-injected" at a glance. Future plugins or CI dashboards can grep on this stable prefix.

</specifics>

<deferred>
## Deferred Ideas

### Phase 28 (already roadmapped; scope shrinks per downstream_impact)
- Codegen output path defaults (`tests/_generated/<server_slug>/`, refuse-to-write-under-site-packages) per CODEGEN-LIB-01/02.
- `gen-test-classes` CLI input-config rewire — Phase 27 may already pull this in (Claude's discretion); if punted, Phase 28 owns it.

### Phase 29 (already roadmapped, unchanged)
- `--mcp-domain-ui` reporter plugin driven by `pytest_runtest_logreport`; xdist master-only; CI/no-TTY auto-OFF.

### Phase 30 (already roadmapped; CLOSE-01 dogfood pre-empted per D-07)
- Production PyPI publish.
- README rewrite leading with library mode ("Add `mcp-contracts` to pyproject; set `mcp_config_file`; run pytest").
- CLI demotion to appendix.
- Carry-forward live UATs (README PASS-sample re-capture, Phase 17 SC1 at ~70 tools, Phase 13 + 14 live-stack UATs).
- CLOSE-01 amended per D-07.

### v1.5 cleanup (deferred from Phase 27)
- `MCPTF_CONFIG_FILE` env var removal (deprecation lands in Phase 27 D-09; removal joins the v1.5 cleanup phase with every other Phase 25 + Phase 26 + Phase 27 deprecation shim).
- Tool auto-discovery (`tools:` omitted → discover all) — already in REQUIREMENTS.md future-deferred list, language updates per downstream_impact.
- Multi-config (list of paths) for multi-server monorepos.

### Possibly deferred from Phase 27 (planner's call)
- `gen-test-classes` CLI input-config rewire (Phase 27 vs Phase 28).
- `_runner.py:_DISCOVERED_TOOL_NAMES` cache survival — keep for CLI wrapper-side header counts vs delete with the rest of the env-driven plumbing.
- Test-code-author preflight predicate adjustment — D-19's marker-based flip handles the contract path; if `tests/test_code/` tests also need preflight (likely yes), the predicate needs to additionally allow them through. Planner verifies.

### Documentation amendments (post-Phase-27, pre-Phase-28)
- REQUIREMENTS.md LIB-01..08 + CFG-01..02 rewrites per `<downstream_impact>`.
- ROADMAP.md milestone goal + Phase 27 title + Success Criteria + Phase 28 + Phase 30 amendments per `<downstream_impact>`.
- These can ship as a Phase 27 plan (a final docs-sweep plan) OR as a quick task before Phase 28 — planner picks.

</deferred>

---

*Phase: 27-register-api-contracts-sub-package-test-extraction-lib (title pre-pivot; new title TBD during planning)*
*Context gathered: 2026-05-16*
