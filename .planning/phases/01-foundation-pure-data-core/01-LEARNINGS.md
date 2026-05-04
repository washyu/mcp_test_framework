---
phase: 01
phase_name: "foundation-pure-data-core"
project: "mcp_test_framework"
generated: "2026-05-04"
counts:
  decisions: 11
  lessons: 6
  patterns: 10
  surprises: 7
missing_artifacts: []
---

# Phase 1 Learnings: foundation-pure-data-core

## Decisions

### PEP 735 `[dependency-groups].dev` for dev tooling
Dev tooling (pytest, pytest-asyncio, ruff) lives under PEP 735 `[dependency-groups].dev` — NOT under the legacy `[tool.uv].dev-dependencies` and NOT under `[project.optional-dependencies].dev`. Runtime deps stay in `[project.dependencies]`.

**Rationale:** PEP 735 is the modern uv-managed shape for dev-only dependencies; it keeps runtime install lean and avoids legacy uv-specific tables that may be removed.
**Source:** 01-01-SUMMARY.md

---

### Explicit Hatch wheel target for project/package name divergence
Added `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` to pyproject.toml. Hatchling cannot auto-detect the package because project name (`mvp-test-framework`) ≠ package name (`mcp_test_framework`) — `mvp` vs `mcp` is not the standard hyphen-to-underscore transform Hatchling looks for.

**Rationale:** Without it, `uv sync` fails at the editable-install build step. Phase 5 will need to remember this when wiring the `[project.scripts]` entry point.
**Source:** 01-01-SUMMARY.md, 01-VERIFICATION.md

---

### Custom `_BareNameNestedEnvSource` ships in v1.0
A custom `PydanticBaseSettingsSource` (~30 LOC) walks each sub-model's `validation_alias` choices against `os.environ` and emits a nested dict for the parent settings to consume. Inserted at position 1 in `settings_customise_sources` (after `init_settings`, before `env_settings`).

**Rationale:** CONTEXT.md locked precedence as `CLI > env > .env > YAML > defaults` AND forbade `env_nested_delimiter`. The stock `EnvSettingsSource` doesn't walk sub-model aliases, so bare env names like `OLLAMA_BASE_URL` had no path to `cfg.ollama.base_url` without this source.
**Source:** 01-02-SUMMARY.md

---

### `AliasChoices(<env name>, <field name>)` + `populate_by_name=True` on every sub-model
Every env-mapped field gets a two-element `AliasChoices` and every sub-model carries `populate_by_name=True` in its `ConfigDict`.

**Rationale:** Single-arg `AliasChoices("OLLAMA_BASE_URL")` makes the field accept ONLY the env-name key; YAML overlays emit field-name keys (`{"ollama": {"base_url": "..."}}`) and silently fall back to defaults. Adding the field-name as a second alias choice + `populate_by_name=True` makes both routing paths work without weakening env-name priority.
**Source:** 01-02-SUMMARY.md

---

### Per-sub-model `ConfigDict(frozen=True)` (Assumption A5)
Frozen marker is applied to each of `OllamaConfig`, `McpServerConfig`, `TargetConfig` independently — not just to the top-level `Config(BaseSettings)`.

**Rationale:** Frozen does NOT propagate from parent `BaseSettings` to nested `BaseModel`. Without per-sub-model frozen, `cfg.ollama.model = "X"` silently succeeds — caught by `test_sub_model_is_frozen`.
**Source:** 01-02-SUMMARY.md

---

### `ValidationIssue.severity` is required, no default
`severity: Literal["error"]` is declared with NO default value — every call site must construct `severity="error"` explicitly.

**Rationale:** CONTEXT.md decision D-02 — adding a `"warning"` tier post-MVP should be a typed schema migration touching every call site, not a silent default flip. A `Literal["error"] = "error"` default would mask uncovered call sites.
**Source:** 01-03-SUMMARY.md

---

### Inline f-string paths over `_pointer_from_deque` helper
The 7 schema checks build their JSON-Pointer paths as inline f-strings (e.g., `f"/inputSchema/properties/{prop_name}/description"`). The `_pointer_from_deque` helper is retained but unused.

