# Phase 34: Opt-in host isolation passthrough (999.3) - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 11 modify + 1 new test + 4 docs
**Analogs found:** 16 / 16 (every file modifies an existing surface, so the analog is almost always the file itself plus a sibling pattern within the codebase)

## File Classification

| File | New / Modify | Role | Data Flow | Closest Analog | Match |
|------|--------------|------|-----------|----------------|-------|
| `src/mcp_test_framework/config.py` | MODIFY | config / model | request-response (load + validate) | self (`Config` class) + `ToolConfig.skip_buckets` in `models.py` (Phase 33 Literal precedent) | exact |
| `src/mcp_test_framework/_isolation.py` | MODIFY | utility (env builder primitive) | transform | self (`_build_isolated_env`) | exact |
| `src/mcp_test_framework/fixtures.py` | MODIFY | fixture (pytest session-scoped) | request-response (spawn-site) | self (`mcp_client` at L428-433, `_isolated_home` at L364-388, `mcp_config` stash at L108-111) | exact |
| `src/mcp_test_framework/mcp_client.py` | MODIFY | client (subprocess spawn) | event-driven (stdio session) | self (`McpTestClient.__aenter__` L172-190); SEED-022 caller-passes-data idiom | exact |
| `src/mcp_test_framework/cli.py` (error mapper) | MODIFY | controller (error renderer) | request-response | self (`sdet_err` branch L318-335 in `_emit_operator_error_for_validation`) | exact |
| `src/mcp_test_framework/cli.py` (scaffold emitter) | MODIFY | utility (config emitter) | transform | self (`_format_tools_yaml_scaffold` L1704-1785, particularly the `test_code:` block at L1746-1759) | exact |
| `src/mcp_test_framework/_plugin.py` | MODIFY | plugin (pytest hook) | event-driven | self (`pytest_configure` L159-247; the MCPTF_CONFIG_FILE warn block L184-200 is the verbatim banner-emit pattern) | exact |
| `src/mcp_test_framework/test_code/session.py` | MODIFY | fixture (test-code) | request-response | `fixtures.py:108-111` (stash-lookup-with-fallback) | role-match |
| `tests/framework/unit/test_error_style.py` | MODIFY | test (regression pin) | request-response | self (`test_error_style_sdet_rejection_message` L98-138) | exact |
| `tests/framework/unit/test_config.py` (default pin) | MODIFY | test (Config defaults) | request-response | self (existing `Config(test_code=_TEST_CODE_STUB)` defaults tests at L280-365) | exact |
| `tests/framework/unit/` (new dispatcher + clamp tests) | NEW | test (unit) | transform | `test_error_style.py` shape for the clamp test; new file `test_isolation_dispatcher.py` for the dispatcher | role-match |
| `tests/framework/unit/test_sdet_fixtures.py` | CONDITIONAL UPDATE | test (test-code fixture monkeypatch) | request-response | self (L122-163, `_install_session_config` monkeypatch shim) | exact |
| `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` | MODIFY (2-line comments only) | test (operator-authored scenario) | request-response | self (L67, L196 — bare-Config audit annotation) | n/a (doc-only) |
| `README.md` | MODIFY | docs | n/a | Phase 33 `skip_buckets` block at L416-459 (~45 lines, YAML + before/after output + digest slice) | exact |
| `docs/LIBRARY-MODE.md` | MODIFY | docs | n/a | Phase 33 worked-example in same file (codegen-driven smoke section) | exact |
| `docs/ERROR-STYLE.md` | MODIFY | docs | n/a | existing SAFE-03 / SAFE-06 / sdet-rejection reference-message entries | exact |

## Pattern Assignments

### `src/mcp_test_framework/config.py` (config / model, request-response)

**Analog:** self — existing field block at L53-68, plus Phase 33's `skip_buckets: list[Literal[...]]` precedent in `models.py:103`.

**Field-block pattern** (`config.py:53-68`):

```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    homelab: HomelabConfig = Field(default_factory=HomelabConfig)
    test_code: TestCodeConfig = Field(...)
    judge_timeout_seconds: int = 120
    version: int = 2
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
```

**Literal-with-default pattern** (Phase 33 precedent at `models.py:103-115`):

