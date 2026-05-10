---
phase: 13-config-safety-opt-in-tool-selection
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - docs/MIGRATION-v1-to-v2.md
  - pyproject.toml
  - src/mcp_test_framework/_reporter.py
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/config.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/models.py
  - tests/conftest.py
  - tests/unit/test_cli_errors.py
  - tests/unit/test_config.py
  - tests/unit/test_config_init.py
  - tests/unit/test_error_style.py
  - tests/unit/test_list_tools_format.py
  - tests/unit/test_migration_doc.py
  - tests/unit/test_reporter.py
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 13 implements SAFE-01..07: a CLI-level config resolver, opt-in tool
allowlist, v1 → v2 schema bump, env/.env source removal, `target` field
removal, and a new migration doc. The implementation is internally
consistent and well-tested *at unit scope*, but the design contains
**two critical IPC-boundary regressions** that break opt-in tool
selection during a real `mcp-test-framework run` invocation:

1. The CLI resolver (`cli.py:_load_config`) determines the YAML path and
   passes it as `Config(yaml_file=...)`, but **the resolved path is
   never propagated to the in-process pytest session** spawned by
   `pytest.main()`. Both `tests/conftest.py:pytest_generate_tests` and
   `fixtures.py:config` construct `Config()` with no kwargs, so they
   silently fall back to model defaults (with `tools={}`). Phase 13 D-01
   explicitly removed the `os.environ["MCPTF_CONFIG_FILE"] = str(path)`
   IPC channel that v1.1 used to bridge this gap, but the replacement
   only operates inside the CLI process — not across the pytest.main
   boundary.

2. The reporter (`_reporter.py:pytest_terminal_summary`) re-instantiates
   `Config()` with no kwargs to compose state-a / state-c SKIP rows.
   Same defect, downstream consequence: every discovered tool will be
   reported as state-(a) "not selected in config" regardless of the
   operator's actual `tools:` block.

Both findings are reachable by `mcp-test-framework run` against any
non-trivial config.yaml and reduce the entire opt-in selection feature
to a no-op for selected tools. Unit tests pass because they invoke
`Config(yaml_file=...)` directly, bypassing the pytest entry point.

Several Warning-level findings cover docstring/help-text drift
(MCPTF_CONFIG_FILE wording survives in three locations after its
semantics changed), a fragile `NoReturn` type assertion, a misleading
exception-suppression rationale, and a docstring claim about
`ValidationError` propagation that contradicts the code.

## Critical Issues

### CR-01: Resolved YAML path does not reach the in-process pytest Config()

**File:** `src/mcp_test_framework/cli.py:362-365`
**Issue:**
`run()` calls `_load_config(config)` to validate the YAML, then calls
`pytest.main(...)` to launch the test session. The resolved `Config`
instance is discarded after validation. Inside the spawned pytest
session, both `tests/conftest.py:158` (`pytest_generate_tests`) and
`src/mcp_test_framework/fixtures.py:92` (`config` fixture) construct
`Config()` with no kwargs.

Per Phase 13 D-05/D-06, the env-overlay was fully removed and
`MCPTF_CONFIG_FILE` is no longer a `Config()` source — it is only read
by `_load_config` as a resolver hint. There is also no
auto-discovery fallback inside `Config.settings_customise_sources`:
```python
yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
sources: list[PydanticBaseSettingsSource] = [init_settings]
if yaml_file and Path(yaml_file).is_file():
    sources.append(YamlConfigSettingsSource(...))
```
With `yaml_file=None`, the YAML source is never appended. The
pytest-session `Config()` therefore returns model defaults — most
critically `tools = {}` (Field(default_factory=dict)).

`tests/conftest.py:_resolve_tool_names` then computes
`[name for name in _DISCOVERED_TOOL_NAMES if name in config.tools and not config.tools[name].skip]`,
which evaluates to `[]` for ANY operator config because `config.tools`
is the empty default. `metafunc.parametrize("target_tool", [], ...)`
runs zero contract tests, and `_reporter` reports every discovered tool
as state-(a) "not selected in config" — regardless of whether the
operator carefully enabled `tools.foo.skip: false` in their YAML.

This silently nullifies the entire opt-in tool selection feature for
`mcp-test-framework run`, which is the SAFE-01 phase goal.

Reproduction:
```
$ cat > config.yaml <<EOF
version: 2
ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
mcp_server:
  command: uvx
  args: ["homelab-mcp"]
tools:
  list_registered_servers:
    skip: false
EOF
$ mcp-test-framework run
# Expected: list_registered_servers parametrized as a contract test.
# Actual:   zero contract tests; "list_registered_servers: SKIP — not selected in config"
```

