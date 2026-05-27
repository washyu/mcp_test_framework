---
phase: 34-opt-in-host-isolation-passthrough-999-3
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - src/mcp_test_framework/_isolation.py
  - src/mcp_test_framework/_plugin.py
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/config.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/mcp_client.py
  - src/mcp_test_framework/test_code/session.py
  - tests/framework/test_config_init_cli.py
  - tests/framework/unit/test_config.py
  - tests/framework/unit/test_error_style.py
  - tests/framework/unit/test_isolated_home_passthrough.py
  - tests/framework/unit/test_mcp_client_host_isolation.py
  - tests/framework/unit/test_mcp_session_host_isolation_stash.py
  - tests/framework/unit/test_plugin_host_isolation_wiring.py
  - tests/framework/unit/test_sdet_fixtures.py
  - tests/framework/unit/test_xdist_clamp.py
  - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 34 lands the binary `host_isolation: strict | passthrough` Config field with a dispatcher seam (`_isolation._build_subprocess_env`), threads the mode through `mcp_client.py`, `fixtures.py`, `_plugin.py`, and `test_code/session.py`, adds the `pytest_configure` xdist clamp (mutating both `numprocesses` and `tx`), the `literal_error` operator-tone branch in `cli.py`, and the scaffold emission. The doctrinal locks (SEED-022 framework-primitives, no-keyring-faking, tryfirst xdist clamp with both attributes) are honored at the framework seam.

Two BLOCKER findings concern the ISOL-05 bare-Config audit: the audit deliverable (`34-BARE-CONFIG-AUDIT.md`) and the inline audit comments at the live proxmox scenario both assert that bare `Config()` "inherits host_isolation='strict' default" — but `Config.test_code` is a REQUIRED field (`Field(...)`) since Phase 21.1, so bare `Config()` actually raises `ValidationError` before any field default can be inspected. The module-level call site is caught by a broad `try/except` and demoted to `pytest.skip()`; the fixture-body call site is NOT caught and will surface as a fixture error on any `live_homelab`-marked run. Two BLOCKERS classify because the misleading audit annotation actively prevents future readers from fixing the latent bugs.

WARNING items address dispatcher hygiene: `_PASSTHROUGH_ALLOWLIST` is named for the legacy term-of-art ("environment passthrough") but Phase 34 redefines "passthrough" to mean "full env, no isolation" — the strict-mode-only constant is now misleadingly named. `McpTestClient._wrap` hardcodes `_host_isolation='strict'` on instances built from the fixture's owner-task path, which is decorative but actively misleading for introspection. The xdist clamp only fires when the plugin stash is populated, so a hypothetical caller who constructs `Config(host_isolation='passthrough')` outside the ini-driven library load arm gets no clamp even though the doctrinal lock says passthrough = serialize.

## Critical Issues

### CR-01: Bare `Config()` in live Proxmox scenario raises ValidationError; ISOL-05 audit comment is wrong

**File:** `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py:67-69` and `:196-200`

**Issue:**
Both call sites read:
```python
# NOTE (ISOL-05 audit, Phase 34): bare Config() in operator-authored scenario.
# Inherits host_isolation='strict' default; scenario does not consume the field.
cfg = Config()
```
This comment is incorrect. `Config.test_code` is declared `test_code: TestCodeConfig = Field(...)` in `config.py:61` — a REQUIRED field with no default. Calling `Config()` with no kwargs raises `pydantic.ValidationError` with `type=missing` at `loc=('test_code',)` BEFORE Pydantic ever evaluates the `host_isolation` default. The "Inherits host_isolation='strict'" claim is unreachable: the constructor does not complete.

- The module-level call at line 69 (`_load_generated_homelab_mcp()`) is caught by the broad `try/except _load_exc` at lines 99-106 and demoted to `pytest.skip(allow_module_level=True)` — so the live scenario is silently skipped even when the operator did everything right (`live_homelab` marker enabled, classes generated). The skip reason includes the bare ValidationError text, masking the real cause.
- The fixture-body call at line 200 (`proxmox_vm_lifecycle_readme`) is NOT wrapped in try/except. On any `live_homelab`-enabled run that reaches fixture setup, this raises `ValidationError` and surfaces as a fixture error, not as the test it was meant to be.