```python
skip_buckets: list[BucketName] = Field(
    default_factory=list,
    description=(
        "..."
    ),
)
```

`BucketName = Literal['schema','judge','output']` (imported from `contracts/_buckets`). Stock pydantic `literal_error` fires on typo — no custom validator. **D-04 deliberately mirrors this:** no `@field_validator`, no `@model_validator`. New field goes between `version: int = 2` and `tools:` (top-level placement per D-01); the operator-tone wrapping lives in `cli.py` exclusively.

**Difference for new file:** one line added — `host_isolation: Literal['strict', 'passthrough'] = 'strict'`. Inline `Literal[...]` (no separate type alias) is fine since the values appear nowhere else; Phase 33 used a named alias because `BucketName` is reused at four sites. Single-site use → inline.

---

### `src/mcp_test_framework/_isolation.py` (utility primitive, transform)

**Analog:** self — existing `_build_isolated_env(isolated_home)` at L78-104.

**Existing builder pattern** (`_isolation.py:78-104`):

```python
def _build_isolated_env(isolated_home: Path) -> dict[str, str]:
    """Return env dict for StdioServerParameters spawning into an isolated home.

    ...
    The returned dict is the COMPLETE env passed to StdioServerParameters --
    NOT a delta on top of os.environ. Anything not in this dict is invisible
    to the subprocess (intentional; that is the isolation guarantee).
    """
    env: dict[str, str] = {}
    for name in _PASSTHROUGH_ALLOWLIST:
        if (value := os.environ.get(name)) is not None:
            env[name] = value
    for name, value in os.environ.items():
        if name.startswith(_MCP_PREFIX):
            env[name] = value
    home_str = str(isolated_home)
    for name in _HOME_OVERRIDES:
        env[name] = home_str
    env.update(_KEYRING_OVERRIDES)
    return env
```

**Module-level docstring constraint** (`_isolation.py:9`):

```
- Isolation is ALWAYS-ON. No toggle, no ``--no-isolation`` CLI escape hatch.
```

This sentence is now false and must be reworded per Open Question 4 in research. Recommended replacement: `Isolation is ON BY DEFAULT (host_isolation='strict') and disabled per-config-file via host_isolation='passthrough'. The maintainer warning at lines 33-37 stays in force for the strict allowlist; passthrough is all-or-nothing by design (no per-var widening).`

**Difference for new file:** add two siblings and one dispatcher (per D-07/D-08):

```python
def _build_passthrough_env() -> dict[str, str]:
    """Return a literal dict(os.environ) copy — passthrough mode contract."""
    return dict(os.environ)

def _build_subprocess_env(
    mode: Literal['strict', 'passthrough'],
    isolated_home: Path | None,
) -> dict[str, str]:
    if mode == 'passthrough':
        return _build_passthrough_env()
    assert isolated_home is not None, (
        "_build_subprocess_env(mode='strict') requires isolated_home"
    )
    return _build_isolated_env(isolated_home)
```

**SEED-022 constraint** (locked by `project_framework_primitives_sdet_safety_principle.md`): the dispatcher takes `mode: str`, NOT `cfg: Config`. `_isolation.py` must NOT import `config.py`. The caller passes data.

---

### `src/mcp_test_framework/fixtures.py` (fixture, request-response)

**Analog:** self — three sites.

**Stash-lookup-with-fallback pattern** (`fixtures.py:108-111`) — the seam test-code session.py mirrors:

```python
cfg = getattr(request.session.config, "_mcp_contracts_config", None)
if cfg is not None:
    return cfg
return Config()
```

**`_isolated_home` short-circuit landing site** (`fixtures.py:364-388`):

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def _isolated_home():
    """Per-session tempdir owning the HOME/USERPROFILE redirect target.
    ...
    """
    async with AsyncExitStack() as stack:
        tmpdir = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mcp-test-fw-")
        )
        yield Path(tmpdir)
```

**Spawn-site pattern (D-07/D-08 landing site)** (`fixtures.py:397-433`):

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(mcp_config: Config, _preflight, _isolated_home: Path):
    """Long-lived McpTestClient session ..."""
    params = StdioServerParameters(
        command=mcp_config.mcp_server.command,
        args=mcp_config.mcp_server.args,
        # Allowlisted env + HOME redirect to the shared isolation tempdir.
        env=_build_isolated_env(_isolated_home),
    )
```

