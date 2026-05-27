# Phase 34: Opt-in host isolation passthrough (999.3) — Research

**Researched:** 2026-05-26
**Domain:** Pydantic config schema extension + pytest plugin hook plumbing + spawn-site env construction
**Confidence:** HIGH on plumbing sites & Config home; HIGH on xdist hook ordering (verified via xdist source); HIGH on stash timing; MEDIUM on banner-surface reuse (Phase 31 D-08 surface present but the formatwarning override is bound to `warnings.warn` sites, not arbitrary `pytest_configure`-time stderr writes — see Finding 6).

## Phase Goal

Add a top-level `Config.host_isolation: Literal['strict','passthrough'] = 'strict'` knob. Under `passthrough`: pass `dict(os.environ)` verbatim to `StdioServerParameters(env=...)`, skip the `_isolated_home` tempdir allocation, and clamp pytest-xdist to one worker with an operator-tone banner. Audit every bare `Config()` call site in `src/` + `tests/`. Update README + `docs/LIBRARY-MODE.md`.

## Source of Truth

All locked decisions live in `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-CONTEXT.md` (D-01..D-08 + Claude's Discretion defaults). The rationale audit trail lives in `34-DISCUSSION-LOG.md`. This research document does NOT re-litigate any locked decision — it surfaces the operational details the planner needs to translate those decisions into a task plan.

**Naming nit (planner will hit this):** CONTEXT.md repeatedly references `cli.py:_emit_operator_error_for_validation_error`. The actual symbol in `src/mcp_test_framework/cli.py:243` is `_emit_operator_error_for_validation` (no trailing `_error`). `_plugin.py:228` imports the correct name. The planner should use the actual symbol name and not propagate the typo from CONTEXT.md.

## Research Findings

### Finding 1 — pytest-xdist hook ordering for ISOL-04 clamp (CRITICAL)

**Conclusion: `pytest_configure(tryfirst=True)` mutating `config.option.numprocesses = 1` is INSUFFICIENT alone.** The plugin must ALSO overwrite `config.option.tx` to `["popen"]` (or simply `[]`). The clamp lands in `pytest_configure(tryfirst=True)`.

**Evidence — pytest-xdist's own hook decorators** (verified at `https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/plugin.py`):

```python
@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config: pytest.Config) -> None:
    if config.option.distload:
        config.option.dist = "load"
    usepdb = config.getoption("usepdb", False)
    if config.option.numprocesses in ("auto", "logical"):
        if usepdb:
            config.option.numprocesses = 0
            config.option.dist = "no"
        else:
            auto_num_cpus = config.hook.pytest_xdist_auto_num_workers(config=config)
            config.option.numprocesses = auto_num_cpus
    if config.option.numprocesses:
        if config.option.dist == "no":
            config.option.dist = "load"
        numprocesses = config.option.numprocesses
        if config.option.maxprocesses:
            numprocesses = min(numprocesses, config.option.maxprocesses)
        config.option.tx = ["popen"] * numprocesses

@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    ...
    if _is_distribution_mode(config):
        from xdist.dsession import DSession
        session = DSession(config)
        config.pluginmanager.register(session, "dsession")
```

**Hook lifecycle** (pytest docs + `https://docs.pytest.org/en/stable/_modules/_pytest/hookspec.html`):
1. `pytest_cmdline_main(tryfirst=True)` — xdist resolves `auto`/`logical` → integer N, sets `tx=["popen"]*N`.
2. `pytest_configure(tryfirst=True)` — user plugins (including ours).
3. `pytest_configure` (default) — pytest core.
4. `pytest_configure(trylast=True)` — xdist registers DSession.
5. `pytest_sessionstart(trylast=True)` — xdist's DSession calls `NodeManager(...).setup_nodes(...)`.

**Worker spawn point** (verified at `xdist/dsession.py` + `xdist/workermanage.py`): `NodeManager.setup_nodes()` reads `config.option.tx`, not `config.option.numprocesses`. One worker spawns per entry in `tx`.

**Implication for ISOL-04:**

- In `_plugin.py:pytest_configure(tryfirst=True)`: after loading the stashed Config, if `cfg.host_isolation == 'passthrough'` AND `config.option.numprocesses` (truthy — operator passed `-n N`):
  1. Emit the operator-tone clamp banner via `warnings.warn` with the `_mcptf_formatwarning` override already in place (Finding 6).
  2. Set `config.option.numprocesses = 1`.
  3. Set `config.option.tx = ["popen"]` (single-entry list — matches what xdist's own `pytest_cmdline_main` would have produced for `-n 1`).
- Do NOT use `pytest_xdist_setupnodes` (not a real hook; the closest available hook is `pytest_xdist_auto_num_workers` which only fires for `-n auto` / `-n logical`, never for an explicit numeric value).
- Do NOT use `pytest_cmdline_main(tryfirst=True)` to clamp — that hook fires BEFORE `pytest_configure`, so the stashed Config is not yet populated. We don't know we're in passthrough mode at `pytest_cmdline_main` time without re-reading the YAML, which would duplicate Config-loading logic.

**Sanity check the planner should pin via a task:** add a unit test that constructs a fake `pytest.Config` with `option.numprocesses=4`, calls the plugin's `pytest_configure` with a passthrough-mode stashed config, then asserts `option.numprocesses == 1 AND option.tx == ["popen"]`. The test does NOT need a real xdist subprocess spawn — the regression guard is "both attributes mutated together," which is the load-bearing invariant.

**Sources:**
- Verified xdist plugin source: `https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/plugin.py`
- Verified worker-spawn site reads `tx`: `https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/workermanage.py`
- Hook lifecycle: `https://docs.pytest.org/en/stable/_modules/_pytest/hookspec.html`

### Finding 2 — `test_code/session.py:67` stash timing (ISOL-05 highest-risk site)

**Conclusion: the bare `Config()` at `test_code/session.py:67` runs AFTER the plugin's stash population. Routing through the stash is safe and is the correct remediation.**

**Evidence:**

- Plugin stash population: `src/mcp_test_framework/_plugin.py:247` — `config._mcp_contracts_config = cfg` inside `pytest_configure`. This hook fires once per session, before any test or fixture runs.
- `mcp_session` fixture signature: `src/mcp_test_framework/test_code/session.py:54`:
  ```python
  @pytest_asyncio.fixture(loop_scope="session", scope="session")
  async def mcp_session(mcp_client: McpTestClient):
  ```
  Session-scoped async fixture. Resolves during test execution, AFTER `pytest_configure` → `pytest_sessionstart` → `pytest_collection` → first test setup. By the time line 67 runs, `request.session.config._mcp_contracts_config` is fully populated (or explicitly absent for non-library-mode runs).
- The fixture body does NOT currently receive a `request` argument. Remediation requires adding `request: pytest.FixtureRequest` to the signature and reading the stash via `getattr(request.session.config, "_mcp_contracts_config", None)`, with a fall-through to bare `Config()` for the framework-self-test path (mirror `fixtures.py:108-111`'s exact pattern).
- Alternative (rejected): just pass `mcp_config` as a fixture dependency. Cleanest but changes the fixture's public dependency list — operators reading the fixture body see an extra argument. The `request`-based stash lookup matches `fixtures.py:mcp_config`'s own implementation pattern and surfaces no new public dependency.

**Concrete remediation pattern** (planner copies into the plan, mirroring `fixtures.py:108-111`):

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(request: pytest.FixtureRequest, mcp_client: McpTestClient):
    ...
    # Step 3: load the generated package from cfg.test_code.generated_root/<slug>/.
    cfg = getattr(request.session.config, "_mcp_contracts_config", None)
    if cfg is None:
        cfg = Config()  # framework-self-test fallback; documented at fixtures.py:100-111
    generated_root = cfg.test_code.generated_root
    ...
```

### Finding 3 — Current Config model home + Literal precedent

**Conclusion: `Config` lives at `src/mcp_test_framework/config.py:45`. It already has `extra="forbid"`. D-01/D-02/D-03 land as a single-line field addition + matching `config-init` scaffold emit line.**

**Evidence — current Config model** (`src/mcp_test_framework/config.py:45-68`):

```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    homelab: HomelabConfig = Field(default_factory=HomelabConfig)
    test_code: TestCodeConfig = Field(...)            # REQUIRED, no default
    judge_timeout_seconds: int = 120
    version: int = 2
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
```

- `frozen=True` is on the model — bare `Config()` returns a frozen instance, so the new field must have an explicit default or it joins `test_code` as a required field.
- D-03 locks the default = `'strict'`, so D-01/D-02/D-03 together produce one field add:
  ```python
  host_isolation: Literal['strict', 'passthrough'] = 'strict'
  ```
- `Literal[...]` precedent in the codebase: Phase 33 added `skip_buckets: list[Literal['schema', 'description', 'output']] = Field(default_factory=list)` on `ToolConfig`. Same Pydantic v2 idiom; `extra='forbid'` already produces a stock `literal_error` for unknown values.
- `version` field already uses an `@field_validator("version", mode="after")` to produce a custom message (`config.py:70-80`). D-04 deliberately does NOT add a `@field_validator` — Pydantic's stock `literal_error` already names the two valid values; the operator-tone wrapping lives in `cli.py` exclusively (mirrors Phase 31 D-01/D-02).

**Constraints inherited automatically:**
- `frozen=True` → operator-supplied YAML `host_isolation: ...` is parsed once; spawn sites read the resolved value, never mutate it.
- `extra='forbid'` → typo at the top-level (e.g. `host_isolaton:`) surfaces as `extra_forbidden` with `loc=('host_isolaton',)`, NOT `literal_error` with `loc=('host_isolation',)`. Both shapes are operator-tone-handled (existing `extra_forbidden` falls through to the generic mapper at `cli.py:350-367`; the new D-04 branch specifically targets `(literal_error, ('host_isolation',))`).

### Finding 4 — Bare `Config()` call site inventory

See full inventory table in next section. Summary count: **3 in `src/`** (matches CONTEXT.md), **6 file-level call counts in `tests/`** across 4 distinct test files (multiple sites in some files).

The CONTEXT.md count is wrong on one point — `cli.py:15` is NOT a bare `Config()` call site. It's a docstring reference (`"... passes it as a 'yaml_file' kwarg to Config()."` on the `_load_config` doc). The actual bare construction sites in `src/` are TWO:

1. `src/mcp_test_framework/fixtures.py:111` — `return Config()` in the `mcp_config` fixture's stash-miss branch. **Intentional and correct.** Two cases trigger it: (a) framework self-tests that bypass the plugin and don't request `mcp_config`, (b) tests that monkeypatch `Config` at fixture-resolution time (see `test_mcp_config_fixture.py:88-93`). Mode-agnostic: returns the v2 model default which IS `host_isolation='strict'` after D-03 — so the implicit assumption ("bare `Config()` → strict") is preserved. **Remediation: 2-line comment block stating the implicit `strict` mode + cite the fallback path.**

2. `src/mcp_test_framework/test_code/session.py:67` — `cfg = Config()` inside the session-scoped `mcp_session` fixture. **High-risk bug for ISOL-05.** Per Finding 2, the stash is populated by this point; bare `Config()` bypasses the operator's `host_isolation: passthrough` setting in YAML, so under passthrough mode `cfg.test_code.generated_root` is read from defaults instead of the loaded YAML. Today (pre-Phase-34) the bug is latent because the bare `Config()` already misses `test_code.generated_root` overrides for operators not in the framework-self-test path — but the canonical missing-required-field error fires before that bug surfaces visibly. The fix lands here as a stash-routing change (see Finding 2's code snippet). **Remediation: route through stash with `request: pytest.FixtureRequest` parameter.**

### Finding 5 — Phase 31 D-04 error-mapper factoring status

**Conclusion: the error mapper is NOT yet factored into a shared module. `_plugin.py:228` lazy-imports `_emit_operator_error_for_validation` directly from `cli.py`. Phase 34 D-04 adds ONE branch to the existing function and BOTH personas inherit the new branch via the existing lazy-import path.**

**Evidence:**

- `cli.py:243` — `_emit_operator_error_for_validation(exc: ValidationError, *, source: str)` is defined here.
- `_plugin.py:228` — `from mcp_test_framework.cli import _emit_operator_error_for_validation` (inside `pytest_configure`'s `except ValidationError` arm, line 226–240). Lazy import to avoid `cli.py` ↔ `_plugin.py` circular at module-load time.
- `_emit_operator_error` (the renderer) was factored out into `_runner.py` (re-exported from `cli.py:96` with `noqa: E402`). This factoring exists, but the VALIDATION-error mapper (the function the branch goes into) still lives in `cli.py`.

**Implication for D-04:**

- Add the new branch inside `_emit_operator_error_for_validation` in `cli.py`. One source edit covers both surfaces.
- Branch shape — based on the existing `sdet_err` lookup pattern at `cli.py:318-335`:
  ```python
  literal_host_isolation_err = next(
      (
          e
          for e in errors
          if e.get("type") == "literal_error"
          and tuple(e.get("loc", ())) == ("host_isolation",)
      ),
      None,
  )
  if literal_host_isolation_err is not None:
      bad_value = literal_host_isolation_err.get("input", "?")
      _emit_operator_error(
          summary=f"unknown host_isolation mode: {bad_value!r}",
          detail=[
              "host_isolation accepts only 'strict' or 'passthrough'.",
              "strict (default) isolates the spawned MCP subprocess from your host credentials and HOME;",
              "passthrough hands the operator's full env to the subprocess (xdist clamped to 1 worker).",
          ],
          next_step=(
              "set `host_isolation: strict` or `host_isolation: passthrough` in your config.yaml; "
              "see docs/LIBRARY-MODE.md §host-isolation for the trade-off"
          ),
      )
  ```
- Place the branch BEFORE the generic fallback at `cli.py:350-367` and AFTER the existing `sdet_err` and `missing` branches — matches the existing scan-all-errors-then-emit precedent so co-occurring `version`/`missing` errors still win their respective branches.
- Whether to factor out a shared helper module in this phase: **NOT recommended.** Phase 31 already chose the lazy-import-from-cli approach and pinned it via the import at `_plugin.py:228`. Factoring now creates an out-of-scope refactor (memory `feedback_phase_scope_intent.md` — phase scope = phase title). One D-04 branch lands in one file; the planner should not propose factoring.

### Finding 6 — Phase 31 D-08 banner surface readiness for the xdist clamp

**Conclusion: the `_mcptf_formatwarning` red-banner override IS present in `_plugin.py:90-100` AND is reachable from `pytest_configure` time, but it's bound to `warnings.warn` calls — NOT to arbitrary stderr writes. The ISOL-04 clamp banner uses `warnings.warn(...)` inside the clamp block, with the formatter swapped in/out under try/finally per the existing precedent at `_plugin.py:184-200` (MCPTF_CONFIG_FILE detector).**

**Evidence — existing reuse pattern** (`_plugin.py:184-200`):

```python
if os.environ.get("MCPTF_CONFIG_FILE"):
    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "MCPTF_CONFIG_FILE is set in your environment but"
            " no longer honored as of v1.5;"
            ...,
            DeprecationWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
```

This is the canonical "operator-tone red banner at `pytest_configure` time" surface. ISOL-04 reuses it verbatim:

```python
# Inside pytest_configure, after Config is stashed, before return.
if cfg.host_isolation == 'passthrough' and config.option.numprocesses:
    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "xdist worker count clamped to 1\n"
            "\n"
            "host_isolation=passthrough serializes subprocess spawns so the operator's "
            "credentials remain a single-owner resource.\n"
            "\n"
            "next: switch to host_isolation=strict for parallel xdist runs",
            UserWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
    config.option.numprocesses = 1
    config.option.tx = ["popen"]
```

**Category choice — `UserWarning` not `DeprecationWarning`:** the existing surface uses `DeprecationWarning` for env-var typos. Passthrough's xdist clamp is NOT a deprecation; it's a runtime mode constraint. `UserWarning` is the correct category. Pytest's `filterwarnings` machinery may suppress it by default in some configurations — the planner should verify that the project's `pyproject.toml` `[tool.pytest.ini_options]` does NOT carry a `filterwarnings = ["error::UserWarning"]` or similar that would turn the banner into a hard fail. (Quick spot check: project's `pyproject.toml` `addopts` line is `-m 'not live_homelab and not live_ollama'` — no `filterwarnings` override — so default behavior holds.)

**Confidence note:** the existing `_mcptf_formatwarning` is exercised by Phase 31 only on the MCPTF_CONFIG_FILE detector + `tests/sdet/` discovery detector. There is no existing test pinning the banner output from `pytest_configure` time under a passthrough-mode-stashed Config. The planner should add a new pin in `tests/framework/unit/test_error_style.py` (or sibling) asserting the rendered banner text contains the three locked phrases ("xdist worker count clamped to 1", "single-owner resource", "host_isolation=strict for parallel").

### Finding 7 — `config-init` scaffold emitter location

**Location:** `src/mcp_test_framework/cli.py:1704` — `def _format_tools_yaml_scaffold(tools: list[Tool]) -> str`.

The `header` literal in that function (`cli.py:1723-1771`) is a hand-formatted Python string with each top-level config field as a separately commented block: `ollama:`, `mcp_server:`, `judge_timeout_seconds:`, `version:`, `test_code:`, `tools:`.

**ISOL-06 scaffold addition (planner pins exact text):**

After the `version: 2` block (`cli.py:1742-1744`) and before the `test_code:` block (`cli.py:1746`), insert:

```python
"\n"
"# Host isolation mode. 'strict' (default) isolates the spawned MCP\n"
"# subprocess from your operator host (allowlist + tempdir HOME redirect +\n"
"# null keyring backend). 'passthrough' hands the operator's full env to\n"
"# the subprocess so live credentials and keyring are reachable; in this\n"
"# mode pytest-xdist worker count is clamped to 1.\n"
"host_isolation: strict\n"
```

Match the existing block's style:
- Inline comment above the value (not on the same line as the value — none of the existing scaffold lines use end-of-line comments).
- The CONTEXT.md Claude's Discretion proposed `host_isolation: strict  # 'strict' (default, isolated) or 'passthrough' (...)`. An end-of-line comment breaks the visual rhythm of the rest of the scaffold. **Planner should choose between (a) match CONTEXT.md verbatim with the end-of-line comment, or (b) match the surrounding scaffold style with a 5-line preceding comment block.** Either is operator-friendly; (b) is more consistent.

There is also a fallback scaffold path at `cli.py:1219-1241` (the FileNotFoundError arm of `config-init`) that builds a partial config and calls `_format_tools_yaml_scaffold([])` for the empty-tools-block tail. The fallback header (`cli.py:1228-1240`) is hand-written and does NOT call `_format_tools_yaml_scaffold` for the `mcp_server` block. The fallback header inherits the new `host_isolation:` line automatically because `_format_tools_yaml_scaffold` emits the full header for all-tool blocks. No separate edit needed for the fallback path.

## Bare `Config()` Inventory

### `src/` sites (audit deliverable per ISOL-05)

| file:line | Category | Recommended Remediation |
|-----------|----------|-------------------------|
| `src/mcp_test_framework/fixtures.py:111` | Mode-agnostic; framework-self-test fallback when plugin stash absent | Add 2-line inline comment: "Stash-miss fallback for framework self-tests that bypass the plugin. Returns Config() defaults including `host_isolation='strict'`. Operator runs always go through the stash branch above." NO behavior change — the bare construction is correct here. |
| `src/mcp_test_framework/test_code/session.py:67` | **HIGH RISK** — runs after stash population during fixture resolution; bypasses operator YAML | Add `request: pytest.FixtureRequest` to fixture signature; route through `getattr(request.session.config, "_mcp_contracts_config", None)` with bare-Config fallback (mirror `fixtures.py:108-111`). |
| `src/mcp_test_framework/cli.py:15` (docstring) | Not a call site — docstring reference inside `_load_config`'s docstring | No remediation (CONTEXT.md miscounted this as the third `src/` site). |
| `src/mcp_test_framework/cli.py:471` (docstring) | Not a call site — docstring reference | No remediation. |
| `src/mcp_test_framework/cli.py:551` (comment) | Not a call site — comment referencing the bootstrap fallback | No remediation. |
| `src/mcp_test_framework/fixtures.py:100, 208` (docstrings) | Not call sites — docstring references | No remediation. |

**Net `src/` actionable count: 2 (not 3 as CONTEXT.md states). The cli.py "site" is doc text.**

### `tests/` sites (categorized inventory per ISOL-05)

| file:line | Category | Recommended Remediation |
|-----------|----------|-------------------------|
| `tests/framework/smoke/test_smoke_homelab_mcp.py:40` (comment) | Not a call site (comment) | No remediation. Comment block referencing bare Config() construction in nearby tests. |
| `tests/framework/test_config_init_cli.py:104, 133` (comments / inline kwarg context) | Tests mode directly via config-init scaffold round-trip | No remediation. The tests construct Config from the emitted scaffold; after Phase 34 the scaffold gains `host_isolation: strict`, so the round-trip continues to validate. Verify the test still passes after scaffold edit (smoke validation). |
| `tests/framework/test_tool_config.py:36, 299` (comment + bare-Config-in-body context) | Mode-agnostic; constructs `Config(test_code=stub)` for ToolConfig table tests | No remediation. Tests assume strict mode implicitly via the v1.0–v1.4 default; D-03's `'strict'` default preserves this. |
| `tests/framework/unit/test_config.py:280, 287, 300, 314, 358, 365` | Mode-agnostic; pure Config-defaults validation | No remediation. Tests construct `Config(test_code=stub)` and assert defaults — D-03's explicit `'strict'` default extends this surface without breaking. ADD ONE new test: `test_host_isolation_default_is_strict` asserting `Config(test_code=_TEST_CODE_STUB).host_isolation == 'strict'` so Phase 35 SHIM-09 capstone has a permanent pin. |
| `tests/framework/unit/test_mcp_config_fixture.py:11, 76, 100` (test bodies + comments) | Tests mode directly — Tier 1 stash hit, Tier 2 bare fallback | No remediation. The Tier 2 test stubs Config; after Phase 34 the stub returns whatever the test wants, including a passthrough-mode config. Tier 1 stash-hit path is mode-agnostic. |
| `tests/framework/unit/test_runner_migration.py:101, 105, 118, 150, 166, 209` (bodies + comments) | Mode-agnostic; verifies env-var fallback removal (Phase 31 SHIM-05) | No remediation. Tests assert "bare `Config()` falls through to model defaults" — the new `host_isolation='strict'` default extends this naturally. |
| `tests/framework/unit/test_sdet_fixtures.py:122, 147` (test body bare Config() under monkeypatch) | Tests `test_code/session.py:67`'s bare Config() via `_install_session_config` monkeypatch shim | **Must update if Finding 2 remediation lands.** When `session.py:67` switches to stash-routing, the existing tests that monkeypatch `mcp_test_framework.test_code.session.Config` need either (a) updating to stash a Config on the test's pytest `session.config` fake, or (b) keeping the bare-Config fallback alive at `session.py` so the existing monkeypatch shim still works. Planner picks; (b) is the smaller change. |
| `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py:67, 196` | Operator-authored test-code scenarios — bare Config() inside scenario bodies | Document inline (2-line comment). These are SCENARIO-PERSONA tests by an SDET. They construct bare Config() to read `test_code.generated_root` and are intentionally simple. Under passthrough mode they would miss the YAML's `host_isolation` — but they don't consume `host_isolation`, so the bug is latent here. Add a 2-line comment explaining the assumption + when it would break. |
| `tests/framework/unit/test_config_init.py:100` (comment) | Not a call site | No remediation. |

**Net `tests/` actionable count: 1 add (new default test) + 1 conditional update (`test_sdet_fixtures.py` if Finding 2 lands) + 2 inline comment additions (`test_proxmox_vm_lifecycle_readme_sample.py:67, 196`).**

The inventory is the deliverable per CONTEXT.md Claude's Discretion ISOL-05: a categorized table, NOT a per-site refactor of every test file. Planner copies this table into the plan.

## Hook Ordering Decision

**Recommendation: clamp in `pytest_configure(tryfirst=True)` and mutate BOTH `config.option.numprocesses = 1` AND `config.option.tx = ["popen"]`.**

| Option | Verdict | Reason |
|--------|---------|--------|
| `pytest_configure(tryfirst=True)` mutating only `numprocesses` | ❌ Insufficient | xdist's `pytest_cmdline_main(tryfirst=True)` already populated `tx = ["popen"]*N` BEFORE any `pytest_configure` runs. NodeManager reads `tx`, not `numprocesses`, so 4 workers still spawn. |
| `pytest_configure(tryfirst=True)` mutating BOTH `numprocesses` and `tx` | ✅ Recommended | Same hook that already loads + stashes the Config; we know the mode by this point. xdist's DSession reads `tx` at `pytest_sessionstart(trylast=True)` — plenty of time. |
| `pytest_cmdline_main(tryfirst=True)` | ❌ Wrong phase | Fires BEFORE Config is loaded — we don't know mode yet. Would require duplicating Config-loading logic in two hooks. |
| `pytest_xdist_setupnodes` (CONTEXT.md fallback suggestion) | ❌ Not a real hook | xdist exposes `pytest_xdist_auto_num_workers` (fires only for `-n auto`/`-n logical`, never numeric `-n 4`) and `pytest_xdist_node_collection_finished` (collection-time, after spawn). Neither is "before worker spawn for an explicit numeric `-n N`." |
| `pytest_xdist_auto_num_workers` returning 1 | ❌ Wrong scope | Only fires for `-n auto`/`-n logical`. An operator running `-n 4` (numeric) under passthrough wouldn't be clamped. |

**Citation chain:**
- xdist `pytest_cmdline_main(tryfirst=True)` resolves `tx` before any `pytest_configure`: `https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/plugin.py` (verified via WebFetch).
- xdist `NodeManager.setup_nodes()` reads `config.option.tx` at `pytest_sessionstart(trylast=True)`: `https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/workermanage.py` (verified via WebFetch).
- Pytest hook ordering rules — wrappers > tryfirst > default > trylast: `https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html`.

## Open Questions for Planner

1. **Banner copy authority.** CONTEXT.md Claude's Discretion locks the banner's three-part SHAPE but NOT the exact wording. The planner pins the verbatim text against a `tests/framework/unit/test_error_style.py` (or sibling) assertion. Draft text in Finding 6 — planner can edit. Surface candidate: extract to `docs/ERROR-STYLE.md` "Reference messages (locked for downstream phases)" section so it lands in the lock-list alongside SAFE-03, SAFE-06, the skip-vs-skip_buckets reference.

2. **`config-init` scaffold comment style — inline vs preceding block.** Finding 7 shows the existing scaffold uses preceding-comment blocks for every field. CONTEXT.md Claude's Discretion proposed an end-of-line comment. Planner picks. Recommendation: match the surrounding scaffold style (preceding block) — operator's eye is already trained to read top-down comments.

3. **`tests/framework/unit/test_sdet_fixtures.py` monkeypatch lifetime.** Finding 4 + Finding 2 interact: if Finding 2's stash-routing fix lands, the `_install_session_config` monkeypatch shim at `test_sdet_fixtures.py:142-163` may stop being load-bearing. Planner decides between (a) update the shim to stash a Config on a fake session, or (b) keep `session.py:67` falling back to bare Config when `request.session.config._mcp_contracts_config` is None, which preserves the shim's current contract. (b) is the smaller change AND matches `fixtures.py:108-111`'s pattern, so default to (b).

4. **Should `_isolation.py` module docstring's "isolation is ALWAYS-ON" line be the only docstring edit, or should the locked-allowlist warning blocks also be reworded?** The docstring at `_isolation.py:1-38` says "Isolation is ALWAYS-ON. No toggle, no `--no-isolation` CLI escape hatch." That's now false. Planner edits the module docstring AND the inline maintainer warning at lines 33–37 ("DO NOT widen `_PASSTHROUGH_ALLOWLIST` ..."). Recommended: the docstring becomes "Isolation is ON BY DEFAULT (`host_isolation='strict'`) and disabled per-config-file via `host_isolation='passthrough'`. ..." preserving the spirit and the maintainer-do-not-widen warning.

5. **D-08 plumbing through to `fixtures.py:432` and `mcp_client.py:189`.** Both spawn sites currently call `_build_isolated_env(_isolated_home)` directly. D-07/D-08 introduce `_build_subprocess_env(mode, isolated_home)`. The `mcp_client.py:189` site lives inside `McpTestClient.__aenter__` — which today does NOT have a Config reference. The constructor signature is `__init__(self, command, args, timeout_seconds)`. Planner decides whether to (a) extend the constructor with a `host_isolation: Literal[...]` parameter (smallest surface change, callers pass `cfg.host_isolation`), or (b) plumb through a small private `_mode` attribute. (a) is the SEED-022-clean answer — caller (CLI/fixture) passes data; the primitive (`McpTestClient`) takes data. CONTEXT.md D-08 implicitly assumes (a) by mandating that callers "pass `cfg.host_isolation` as the `mode` arg." Document in the plan.

6. **`_isolated_home` fixture's None-yield semantics.** D-06 says the fixture short-circuits and yields None (or equivalent) under passthrough. `mcp_client` fixture's signature (`fixtures.py:397`) currently types `_isolated_home: Path`. Under passthrough it would be `Path | None`. The dispatcher `_build_subprocess_env(mode, isolated_home: Path | None)` must handle `isolated_home=None` only when `mode='passthrough'`. Add a defensive assert: `if mode == 'strict': assert isolated_home is not None`. Pin via unit test.

7. **Whether to deliver the test_code/session.py:67 fix in this phase or defer.** Finding 2 confirms the bug is real and the remediation is small. CONTEXT.md Claude's Discretion ISOL-05 names this site as "the highest-risk site" and recommends routing through the stash. Recommendation: deliver in this phase. Memory `feedback_phase_scope_intent.md` locks the audit IN-scope; routing the highest-risk site is the natural close.

## RESEARCH COMPLETE