The unit tests do not catch this because `tests/unit/test_config.py`
exclusively exercises `Config(yaml_file=str(path))` (lines 110, 151,
169, 192, 215, 233, 250, 286, 394) — the kwarg form that DOES work in
isolation. There is no test that drives the full `run -> pytest.main
-> fixtures.config` chain with a YAML present.

**Fix:**
Reintroduce a process-local handoff for the resolved path. Options:

(a) Have `_load_config` write the resolved path back to
`os.environ["MCPTF_CONFIG_FILE"]` *for the purpose of the pytest
session only* AND restore the YAML-from-env source on Config (but
ONLY the `MCPTF_CONFIG_FILE` path, not arbitrary scalar values — this
preserves D-05's "env vars don't override config values" without
losing the IPC channel). This is the smallest change.

(b) Add a `./config.yaml` auto-discovery fallback inside
`Config.settings_customise_sources` mirroring the resolver's branch
3. Less explicit, but recovers the common case.

(c) Refactor so the in-process pytest does not instantiate `Config()`
fresh; instead inject the resolver's instance via a pytest plugin
argument or a module-level singleton populated by `run()` before
`pytest.main`.

Minimal patch for (a):
```python
# cli.py:_load_config, near the end of the success branches
import os
os.environ["MCPTF_CONFIG_FILE"] = str(resolved)
return Config(yaml_file=str(resolved))

# config.py:settings_customise_sources, after the init_kwargs pop
yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
if yaml_file is None:
    yaml_file = os.environ.get("MCPTF_CONFIG_FILE")
sources: list[PydanticBaseSettingsSource] = [init_settings]
if yaml_file and Path(yaml_file).is_file():
    sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file)))
```
The SAFE-05 contract ("env vars never override config VALUES") is
preserved because the env var is still only a *path pointer*, not a
value source.

Add an end-to-end regression test that invokes `mcp-test-framework
run --config <path>` with a YAML that lists one tool and asserts a
parametrized test ran (not skipped via state-a).

---

### CR-02: Reporter loads bare Config() and ignores the operator's tools block

**File:** `src/mcp_test_framework/_reporter.py:229-239`
**Issue:**
`pytest_terminal_summary` instantiates `_FwConfig()` with no kwargs
and passes it to `_compose_unparametrized_skips` to render state-c
rows (operator-curated `skip_reason` strings).

```python
from mcp_test_framework.config import Config as _FwConfig
_fw_cfg = _FwConfig()
```

Same root cause as CR-01: under Phase 13 there is no source through
which a bare `Config()` learns about `./config.yaml` or `--config
PATH`. `_fw_cfg.tools` is always `{}` here, so the state-(c) branch in
`_compose_unparametrized_skips`:

```python
cfg_entry = tools_cfg.get(name)
if cfg_entry is not None and getattr(cfg_entry, "skip", False):
    # state (c) -- never reached
    ...
else:
    # state (a) -- always reached
    result[name] = _REASON_NOT_SELECTED
```

is unreachable for real `run` invocations. Every discovered tool, even
ones the operator explicitly skipped with a curated reason, renders as
"not selected in config" instead of the operator's chosen skip_reason.
This breaks D-12's "scan the report and distinguish 'I forgot this
tool' from 'I deliberately skipped this tool'" promise.

Additionally, the `except Exception` rationale at line 232-236 is
factually incorrect:

> under unit-only runs Config() may fail (SAFE-03 fail-loud, no
> config in cwd).

`Config()` with no kwargs does NOT raise SAFE-03 — that error is
emitted by `cli.py:_emit_operator_error` inside `_load_config`. Bare
`Config()` succeeds with model defaults. The defensive `try/except`
hides the silent-defaults bug rather than catching a real exception.

**Fix:**
After CR-01 is fixed (env-var pointer OR cwd autodiscovery inside
`settings_customise_sources`), this site will pick up the operator's
config automatically — no code change needed beyond CR-01. Also tighten
or remove the misleading `except Exception` block: `Config()` should
not be expected to fail in a terminal-summary path.

```python
# After CR-01 fix, this loads the same yaml the test session used.
from mcp_test_framework.config import Config as _FwConfig
_fw_cfg = _FwConfig()
unparam_skips = _compose_unparametrized_skips(_fw_cfg)
```