**Difference for new file:** three coordinated edits:
1. `_isolated_home`: branch on `mcp_config.host_isolation`. Under passthrough, yield `None` without entering the tempdir context manager (D-06). Requires reading `mcp_config` — promote the fixture to take `mcp_config` as a dependency, OR thread the mode via a new helper. Plan-time decision; if `_isolated_home` gains a `mcp_config` dependency, verify pytest-asyncio fixture-scope compatibility (both session-scoped → fine).
2. `mcp_client` body L432: swap `_build_isolated_env(_isolated_home)` → `_build_subprocess_env(mcp_config.host_isolation, _isolated_home)`. Type annotation on the fixture param needs widening to `Path | None`.
3. Update the inline comment at L431 ("Allowlisted env + HOME redirect …") to describe the dispatcher's two modes.

---

### `src/mcp_test_framework/mcp_client.py` (client, event-driven)

**Analog:** self — `McpTestClient.__aenter__` at L172-200, plus the import at L48.

**Spawn-site pattern** (`mcp_client.py:172-194`):

```python
stack = AsyncExitStack()
try:
    isolated_home = Path(
        stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mcp-test-fw-cli-")
        )
    )
    params = StdioServerParameters(
        command=self._command,
        args=self._args,
        # Allowlisted env + HOME redirect to the isolation tempdir.
        env=_build_isolated_env(isolated_home),
    )
```

**Difference for new file (per research Open Question 5, SEED-022-clean path (a)):**
- Extend `__init__` signature with `host_isolation: Literal['strict','passthrough'] = 'strict'` — default preserves all current callers; explicit pass from the CLI / fixture / `_discover_tools_live` (`_plugin.py:137-150`) passes `cfg.host_isolation`.
- Under passthrough at L180-184: skip the `tempfile.TemporaryDirectory` block entirely (no `enter_context` call → no orphan tempdir).
- L189: swap `_build_isolated_env(isolated_home)` → `_build_subprocess_env(self._host_isolation, isolated_home if self._host_isolation == 'strict' else None)`.
- Import update at L48: `from mcp_test_framework._isolation import _build_subprocess_env` (drop `_build_isolated_env` direct import).

**Caller update sites for the new constructor arg:**
- `_plugin.py:144-148` — `_discover_tools_live(cfg)` already has `cfg` in scope; add `cfg.host_isolation` positional or keyword.
- Any test-side `McpTestClient(...)` callers — default keeps them green; planner audits via grep.

---

### `src/mcp_test_framework/cli.py` — error-mapper branch (controller, request-response)

**Analog:** self — `_emit_operator_error_for_validation` at L243-367, specifically the `sdet_err` branch at L318-335.

**Existing branch pattern** (`cli.py:318-335`):

```python
sdet_err = next(  # noqa: sdet-rename-shim
    (
        e
        for e in errors
        if e.get("type") == "extra_forbidden"
        and tuple(e.get("loc", ())) == ("sdet",)  # noqa: sdet-rename-shim
    ),
    None,
)
if sdet_err is not None:  # noqa: sdet-rename-shim
    _emit_operator_error(
        summary="unknown config key: sdet",  # noqa: sdet-rename-shim
        detail=[
            "the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5.",  # noqa: sdet-rename-shim
            "your existing block under `sdet:` ports forward unchanged -- just rename the top-level key.",  # noqa: sdet-rename-shim
        ],
        next_step="rename the `sdet:` key to `test_code:` in your config.yaml",  # noqa: sdet-rename-shim
    )
```

**Difference for new file:** same shape, new branch keyed on `(err_type='literal_error', loc=('host_isolation',))`. Branch placement: **after** the `version_err` and `sdet_err` branches, **before** the generic `missing` branch at L336 — matches the "scan-all-errors, prefer specific over generic" precedent. Draft text from research Finding 5:

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
            "strict (default) isolates the spawned MCP subprocess from "
            "your host credentials and HOME;",
            "passthrough hands the operator's full env to the subprocess "
            "(xdist clamped to 1 worker).",
        ],
        next_step=(
            "set `host_isolation: strict` or `host_isolation: passthrough` "
            "in your config.yaml; see docs/LIBRARY-MODE.md §host-isolation "
            "for the trade-off"
        ),
    )