The accompanying ISOL-05 audit document (`34-BARE-CONFIG-AUDIT.md` rows for `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py:67, 196`) classifies these as "Operator-authored test-code scenario" with "2-line inline ISOL-05 audit comment" as the only remediation. The audit failed to verify that the call site even runs. Since the comment now lives inline declaring the call safe, future contributors are actively misled.

**Fix:**
Replace both bare `Config()` calls with a YAML-load or pass `test_code=` explicitly:
```python
# Module-level loader (line 69):
from mcp_test_framework.models import TestCodeConfig
cfg = Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))
# ...or, if the scenario should honor an operator's YAML, route through
# the same stash pattern fixtures.py:108-111 / session.py uses.

# Fixture-body (line 200):
# Same swap. Also: the scenario reads cfg.homelab.proxmox.dogfood_vmid_range,
# which is mode-agnostic — but the Config() construction has never worked
# under the test_code-required regime, so the bug predates Phase 34. Replace
# the misleading "inherits strict default" comment with the truth: this
# constructor needs test_code explicitly, and the scenario does not consume
# host_isolation.
```
Then update `34-BARE-CONFIG-AUDIT.md` to remove the "no remediation needed" classification for these two sites.

### CR-02: `pytest_configure` ValidationError branch has unreachable-but-undefined-`cfg` fall-through path

**File:** `src/mcp_test_framework/_plugin.py:225-249`

**Issue:**
The library-mode YAML-load block:
```python
try:
    cfg = Config(yaml_file=str(path))
except ValidationError as exc:
    from mcp_test_framework.cli import _emit_operator_error_for_validation
    try:
        _emit_operator_error_for_validation(exc, source=str(path))
    except SystemExit:
        pytest.exit(...)

# Relocated black-box guard...
check_black_box()
# Stash for the collection hook to consume.
config._mcp_contracts_config = cfg  # type: ignore[attr-defined]
```
`_emit_operator_error_for_validation` is annotated `-> typing.NoReturn` and raises `typer.Exit` (a `SystemExit` subclass) on every code path. The inner `except SystemExit` re-raises via `pytest.exit`. The defensive shape is sound when every helper actually raises.

But the static control-flow analyzer sees a path where neither raise fires: if `_emit_operator_error_for_validation` ever returns normally (e.g., a future refactor accidentally drops the final `_emit_operator_error` call from one of the branches, or someone adds a new branch that returns), control falls through to `check_black_box()` and then `config._mcp_contracts_config = cfg`, where `cfg` is unbound (NameError). The NameError would then surface during pytest's session-startup instead of the operator-tone ValidationError, which is strictly worse than the original ValidationError.

This is an implicit dependency on `_emit_operator_error_for_validation` always raising. The function does always raise today, but the contract is enforced only by manual code review.

**Fix:**
Make the fall-through impossible by either (a) raising explicitly on the validation-error path:
```python
try:
    cfg = Config(yaml_file=str(path))
except ValidationError as exc:
    from mcp_test_framework.cli import _emit_operator_error_for_validation
    try:
        _emit_operator_error_for_validation(exc, source=str(path))
    except SystemExit:
        pass  # Translate to pytest.exit, below.
    pytest.exit(
        f"mcp_config_file validation failed: {path!s}\n...",
        returncode=2,
    )
    return  # defensive; pytest.exit raises but mypy/static can't see NoReturn
```
or (b) hoist the stash + black-box guard inside the `try` so they never run when validation fails:
```python
try:
    cfg = Config(yaml_file=str(path))
    check_black_box()
    config._mcp_contracts_config = cfg
except ValidationError as exc:
    ...
```
Option (b) is cleaner and removes the implicit ordering coupling.

## Warnings

### WR-01: `_PASSTHROUGH_ALLOWLIST` misnamed after Phase 34 redefined "passthrough"