Add a unit test that pins a non-empty `tools.<name>.skip=True` entry
flowing all the way to a state-(c) row with the operator's
`skip_reason` (not the default fallback). The current
`test_safe_01_compose_state_c_with_curated_reason` only exercises the
helper with a manually constructed `_Cfg` and bypasses the
`pytest_terminal_summary` call site entirely.

## Warnings

### WR-01: --config help text falsely claims it sets MCPTF_CONFIG_FILE

**File:** `src/mcp_test_framework/cli.py:321, 373, 468`
**Issue:**
Three identical typer.Option help strings read:
> "Path to a YAML config overlay (sets MCPTF_CONFIG_FILE)."

After Plan 13-01, `--config` no longer sets `MCPTF_CONFIG_FILE` — it
passes the path as a kwarg to `Config()` and the env var is only read
*to determine the path*, never written. An operator following the
help text would set MCPTF_CONFIG_FILE manually expecting equivalent
behavior, which is now technically supported only as a fallback below
`--config` in precedence.

**Fix:**
Change all three to a phrasing that matches the current resolver:
```python
help="Path to a YAML config (overrides MCPTF_CONFIG_FILE and ./config.yaml autodiscovery)."
```

### WR-02: _load_config docstring claims ValidationError propagates; the code maps it

**File:** `src/mcp_test_framework/cli.py:364`
**Issue:**
The inline comment on the `_load_config(config)` call says:
> "raises typer.Exit(2) on bad path; ValidationError propagates"