```

**Naming nit:** research Finding 0 notes CONTEXT.md repeatedly references `_emit_operator_error_for_validation_error` (trailing `_error`). The actual symbol at `cli.py:243` is `_emit_operator_error_for_validation` (no trailing `_error`). `_plugin.py:228` imports the correct name. Planner uses the actual symbol.

---

### `src/mcp_test_framework/cli.py` — `_format_tools_yaml_scaffold` (utility, transform)

**Analog:** self — `_format_tools_yaml_scaffold` at L1704-1785, specifically the preceding-comment-block pattern for the `test_code:` field (L1746-1759).

**Existing preceding-comment-block pattern** (`cli.py:1740-1759`):

```python
"# Outer budget cap on each judge HTTP call.\n"
"judge_timeout_seconds: 120\n"
"\n"
"# Schema version. This release accepts version 2.\n"
"version: 2\n"
"\n"
"# test-code codegen + fixture output path. REQUIRED.\n"
"#\n"
"# The `mcp-test-framework gen-test-classes` command writes generated\n"
"# typed classes into <generated_root>/<server_slug>/, and the\n"
"# `mcp_session` pytest fixture loads them from the same path.\n"
"# ...\n"
"# Non-absolute paths are resolved relative to the current working\n"
"# directory when the config is loaded.\n"
"test_code:\n"
f"  generated_root: {json.dumps('tests/test_code/_generated')}\n"
```

**Difference for new file:** insert a new block between `version: 2` (L1744) and the blank-line/`test_code:` block (L1746). Per research Finding 7 and Open Question 2, **use the preceding-comment-block style (not end-of-line)** to match scaffold visual rhythm. Draft text:

```python
"\n"
"# Host isolation mode. 'strict' (default) isolates the spawned MCP\n"
"# subprocess from your operator host (allowlist + tempdir HOME redirect +\n"
"# null keyring backend). 'passthrough' hands the operator's full env to\n"
"# the subprocess so live credentials and keyring are reachable; in this\n"
"# mode pytest-xdist worker count is clamped to 1.\n"
"host_isolation: strict\n"
```

The fallback scaffold path at `cli.py:1219-1241` calls `_format_tools_yaml_scaffold([])` and inherits the header automatically — no separate edit needed there.

---

### `src/mcp_test_framework/_plugin.py` (plugin, event-driven)

**Analog:** self — `pytest_configure` at L159-247, with two reusable surfaces:

**Verbatim banner-emit-under-formatwarning-swap pattern** (`_plugin.py:184-200`):

```python
if os.environ.get("MCPTF_CONFIG_FILE"):
    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "MCPTF_CONFIG_FILE is set in your environment but"
            " no longer honored as of v1.5;"
            " configure via `[tool.pytest.ini_options]"
            " mcp_config_file = PATH` in pyproject.toml or pass"
            " `--config PATH` to `mcp-contracts run`.",
            DeprecationWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
```

**The renderer it pairs with** (`_plugin.py:90-100`):

```python
def _mcptf_formatwarning(message, category, filename, lineno, line=None):
    """Operator-tone single-block render. ..."""
    prefix = "[mcp-contracts]"
    try:
        if sys.stderr.isatty():
            prefix = f"\x1b[31m{prefix}\x1b[0m"
    except Exception:
        pass
    return f"\n{prefix} {message}\n\n"
```

**Hook function decorator pattern** (no current `tryfirst` on `pytest_configure` in this plugin; planner must ADD `@pytest.hookimpl(tryfirst=True)` to the existing definition at L159). Per research Finding 1, this is the critical addition: the xdist clamp MUST run before xdist's own `pytest_configure(trylast=True)` registers `DSession`.

**Difference for new file:** new block at the end of `pytest_configure` (after `config._mcp_contracts_config = cfg` at L247). Per research Finding 6:

```python
# Inside pytest_configure, after Config is stashed.
# ISOL-04: clamp xdist worker count to 1 under passthrough.
if cfg.host_isolation == 'passthrough' and config.option.numprocesses:
    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "xdist worker count clamped to 1\n"
            "\n"
            "host_isolation=passthrough serializes subprocess spawns so the "
            "operator's credentials remain a single-owner resource.\n"
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