**File:** `src/mcp_test_framework/_isolation.py:52-65`

**Issue:**
The constant `_PASSTHROUGH_ALLOWLIST` lists exactly the env vars that should pass through the STRICT mode's allowlist (PATH, SYSTEMROOT, LANG, USERNAME). It is used only in `_build_isolated_env` (the strict-mode builder) — never in `_build_passthrough_env`. The pre-Phase-34 codebase used "passthrough" as a term-of-art for "env var that survives the allowlist filter." Phase 34 redefined "passthrough" at the public surface to mean "the entire `os.environ` is passed through unfiltered." After the redefinition, the constant name `_PASSTHROUGH_ALLOWLIST` now reads as "the allowlist used under passthrough mode" — which is the exact opposite of the truth.

A maintainer reading `_build_passthrough_env` and looking for the allowlist will find `_PASSTHROUGH_ALLOWLIST` and assume passthrough mode applies it. Any patch that "consolidates" by referencing the constant from `_build_passthrough_env` reintroduces the strict-mode filter under what is supposed to be unfiltered passthrough — a silent isolation regression.

**Fix:**
Rename the constant to disambiguate from the mode name:
```python
# Was: _PASSTHROUGH_ALLOWLIST
_STRICT_MODE_ENV_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "SYSTEMROOT",
    ...
)
```
Update the one referencing site (`_build_isolated_env`) and add a module-docstring sentence: "The strict-mode allowlist is unrelated to the public `host_isolation='passthrough'` mode despite the legacy variable name." Or, if rename is too invasive, add a same-line comment on the constant declaration: `# NOTE: name predates Phase 34's redefinition of 'passthrough'; this is the STRICT-MODE allowlist.`

### WR-02: `McpTestClient._wrap` hardcodes `_host_isolation='strict'` regardless of the actual fixture mode

**File:** `src/mcp_test_framework/mcp_client.py:166-176`

**Issue:**
The `_wrap` classmethod is used by `fixtures.py:mcp_client` to build an `McpTestClient` around the session-owned `ClientSession`. The fixture already drove the spawn with its own `env=_build_subprocess_env(mcp_config.host_isolation, _isolated_home)`, so the wrapped client's `_host_isolation` attribute is decorative — `__aenter__` is not called on `_wrap`-built instances.

But: the value is stored as `'strict'` regardless of whether the operator's `mcp_config.host_isolation` is strict or passthrough. The comment says "set defensively to keep introspection consistent." This is precisely backwards — any introspector who reads `client._host_isolation` on a `_wrap`-built instance gets a wrong, hard-coded answer that no longer reflects the operator's choice. The "introspection consistent" claim only holds with the SPAWN path, not the actual mode of the session the wrapper is attached to.

This is currently latent (no in-tree consumer reads `_host_isolation` on a `_wrap`-built instance), but Phase 34 explicitly added the attribute and the comment promotes it as "for introspection." Any near-future test or log line that introspects this attribute is silently wrong under passthrough.

**Fix:**
Either:
1. Thread the actual mode through `_wrap`:
```python
@classmethod
def _wrap(
    cls,
    session: ClientSession,
    timeout_seconds: int,
    *,
    server_info: Implementation | None = None,
    host_isolation: Literal['strict', 'passthrough'] = 'strict',
) -> "McpTestClient":
    ...
    instance._host_isolation = host_isolation
    ...
```
And update the one caller in `fixtures.py:466` to pass `host_isolation=mcp_config.host_isolation`.

2. Or, if the attribute is truly never consulted on wrapped instances, delete the `instance._host_isolation = 'strict'` line and the misleading comment. Force a NameError on accidental reads.

### WR-03: xdist clamp fires only when the plugin stash is populated; out-of-band Config(host_isolation='passthrough') escapes the lock

**File:** `src/mcp_test_framework/_plugin.py:259-281`