But `_load_config` (lines 279-282) wraps the `Config(yaml_file=...)`
call in `try/except ValidationError` and routes through
`_emit_operator_error_for_validation`, which itself raises
`typer.Exit`. `ValidationError` therefore never reaches the caller.
The module docstring header at line 10-11 has the same issue
("_load_config(path) helper sets MCPTF_CONFIG_FILE env var if
--config given" — also obsolete after Plan 13-01).

**Fix:**
Update both comments:
```python
_load_config(config)  # raises typer.Exit(2) on any unrecoverable error
```
And in the module docstring header, replace the obsolete "sets
MCPTF_CONFIG_FILE env var" line with "passes the resolved path as a
`yaml_file` kwarg to Config()".

### WR-03: fixtures.config docstring lists removed env precedence

**File:** `src/mcp_test_framework/fixtures.py:91`
**Issue:**
```python
def config() -> Config:
    """Load env + YAML config once per session (Phase 1 precedence: CLI > env > YAML > default)."""
    return Config()
```

Phase 13 D-05 dropped env from the precedence chain entirely. The
docstring still advertises "env > YAML" which is now false; YAML wins
over env (when YAML loads at all — see CR-01). The bare `Config()`
call here also has the CR-01 silent-defaults problem.

**Fix:**
After applying CR-01, update the docstring to reflect actual Phase 13
precedence:
```python
"""Load YAML config once per session (Phase 13 precedence: init kwarg > YAML > defaults)."""
```

### WR-04: Preflight hint recommends MCPTF_CONFIG_FILE for value injection

**File:** `src/mcp_test_framework/fixtures.py:148-156, 247-253` and `tests/conftest.py:123-129`
**Issue:**
Three nearly identical hint blocks (kept "in sync" by comments) tell
the operator:
> "point MCPTF_CONFIG_FILE at a config.yaml that defines
> mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`)."

This advice is operationally correct (the env var IS a valid
resolver-hint path under Phase 13), but under the current code (see
CR-01) setting MCPTF_CONFIG_FILE from outside the CLI would not be
picked up by the pytest fixtures either — only `cli.py:_load_config`
reads it. The hint will appear to work when the operator runs
`mcp-test-framework run` (because resolver validates the path) but the
actual values won't reach the test fixtures, producing the same
silent-no-tools-selected outcome.

After CR-01 is fixed via the env-var-pointer approach, this hint
becomes accurate and the in-sync comments are correct.

**Fix:**
Resolve CR-01 first; this hint then becomes correct without text
changes. Otherwise, rephrase to point operators at `--config PATH`
which is the only fully-supported channel today.

### WR-05: NoReturn type assertion accepts non-NoReturn return types

**File:** `tests/unit/test_cli_errors.py:67-70`
**Issue:**
```python
sig = typing.get_type_hints(_emit_operator_error)
assert sig.get("return") in (typing.NoReturn, type(None).__class__) or \
       getattr(sig.get("return"), "__name__", "") == "NoReturn"
```

`type(None).__class__` is `<class 'type'>` (the metaclass of `None`'s
type), not `<class 'NoneType'>`. So this assertion really reads "is
the return type NoReturn OR `type` itself OR does its `__name__` end
in 'NoReturn'?". Almost any function with a properly-named class as
return would satisfy this. The test would pass if someone changed the
return annotation to `-> int`, because `int.__class__` is `type` and
the assertion's middle branch matches. The intent (verify NoReturn
annotation) is not enforced.

**Fix:**
```python
sig = typing.get_type_hints(_emit_operator_error)
ret = sig.get("return")
assert ret is typing.NoReturn or getattr(ret, "__name__", "") == "NoReturn", (
    f"return annotation must be NoReturn, got {ret!r}"
)
```

### WR-06: Reporter rationale comment contradicts actual Config() behavior

**File:** `src/mcp_test_framework/_reporter.py:232-236`
**Issue:**
```python
except Exception:  # noqa: BLE001 -- under unit-only runs Config() may
    # fail (SAFE-03 fail-loud, no config in cwd). The terminal-summary
    # path is best-effort; absence of Config means we cannot compose
    # state-a/c rows.
    _fw_cfg = None
```

SAFE-03 fail-loud is implemented in `cli.py:_load_config` — not in
`Config.__init__`. Bare `Config()` never raises a SAFE-03 error; it
returns defaults. The comment misattributes the safeguard and may
mislead a future contributor into believing this except is unreachable
or that they can remove it safely. (See CR-02 for the larger structural
issue.)

**Fix:**
Either remove the try/except (Config() shouldn't fail here) or, if
keeping it for genuine defensiveness, document the real failure modes:
```python
except Exception:  # noqa: BLE001 -- defensive: terminal-summary path
    # must not crash if Config() ever raises. Bare Config() succeeds
    # with defaults today; this guard is belt-and-suspenders.
    _fw_cfg = None
```

## Info

### IN-01: Resolved Config from cli.run() is constructed and discarded

**File:** `src/mcp_test_framework/cli.py:364`
**Issue:**
`_load_config(config)` returns a fully-validated `Config` instance,
but `run` does nothing with the return value — it's used solely for
the validation side-effect. Aside from being slightly wasteful
(double-parsing YAML — `_load_config` once, then pytest's fixture
again under CR-01's eventual fix), it also obscures the dependency
between resolver-success and fixture-Config equivalence.

**Fix:**
After CR-01, consider exposing the resolved Config via the
process-local handoff so `run`'s validation work is reused by the
fixture instead of re-parsed. Minor cleanup, not blocking.

### IN-02: yaml_file=non-existent path silently returns defaults

**File:** `src/mcp_test_framework/config.py:94`
**Issue:**
`if yaml_file and Path(yaml_file).is_file():` silently skips a
non-existent yaml_file path. The unit test
`test_invalid_yaml_path_skips_yaml_overlay` explicitly pins this
behavior, but it means a programmatic caller passing a typo'd path
gets default values rather than an error. The CLI resolver protects
the operator from this by validating path existence first, but the
asymmetry could surprise a downstream library consumer.

**Fix:**
Optionally tighten: raise `FileNotFoundError` when `yaml_file` is
given but doesn't exist, since `_load_config` already pre-validates.
Defensive layering is fine; just consider whether the silent-skip is
worth the surprise.

### IN-03: Docstring for _load_config says "Phase 13 D-01" inside source

**File:** `src/mcp_test_framework/cli.py:191`
**Issue:**
The docstring contains "Phase 13 D-01", "Phase 13 D-03", "Phase 13
D-05". The `BANNED_RE` in `tests/unit/test_cli_errors.py:25` is
applied only to **operator-facing stderr / scaffold output**, not to
source docstrings, so this is allowed by the test suite as designed.
However, project memory `feedback_doc_scrub_planning_artifacts.md`
notes the v1.2 docs scrub initiative — eventually internal D-NN
references in user-readable docstrings may also be cleaned.

**Fix:**
Defer. Not a Phase 13 regression; tracked under the broader v1.2
doc-scrub effort.

### IN-04: Migration doc references --config focus-list_tools.yaml without verifying flow

**File:** `docs/MIGRATION-v1-to-v2.md:28-29`
**Issue:**
> "Single-tool focus is now done via a focus config passed to
> `--config` (e.g. `--config focus-list_tools.yaml`)."

This advice only works once CR-01 is resolved. Until then, operators
following this guidance from a fresh checkout will hit the same
silent-no-tools-selected outcome.

**Fix:**
After CR-01 is resolved, no doc change needed. Otherwise add a caveat
or revise the workflow.

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