**Load-bearing invariant (pin via test):** both `numprocesses` AND `tx` must be mutated together. Per research Finding 1, xdist's `NodeManager.setup_nodes()` reads `tx`, not `numprocesses`. Mutating only `numprocesses` leaves 4 workers spawning.

Also: add `@pytest.hookimpl(tryfirst=True)` decorator to the existing `pytest_configure` function (no current decorator → defaults to "default" ordering, runs after xdist's `pytest_cmdline_main(tryfirst=True)` but in the indeterminate band with other plugins). Per the hook lifecycle in research Finding 1, `tryfirst=True` keeps us safely before xdist's `pytest_configure(trylast=True)` DSession registration.

---

### `src/mcp_test_framework/test_code/session.py` (fixture, request-response)

**Analog:** `fixtures.py:108-111` (the canonical stash-lookup-with-fallback pattern).

**Existing bare-Config site** (`test_code/session.py:54-67`):

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    """Live ClientSession driver + active test-code registry."""
    ...
    # Step 3: load the generated package from cfg.test_code.generated_root/<slug>/.
    cfg = Config()
```

**Difference for new file:** add `request: pytest.FixtureRequest` to fixture signature and route through stash with bare-Config fallback (per research Finding 2 + Finding 4):

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
):
    ...
    # Step 3: load the generated package from cfg.test_code.generated_root/<slug>/.
    cfg = getattr(request.session.config, "_mcp_contracts_config", None)
    if cfg is None:
        cfg = Config()  # framework-self-test fallback; mirrors fixtures.py:108-111
    generated_root = cfg.test_code.generated_root
```

Keep the bare-Config fallback alive (per research Open Question 3 recommendation (b)) so `tests/framework/unit/test_sdet_fixtures.py:122-163`'s `_install_session_config` monkeypatch shim doesn't need a coordinated update.

---

### `tests/framework/unit/test_error_style.py` (test, request-response)

**Analog:** self — `test_error_style_sdet_rejection_message` at L98-138 is the verbatim template for the new `host_isolation` typo pin.

**Existing rejection-message-pin pattern** (`test_error_style.py:98-138`):

```python
def test_error_style_sdet_rejection_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 31 SHIM-04: a `sdet:`-keyed config triggers the D-02 three-part
    operator-tone rejection message via the
    `_emit_operator_error_for_validation` dispatcher branch added in Task 2.

    Pins the verbatim summary/detail/next_step text from CONTEXT D-02.
    Future drift -- in either cli.py or this test -- breaks the assertion."""
    import typer
    from pydantic import ValidationError

    from mcp_test_framework.cli import _emit_operator_error_for_validation
    from mcp_test_framework.config import Config

    cfg = tmp_path / "sdet.yaml"
    cfg.write_text(
        "version: 2\nsdet:\n  generated_root: out\n",
        encoding="utf-8",
    )
    try:
        Config(yaml_file=str(cfg))
    except ValidationError as exc:
        with pytest.raises(typer.Exit) as exit_info:
            _emit_operator_error_for_validation(exc, source=str(cfg))
        assert exit_info.value.exit_code == 2
        captured = capsys.readouterr()
        text = captured.out + captured.err
        assert "unknown config key: sdet" in text
        assert "the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5." in text
        assert "your existing block under `sdet:` ports forward unchanged" in text
        assert "rename the `sdet:` key to `test_code:` in your config.yaml" in text
    else:
        raise AssertionError(
            "Config(yaml_file=...) with sdet: key should have raised ValidationError"
        )
```

**Difference for new file:** copy verbatim, swap the YAML body to `version: 2\nhost_isolation: hermetic\ntest_code:\n  generated_root: out\n` (note: `test_code` is required so the YAML needs it; otherwise the test fires on `missing` before `literal_error`). Assert the four locked phrases from the new branch (summary phrase, "strict (default)", "passthrough hands the operator's full env", and the `next_step` pointer at `docs/LIBRARY-MODE.md §host-isolation`).

---

### `tests/framework/unit/test_config.py` (test, request-response)

**Analog:** self — existing `Config(test_code=_TEST_CODE_STUB)` default-assertion tests at L280-365 (six call sites).

**Pattern:** straight defaults-assertion test, no fixtures.

**Difference for new file:** add ONE new test (Phase 35 SHIM-09 capstone pin):

```python
def test_host_isolation_default_is_strict() -> None:
    """ISOL-01 D-03: bare Config() returns host_isolation='strict'.

    Phase 35 SHIM-09 regression gate depends on this default — a future
    capstone-style sweep greps for the top-level `host_isolation` field
    AND asserts the v1.5-shipped default value is preserved."""
    cfg = Config(test_code=_TEST_CODE_STUB)
    assert cfg.host_isolation == "strict"
```

---

### NEW `tests/framework/unit/test_isolation_dispatcher.py` (test, transform)

**Analog:** none directly — new file. Closest sibling: `tests/framework/unit/test_error_style.py` (operator-error pin shape) and the existing `_build_isolated_env` consumers (no current unit test on the env builder directly per Grep).

**Difference for new file:** three load-bearing pins:

1. `_build_subprocess_env(mode='passthrough', isolated_home=None)` returns a `dict` equal to `dict(os.environ)` — passthrough is a literal env copy (D-05).
2. `_build_subprocess_env(mode='strict', isolated_home=Path('/tmp/x'))` delegates to the existing `_build_isolated_env` (verify by checking presence of `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` and `HOME=/tmp/x` keys).
3. `_build_subprocess_env(mode='strict', isolated_home=None)` raises (defensive `assert isolated_home is not None`, per research Open Question 6).

Use `monkeypatch.setenv` / `monkeypatch.delenv` to seed a clean parent env; do not rely on test-runner host env.

---

### NEW `tests/framework/unit/test_xdist_clamp.py` (test, transform)

**Analog:** test_error_style.py shape for "assert text in captured output" plus `tests/framework/unit/test_mcp_config_fixture.py` (fake `pytest.Config` construction pattern).

**Difference for new file:** Per research Finding 1's "sanity check the planner should pin via a task":

```python
def test_passthrough_clamps_xdist_numprocesses_and_tx(capsys) -> None:
    """ISOL-04: pytest_configure under host_isolation=passthrough clamps
    BOTH config.option.numprocesses (=1) AND config.option.tx (=['popen'])
    so xdist's NodeManager spawns one worker, not N. Banner-text pin
    asserts the three operator-tone locked phrases."""
    # Build a SimpleNamespace fake pytest.Config carrying:
    #   - getini -> returns "" so the ini-path arm short-circuits
    #   - option.numprocesses = 4 (operator passed -n 4)
    #   - _mcp_contracts_config = a Config with host_isolation='passthrough'
    # Then call _plugin.pytest_configure(fake_config) directly.
    # Assert: fake_config.option.numprocesses == 1
    #         fake_config.option.tx == ["popen"]
    # Plus: captured.err contains "xdist worker count clamped to 1"
    #       AND "single-owner resource" AND "host_isolation=strict for parallel".
```

The banner-text pin can also live in `test_error_style.py` if the planner prefers single-file co-location for all operator-tone reference messages.

---

### `tests/framework/unit/test_sdet_fixtures.py` (test, request-response — CONDITIONAL update)

**Analog:** self — `_install_session_config` monkeypatch shim at L142-163, called from tests at L122 and L147.

**Difference for new file:** Per research Open Question 3, default to recommendation (b) — **keep the bare-Config fallback alive at `session.py:67`** so the existing monkeypatch shim still works. If planner picks (a) instead, update the shim to stash a Config on the fake session's `config._mcp_contracts_config` attribute. (b) is smaller; default to (b) unless plan-time review surfaces a reason.

---

### `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` (test, request-response)

**Analog:** self — L67 and L196 bare-Config call sites.

**Difference for new file:** 2-line inline comment annotation only (per ISOL-05 inventory deliverable). Example:

```python
# NOTE (ISOL-05 audit): bare Config() in operator-authored scenario.
# Inherits host_isolation='strict' default; scenario does not consume the field.
cfg = Config()
```

---

## Shared Patterns

### Operator-tone three-part error message
**Source:** `docs/ERROR-STYLE.md` (summary / detail / next_step contract); rendered via `cli.py:_emit_operator_error`.
**Apply to:** `cli.py` literal_error branch (D-04), `_plugin.py` xdist-clamp banner (ISOL-04).
**Reference message text-pin:** every operator-facing rejection has a pinned regression assertion in `tests/framework/unit/test_error_style.py` (or sibling). New branches pinned same way.

### `_mcptf_formatwarning` red-banner surface (Phase 31 D-08)
**Source:** `src/mcp_test_framework/_plugin.py:87-100` (renderer) + L184-200 (try/finally formatter swap).
**Apply to:** ISOL-04 xdist-clamp banner. Reuse verbatim; do NOT introduce a parallel output channel.
**Category:** `UserWarning` (NOT `DeprecationWarning`) — the clamp is a runtime mode constraint, not a deprecation. Project's `pyproject.toml` has no `filterwarnings = ["error::UserWarning"]` (verified via spot-check; planner re-checks if any review-fix changes ini options).

### Caller-passes-data primitives (SEED-022)
**Source:** memory `project_framework_primitives_sdet_safety_principle.md`.
**Apply to:** `_isolation.py` dispatcher (takes `mode: Literal[...]`, not `cfg: Config`), `mcp_client.py` constructor extension (takes `host_isolation: Literal[...]`, not the full Config).
**Excerpt** (mental shape, no exact precedent in `_isolation.py` because it currently takes only `Path`):

```python
# Caller (fixtures.py / mcp_client.py / _plugin.py) extracts the data:
mode = cfg.host_isolation
# Primitive (_isolation.py) takes plain data:
env = _build_subprocess_env(mode, isolated_home)
```

### Stash-lookup-with-fallback (Phase 27 / Phase 31 plumbing seam)
**Source:** `fixtures.py:108-111`.
**Apply to:** `test_code/session.py:67` (Finding 2 remediation). Add `request: pytest.FixtureRequest` to the fixture signature; route through stash; fall back to bare `Config()` so the framework-self-test path and `test_sdet_fixtures.py`'s monkeypatch shim both continue to work.

### `extra='forbid'` + `Literal[...]` for opt-in mode fields
**Source:** Phase 33 precedent — `models.py:103` `skip_buckets: list[BucketName]` (where `BucketName = Literal['schema','judge','output']`).
**Apply to:** `config.py` `host_isolation` field. No custom validator; rely on stock `literal_error` for typos; operator-tone wrapping in `cli.py` exclusively.

### Worked-example doc shape (Phase 33 D-03)
**Source:** `README.md:416-459` (the `skip_buckets` block — ~45 lines, YAML + before/after output + digest slice).
**Apply to:** README and `docs/LIBRARY-MODE.md` for ISOL-06 worked example. Use the Phase 30 UAT-1 homelab-mcp Proxmox credential repro (per memory `project_isolation_blocks_live_uat.md`); ~30-50 lines per doc; SEED-022 + no-keyring-faking lock cited inline (not a separate sidebar).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/framework/unit/test_isolation_dispatcher.py` | test (unit) | transform | No existing unit test directly exercises `_build_isolated_env` — currently tested only through fixture integration. New file, but shape mirrors `tests/framework/unit/test_error_style.py` for the "import + assert" idiom. |
| `tests/framework/unit/test_xdist_clamp.py` | test (unit) | transform | No existing test injects a fake `pytest.Config` into `_plugin.pytest_configure` to assert option-mutation side effects. Closest analog (fake-Config construction): `test_mcp_config_fixture.py:88-93`. New file, planner copies the fake-Config builder pattern from there if it exists; otherwise hand-roll `SimpleNamespace`. |

---

## Metadata

**Analog search scope:** `src/mcp_test_framework/` (config, isolation, fixtures, mcp_client, cli, _plugin, test_code/session, models), `tests/framework/unit/` (test_error_style, test_config, test_mcp_config_fixture, test_sdet_fixtures), `docs/`, `README.md`.
**Files scanned:** 14 source files + 4 doc files + 6 test files = 24.
**Files actively read:** 9 (with multiple targeted reads on `config.py`, `_isolation.py`, `fixtures.py`, `mcp_client.py`, `cli.py`, `_plugin.py`, `test_code/session.py`, `test_error_style.py`, `models.py`, `README.md`).
**Pattern extraction date:** 2026-05-26.