**Issue:**
The clamp:
```python
stashed_cfg = getattr(config, "_mcp_contracts_config", None)
if (
    stashed_cfg is not None
    and stashed_cfg.host_isolation == "passthrough"
    and getattr(config.option, "numprocesses", 0)
):
    ...
    config.option.numprocesses = 1
    config.option.tx = ["popen"]
```
The stash is populated only inside the `if raw:` ini-arm branch above (line 207-249). If the operator did not set `[tool.pytest.ini_options] mcp_config_file = PATH`, no stash exists — and the clamp never evaluates `host_isolation`. Phase 34's doctrinal lock is "passthrough must serialize." But any caller who:
- ships a custom `conftest.py` that constructs `Config(host_isolation='passthrough')` and uses it without populating the stash, OR
- uses the `mcp_config` fixture's bare-`Config()` fallback path (`fixtures.py:113`) on a future build where the bare default were ever changed to passthrough

would run xdist at full parallelism under passthrough mode. The clamp is one step removed from the actual mode-decision: it depends on the stash being populated, which depends on the ini path.

This is a defense-in-depth issue rather than a current bug (the bare-Config defaults to `strict`, and the CLI run path threads `mcp_config_path=resolved` so its subprocess pytest gets the same ini override). But Phase 34's spec promised the clamp tracks the mode, not the ini.

**Fix:**
Move the clamp to a hook that runs after `mcp_config` is fully resolved, or have it consult `config.getini("mcp_config_file")` directly and short-circuit on absent ini without consulting the stash. Alternatively, document the limitation explicitly in `_plugin.py`:
```python
# NOTE: The clamp depends on the stash, which is populated only when
# mcp_config_file ini is set. Out-of-band Config(host_isolation='passthrough')
# construction without ini-driven load bypasses the clamp. This is acceptable
# in v1.5 because the only operator-supported path to passthrough is via the
# YAML loaded through the ini key.
```

### WR-04: `_session_needs_preflight` `iter_markers` AttributeError is silently swallowed via `getattr`

**File:** `src/mcp_test_framework/fixtures.py:170-181`

**Issue:**
```python
iter_markers = getattr(item, "iter_markers", None)
if iter_markers is not None and any(iter_markers("mcp_contract")):
    return True
```
This guards against test fakes that don't have `iter_markers`. Real pytest `Item` instances always do; the guard exists for SimpleNamespace fakes in the xdist-clamp tests. But: if a future test introduces a `Mock` that returns a non-callable `iter_markers` attribute, the `any(iter_markers("mcp_contract"))` line raises `TypeError`. The guard catches missing attribute but not "attribute exists, isn't callable." Result: the predicate returns False (live preflight skipped) on what should have been a live test.

Lower-severity than the others because no in-tree mock currently triggers it, but the partial-guard pattern invites future bugs.

**Fix:**
Either tighten the guard to `callable(iter_markers)`:
```python
iter_markers = getattr(item, "iter_markers", None)
if callable(iter_markers) and any(iter_markers("mcp_contract")):
    return True
```
Or wrap in a try/except since the predicate's purpose is best-effort marker detection:
```python
try:
    if any(item.iter_markers("mcp_contract")):
        return True
except (AttributeError, TypeError):
    pass
```

### WR-05: `mcp_config` fixture's bare-`Config()` fallback path is broken under v1.5 required-`test_code` regime

**File:** `src/mcp_test_framework/fixtures.py:108-113`

**Issue:**
```python
cfg = getattr(request.session.config, "_mcp_contracts_config", None)
if cfg is not None:
    return cfg
# Audit: stash-miss fallback for framework self-tests that bypass the
# plugin. Returns Config() defaults including host_isolation='strict'.
return Config()
```
Same defect as CR-01: `Config()` with no args raises `ValidationError` for the missing required `test_code` field. The comment "Returns Config() defaults including host_isolation='strict'" is wrong; the bare call cannot return — it raises.

This is unreachable in the current test layout because `_session_needs_preflight` short-circuits before `mcp_config` is requested on framework-only sessions, and operator-live runs populate the stash. But the audit deliverable (`34-BARE-CONFIG-AUDIT.md` line 48) explicitly classifies this site as "Mode-agnostic; framework-self-test fallback" — the audit failed to verify the call site works AT ALL.