**Rationale:** Hand-coded checks always know their literal path components — none contain `~` or `/`, so RFC 6901 escaping isn't needed in practice. The helper is reserved for future `iter_errors`-driven checks (e.g., Phase 4 response-schema validation) where path components could be arbitrary.
**Source:** 01-03-SUMMARY.md

---

### `validator_for(schema, default=Draft202012Validator)` — fallback, not hardcoded
JSON Schema draft is auto-detected via `validator_for`; `Draft202012Validator` is the fallback default only.

**Rationale:** MVP target schemas declare their `$schema`; falling back to Draft 2020-12 only matters when the schema omits a draft URI. Hardcoding would silently misvalidate schemas that declare older drafts.
**Source:** 01-03-SUMMARY.md, 01-VERIFICATION.md

---

### `Tool.model_construct(...)` for defensive-branch coverage
Tests that need to inject `inputSchema=None` (to exercise the validator's "not a dict" branch) use `mcp.types.Tool.model_construct(...)` to bypass pydantic validation.

**Rationale:** `mcp.types.Tool`'s pydantic validator rejects `None` for `inputSchema`, so direct construction raises `ValidationError`. `model_construct` is pydantic's blessed escape hatch for this exact case — preferable to `# type: ignore + cast`.
**Source:** 01-03-SUMMARY.md

---

### Black-box enforcement is belt + suspenders
SETUP-03 ships in TWO layers: (1) ruff TID251 banned-api at the lint layer (declared in 01-01) and (2) `tests/conftest.py` `pytest_configure` `sys.modules` scan at runtime (shipped in 01-04).

**Rationale:** The runtime belt catches dynamic imports (`importlib.import_module("homelab_mcp")`) that static analysis cannot cover regardless of ruff version, and survives ruff version drift if TID251 behavior changes. The lint layer fails fast in CI.
**Source:** 01-04-SUMMARY.md

---

### Smoke-test fixtures live at `tests/_fixtures/<name>.py.txt`
Deliberately-malformed lintable fixtures use the `.py.txt` extension and live under `tests/_fixtures/` (NOT `tests/unit/_fixtures/`).

**Rationale:** The `.py.txt` extension hides the file from repo-wide `ruff check src tests` (ruff only matches `*.py`) while still being copyable to a `.py` path under pytest `tmp_path` for explicit invocation. The cross-cutting `tests/_fixtures/` location supports reuse by Phase 4 integration tests, not just unit tests.
**Source:** 01-04-SUMMARY.md

---

## Lessons

### `EnvSettingsSource` does not walk sub-model `validation_alias`
Pydantic-settings' built-in env source only inspects fields declared on the top-level `BaseSettings` class. Bare env names like `OLLAMA_BASE_URL` annotated on a nested `BaseModel` field never get picked up — the model silently falls back to the default with no error signal.

**Context:** Discovered in plan 01-02 Task 2 when 4/9 config tests failed even after the `AliasChoices` fix. Required shipping the custom `_BareNameNestedEnvSource` (~30 LOC). The failure mode is invisible without tests because there's no exception — just a silent default-fallback.
**Source:** 01-02-SUMMARY.md

---

### Single-arg `AliasChoices` breaks YAML overlay routing
A field declared with `validation_alias=AliasChoices("OLLAMA_BASE_URL")` accepts ONLY the alias name as an input key. `YamlConfigSettingsSource` and the standard nested-dict source emit field-name keys (`{"ollama": {"base_url": "..."}}`) — with only the alias as an accepted key, YAML and init-kwarg pathways stop populating the field.

**Context:** Caught in plan 01-02 only because the test suite covers all 5 precedence levels. Fix: add the field name as a second alias choice AND set `populate_by_name=True` on the sub-model. Without tests covering both env AND YAML for the same field, this would have shipped as a silent YAML regression.
**Source:** 01-02-SUMMARY.md

---

### `frozen=True` on parent `BaseSettings` does not propagate to nested `BaseModel`
Pydantic v2's frozen marker is per-class, not inherited through composition. A parent `BaseSettings(frozen=True)` does NOT make its `OllamaConfig` field's attributes immutable.

**Context:** Assumption A5 from CONTEXT.md was verified in plan 01-02. Removing `ConfigDict(frozen=True)` from any sub-model lets `cfg.ollama.model = "X"` silently succeed. Always test mutation guards explicitly per sub-model.
**Source:** 01-02-SUMMARY.md

---

### Pydantic blocks `inputSchema=None` on `mcp.types.Tool`
Direct construction `Tool(name="ok", description="ok", inputSchema=None)` raises `ValidationError`. The only way to test a validator's defensive "not a dict" branch is `Tool.model_construct(...)` which bypasses validation.

**Context:** Discovered in plan 01-03 when writing `test_check_3_invalid_input_schema_not_dict`. Pydantic v2's validation is strict at construction; defensive branches downstream are unreachable through normal construction.
**Source:** 01-03-SUMMARY.md

---

### Pytest 9 returns exit code 5 for "no tests collected"
`pytest --collect-only tests/` against a directory with no test files exits 5 (not 0) — by design. This is "discovery succeeded but found nothing," distinct from "discovery failed."

**Context:** Plan 01-01's acceptance criterion said "exits 0" but the verify-grep on output (`collected 0 items`) was the load-bearing check. The grep matched; the exit-0 phrasing was wrong vs pytest 9 behavior. Future plans should phrase as "exits 0 OR exits 5 with 'collected 0 items'" when they pre-stage empty test trees.
**Source:** 01-01-SUMMARY.md

---

### Ruff 0.15.12 catches the homelab_mcp submodule import case
Contrary to RESEARCH Pitfall 4 (citing ruff issue #1614), ruff 0.15.12 + this repo's `[tool.ruff.lint.flake8-tidy-imports.banned-api]` config DOES catch `from homelab_mcp.client import x` with TID251.

**Context:** Plan 01-04 was written assuming the submodule case was a documented gap — the third smoke test was designed as `xfail(strict=False)` for that path. In practice the test passed via the "ruff caught it" branch. The runtime sys.modules belt remains valuable as defense-in-depth against ruff version regressions and for catching dynamic imports.
**Source:** 01-04-SUMMARY.md, 01-VERIFICATION.md

---

## Patterns

### Custom PydanticBaseSettingsSource for bare-env-name routing
A ~30 LOC subclass of `PydanticBaseSettingsSource` that walks each sub-model's `model_fields`, reads each field's `validation_alias` choices, and emits a nested dict for the parent settings to merge. Inserted into the `settings_customise_sources` tuple at the right precedence position.

**When to use:** Any pydantic-settings BaseSettings where bare env names must route to nested sub-model fields and `env_nested_delimiter` is not acceptable (because of locked naming conventions or precedence requirements).
**Source:** 01-02-SUMMARY.md (`_BareNameNestedEnvSource`)

---

### `AliasChoices(<env>, <field>)` + `populate_by_name=True` for dual routing
Every sub-model field that participates in env routing AND structured-source overlays carries `validation_alias=AliasChoices(<env name>, <field name>)` and the sub-model's `ConfigDict` includes `populate_by_name=True`.

**When to use:** Any pydantic v2 sub-model that needs to accept both env-name keys (from a custom env source) and field-name keys (from YAML/init/JSON sources).
**Source:** 01-02-SUMMARY.md

---

### Per-sub-model frozen marker
Every nested `BaseModel` carries its own `ConfigDict(frozen=True)` independently of the parent `BaseSettings`.

**When to use:** Any pydantic v2 composite model where the WHOLE config tree must be immutable. Don't rely on frozen propagation; assert per sub-model with a dedicated test.
**Source:** 01-02-SUMMARY.md

---

### `tests/conftest.py` owns the session-level black-box guard
A single `pytest_configure(config)` hook in `tests/conftest.py` scans `sys.modules` at session start for forbidden modules and raises `RuntimeError` on leak. The hook is auto-registered by pytest (no explicit import needed).

**When to use:** Any project that imports a "subject under test" as a black-box subprocess and must catch accidental in-process imports — including dynamic `importlib.import_module(...)` paths that static analysis can't see.
**Source:** 01-04-SUMMARY.md

---

### `.py.txt` extension for deliberately-malformed lintable fixtures
Fixture files containing intentionally-invalid Python code live at `tests/_fixtures/<name>.py.txt`. The `.py.txt` extension hides them from repo-wide `ruff check src tests` while keeping them human-readable and copyable to real `.py` paths under pytest `tmp_path`.

**When to use:** Any test that needs to invoke a linter/static-analyzer against a fixture containing a deliberate violation, without breaking the project's repo-wide lint pass.
**Source:** 01-04-SUMMARY.md

---

### Pin linter config to repo root in smoke tests
Smoke tests that invoke ruff (or any external linter) pass `--config <repo_root>/pyproject.toml` explicitly so a developer's `~/.config/ruff/ruff.toml` cannot weaken the test signal.

**When to use:** Any subprocess-based linter test where config-file walk-up could pick a different config than the one under test. Without `--config`, the test signal is at the mercy of the developer's home directory.
**Source:** 01-04-SUMMARY.md

---

### Two-tool union strategy for cross-cutting invariants
When a validator short-circuits on certain failures (e.g., schema_validator's Check 3), a single "everything broken" tool can never trigger all checks. Cross-cutting invariant tests construct two tools — one exercising the non-short-circuit checks, one exercising the short-circuit case — and concatenate their issue lists before asserting the invariant.

**When to use:** Any validator with a fail-fast / short-circuit branch where invariants need to be asserted across the FULL output space, not just one branch.
**Source:** 01-03-SUMMARY.md

---

### Inline f-string paths vs RFC 6901 helper
For hand-coded checks where every path component is a known literal string (no `~` or `/` characters), build paths inline as f-strings. Reserve a `_pointer_from_deque` helper (with full RFC 6901 escaping) for future `iter_errors`-driven checks where path components are arbitrary user data.

**When to use:** When you control the path components at the call site (literal field names, fixed indices), prefer inline. When path components come from a library iterator or user input that may contain RFC 6901 reserved chars, use the helper.
**Source:** 01-03-SUMMARY.md

---

### Pytest-asyncio strict mode + session-scoped fixture loop, configured at the build layer
Configure `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "session"` ONCE in `[tool.pytest.ini_options]`. Tests opt into the session loop via `@pytest.mark.asyncio(loop_scope="session")`.

**When to use:** Any project with long-lived async fixtures (e.g., a session-scoped MCP subprocess). Strict mode forces explicit `@pytest.mark.asyncio` so the test author always thinks about scope.
**Source:** 01-01-SUMMARY.md (Pattern 3)

---

### Black-box defense in depth — lint + runtime
Static analysis (ruff TID251 banned-api) catches the easy cases at CI lint time; a runtime `sys.modules` scan catches dynamic imports and survives lint-rule regressions. Ship both — they have non-overlapping failure modes.

**When to use:** Any project with a "do not import X in process Y" rule where the rule is load-bearing for correctness (not just style). Static-only or runtime-only is insufficient.
**Source:** 01-04-SUMMARY.md, 01-VERIFICATION.md

---

## Surprises

### Hatchling's package auto-detect failed because `mvp` ≠ `mcp`
`uv sync` failed at the editable-install build step with a Hatchling error: it could not find a directory matching the project name (`mvp_test_framework`) because the package is intentionally named `mcp_test_framework`. The standard hyphen-to-underscore heuristic doesn't account for letter-substitution divergences.

**Impact:** Forced a Rule-3 (blocking) deviation in plan 01-01 — added explicit `[tool.hatch.build.targets.wheel] packages = [...]` block. Bundled into Task 2 commit. Plan-text gap (the plan said "keep [build-system] as-is" — but uv init produced no wheel-target block).
**Source:** 01-01-SUMMARY.md

---

### Custom env source needed (not anticipated in any plan)
Plan 01-02 assumed bare env names would route to sub-model fields via `validation_alias` annotations on the sub-model. They don't — `EnvSettingsSource` only inspects top-level fields. ~30 LOC of custom `PydanticBaseSettingsSource` were required to make the locked precedence work without `env_nested_delimiter`.

**Impact:** Bumped plan 01-02 task 2 to include both the test suite AND the custom env source as Rule-1 fixes. The custom source was committed alongside the test fixes in `5767178`. Plan-checker BLOCKER #1 originally specified a different fix (`Option A: AliasChoices alone`) — that fix turned out to be necessary but not sufficient.
**Source:** 01-02-SUMMARY.md

---

### 4/9 config tests failed initially due to silent default-fallback
After plan 01-02 task 1 shipped the implementation per spec (single-arg `AliasChoices` + no custom env source), the test suite revealed 4/9 failures — all silent default-fallbacks with no exception trace. The route from env var to sub-model field was broken in two places (alias shape + missing nested env source) and neither broke loudly.

**Impact:** Required two stacked Rule-1 bug fixes to pass the suite. Drove home the value of writing the test suite before declaring the implementation done — silent failures don't surface in smoke checks.
**Source:** 01-02-SUMMARY.md

---

### Ruff 0.15.12 already closes the submodule-import gap
RESEARCH Pitfall 4 cited ruff issue #1614 and built plan 01-04's third test as `pytest.xfail(strict=False)` for the documented gap. In execution, ruff caught `from homelab_mcp.client import x` with TID251 — the test passed via the "ruff caught it" branch, never exercised the xfail path.

**Impact:** RESEARCH note is partially obsolete. The runtime sys.modules belt remains load-bearing — both because ruff version drift could regress and because it catches dynamic imports static analysis can't see. Plan 01-04 documented this in a "Research-vs-Reality" note.
**Source:** 01-04-SUMMARY.md, 01-VERIFICATION.md

---

### Pytest 9 exit-code-5 vs plan acceptance criterion text
Plan 01-01's acceptance text said `pytest --collect-only tests/` "exits 0," but pytest 9 exits 5 for "no tests collected" by design. The verify-grep (`collected 0 items`) matched correctly, so the criterion was effectively met — but the literal exit-0 phrasing is wrong vs runtime behavior.

**Impact:** Required mid-plan judgment that the verify-grep was the load-bearing check. Recommendation propagated to subsequent plans: phrase as "exits 0 OR exits 5 with 'collected 0 items'" for empty-tree pre-staging.
**Source:** 01-01-SUMMARY.md

---

### Schema validator's Check 3 short-circuit forced a two-tool test architecture
Check 3 (inputSchema is a valid JSON Schema dict) short-circuits — if it fails, checks 4-7 cannot run because they require a usable schema dict. This means the cross-cutting invariant tests (severity always "error"; paths always JSON-Pointer) cannot use a single "everything broken" tool; they have to construct two tools and concatenate their issue lists.

**Impact:** Drove plan 01-03's test architecture: separate `_clean_tool()`, `_everything_broken_tool()`, and `_issues_covering_all_seven_checks()` helpers, plus a `_check_3b_only_tool()` to exercise the short-circuit independently. Pattern is documented for any future short-circuiting validator.
**Source:** 01-03-SUMMARY.md

---

### `mcp 1.27.0` and ruff `target-version = "py314"` both worked first try on Python 3.14
Two plan-01 open questions (Q1: does ruff accept `py314`? Q2: does mcp 1.27 install on Python 3.14.3?) were both expected to require fallbacks — `py313` for ruff, an upstream issue file for mcp. Neither fallback was needed. `uv sync` resolved 40 packages cleanly; ruff accepted `py314` with no warnings.

**Impact:** Removed two anticipated risks from the foundation phase. Plan 01-01 closed faster than budgeted (2 min 29 sec). Confidence boost for the rest of the stack — if mcp installs cleanly on 3.14, downstream Phase 2 stdio work doesn't need a separate compat investigation.
**Source:** 01-01-SUMMARY.md