This is a WARNING (not CR-) because it's currently dead code; promoting to BLOCKER would require an in-tree trigger.

**Fix:**
Same shape as CR-01: replace with `Config(test_code=TestCodeConfig(generated_root=Path("tests/test_code/_generated")))` or thread through the same `_BOOTSTRAP_TEST_CODE_STUB` constant `cli.py` uses. Then update the audit row.

## Info

### IN-01: `_isolated_home` strict branch's `tempfile.TemporaryDirectory` cleanup error is silently lost

**File:** `src/mcp_test_framework/fixtures.py:397-401`

**Issue:**
```python
async with AsyncExitStack() as stack:
    tmpdir = stack.enter_context(
        tempfile.TemporaryDirectory(prefix="mcp-test-fw-")
    )
    yield Path(tmpdir)
```
On Windows, `TemporaryDirectory.cleanup()` can raise `PermissionError` if any of the subprocess's file handles are still open at teardown. The `AsyncExitStack.__aexit__` will propagate that exception, which under pytest-asyncio's session-scoped finalizer can surface as an unrelated teardown error masking the actual test failure. Pre-Phase-34, the same pattern existed; Phase 34 just relocated the strict branch. Mentioning as info so a future hardening pass can wrap with `ignore_cleanup_errors=True` (Python 3.10+) or a try/finally.

**Fix:**
```python
tmpdir = stack.enter_context(
    tempfile.TemporaryDirectory(
        prefix="mcp-test-fw-",
        ignore_cleanup_errors=True,  # Python 3.10+, Phase 34 was 3.14
    )
)
```

### IN-02: Operator-tone error wording diverges between `cli.py` and `_plugin.py` for the same validation error

**File:** `src/mcp_test_framework/_plugin.py:237-242` vs `src/mcp_test_framework/cli.py:243-401`

**Issue:**
When `mcp_config_file` ini path resolves to an unloadable YAML, the plugin path emits:
```
mcp_config_file validation failed: <path>
next: check the YAML against config.example.yaml or run `mcp-contracts config-init -o config.yaml`
```
The CLI path (via `_emit_operator_error_for_validation`) emits the field-specific three-part block (e.g., `unsupported config version 1`, `unknown host_isolation mode: 'X'`). The plugin path's generic fallback throws away the per-field message that `_emit_operator_error_for_validation` already rendered to stdout — the operator sees BOTH the per-field block (printed by `_emit_operator_error`) AND the plugin's generic "validation failed" line. The second line is redundant noise that contradicts the operator-tone style guide (one summary, not two).

**Fix:**
Have the plugin's `except SystemExit` block re-raise the SystemExit directly instead of overwriting with a generic `pytest.exit`:
```python
except ValidationError as exc:
    from mcp_test_framework.cli import _emit_operator_error_for_validation
    _emit_operator_error_for_validation(exc, source=str(path))
    # _emit_operator_error_for_validation raises typer.Exit (SystemExit
    # subclass); let it propagate. pytest will translate to its own exit.
```
Or convert the SystemExit to a `pytest.exit` with NO additional summary line, just the returncode.

### IN-03: ISOL-05 audit row for `session.py` references "session.py:67" but actual call is at line 76 in committed source

**File:** `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md:48-49` (audit doc — not source)

**Issue:**
The audit row lists `src/mcp_test_framework/test_code/session.py:67` as the bare-Config site. The committed source shows the bare-Config fallback at `session.py:76`. Likely the line shifted during ISOL-05 Plan 34-06 Task 2 implementation (the `request:` param was added and the stash-lookup block was inserted above the bare call). Line-number drift is normal; mentioning as INFO so a future audit refresh can update the line reference and any external citations.

Lower-priority because the file path is unambiguous. But the audit is also cited inline in source-level comments — if any of those embed the line number, they will mislead.

**Fix:**
Either (a) update audit row to `session.py:76`, or (b) remove line number from audit (file:symbol is enough), since line numbers drift across phases.

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
