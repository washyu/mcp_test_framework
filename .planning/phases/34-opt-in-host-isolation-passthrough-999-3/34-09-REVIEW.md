---
phase: 34-opt-in-host-isolation-passthrough-999-3
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/mcp_test_framework/_plugin.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/test_code/session.py
  - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py
  - tests/framework/unit/test_bare_config_construction.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 34-09: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Scope is the gap-closure plan 34-09 (ISOL-05): four bare `Config()` call sites replaced
with explicit `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`,
a CR-02 control-flow hoist in `_plugin.py`, and a new regression-pin test module.

The core change is correct. `Config.test_code` is a REQUIRED field with no default
(`models.py:345` / `config.py:61`), so the old bare `Config()` fallbacks would always have
raised `ValidationError` if reached — the audit comments they replaced ("inherits strict
default") were factually wrong, and the new comments correctly document this. The replacement
`generated_root` value matches the project convention used in `config.example.yaml:43` and
`config.test.yaml:28`.

The CR-02 hoist in `_plugin.py` is sound: `check_black_box()` raises `RuntimeError`
(`_black_box_guard.py:32`), not `ValidationError`, so moving it inside the `try` does not let
the black-box guard be swallowed by `except ValidationError`. The stated fragility it removes
(reliance on `_emit_operator_error_for_validation` being `NoReturn`) is real and now closed.

No blockers. Findings are robustness/quality concerns, the most notable being a hidden coupling
between the new fallback shape and an existing self-test monkeypatch shim.

## Warnings

### WR-01: New fallback shape silently relies on monkeypatch discarding the `test_code` kwarg

**File:** `src/mcp_test_framework/test_code/session.py:79` (and `tests/framework/unit/test_sdet_fixtures.py:158-163`)
**Issue:** The session-fixture self-tests (`test_sdet_fixtures.py`) drive `mcp_session` with
`_mcp_contracts_config=None`, hitting the new fallback line. Those tests depend on
`_install_session_config`'s shim:

```python
def _config_with_yaml(*args, **kwargs):
    if "yaml_file" not in kwargs and not args:
        return _RealConfig(yaml_file=str(yaml_path))
    return _RealConfig(*args, **kwargs)
```

Before 34-09 the fallback was bare `Config()` (no args/kwargs), so the shim's
`not args and "yaml_file" not in kwargs` branch fired cleanly. After 34-09 the fallback is
`Config(test_code=TestCodeConfig(...))` — i.e. called WITH a `test_code` kwarg. The shim still
takes the first branch (yaml_file is absent, no positional args) and therefore **silently
discards the `test_code` kwarg** the production code now passes, substituting
`Config(yaml_file=...)`. The tests stay green only by this coincidence. The coupling is
undocumented at the production call site, and any future shim that forwards kwargs (e.g.
`return _RealConfig(*args, yaml_file=str(yaml_path), **kwargs)`) would raise `TypeError:
multiple values` or pass conflicting sources. This is brittle cross-module coupling between a
production fallback and a test shim's argument-sniffing logic.
**Fix:** Make the dependency explicit. Either (a) update `_config_with_yaml` to forward only
when `yaml_file` is being injected and assert the discarded kwargs are benign, or (b) add a
one-line note at `session.py:77-79` (and the mirror at `fixtures.py:112-114`) that the
self-test shim intentionally ignores the `test_code` kwarg, so a future shim refactor does not
break silently. Prefer (a) — the shim should not blindly drop caller-supplied kwargs:

```python
def _config_with_yaml(*args, **kwargs):
    # Inject yaml_file; drop the fallback's test_code kwarg intentionally
    # (the YAML supplies test_code). Documented coupling with
    # session.py / fixtures.py fallback shape.
    if not args:
        kwargs.pop("test_code", None)
        kwargs.setdefault("yaml_file", str(yaml_path))
    return _RealConfig(*args, **kwargs)
```

### WR-02: Four duplicated fallback literals with no shared constant invite drift

**File:** `src/mcp_test_framework/fixtures.py:114`, `src/mcp_test_framework/test_code/session.py:79`, `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py:72,204`
**Issue:** The literal `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`
is now hand-copied at four sites. The string `"tests/test_code/_generated"` is a magic value
duplicated five times (four call sites + the regression test). If the project convention path
changes, four production/scenario sites and the count-pinned regression test
(`test_bare_config_construction.py:86` expects exactly `2`) must all be updated in lockstep, and
the regression test's text-substring assertions (WR/IN below) will silently constrain the
refactor. There is no single source of truth for "the bootstrap test-code config" even though
`cli.py:63` already defines a `_BOOTSTRAP_TEST_CODE_STUB` for the same purpose.
**Fix:** Reuse the existing bootstrap stub or introduce one shared factory, e.g. a module-level
`_FALLBACK_TEST_CODE = TestCodeConfig(generated_root="tests/test_code/_generated")` (or import
`cli._BOOTSTRAP_TEST_CODE_STUB` where no circular-import barrier exists), and have the fallbacks
reference it. This collapses four literals to one and removes the drift surface.

## Info

### IN-01: Regression test relies on fragile exact-substring/count assertions

**File:** `tests/framework/unit/test_bare_config_construction.py:80,86`
**Issue:** `test_proxmox_scenario_module_has_no_bare_config` asserts
`"cfg = Config()" not in src` and `src.count("TestCodeConfig(generated_root=") == 2`. Both are
whitespace-/spelling-sensitive text scans. A benign refactor — renaming `cfg` to `config`,
removing the space in `cfg=Config()`, or wrapping the construction on two lines so
`TestCodeConfig(generated_root=` no longer appears on one line — would either let a real
regression through (the negative check) or fail spuriously (the count check) without any
behavioral change. The count `2` is also coupled to WR-02's duplication.
**Fix:** Acceptable as a cheap pin given the file cannot be imported (it carries `live_homelab`
markers and loads generated classes at import). If hardening later: parse the module with `ast`
and assert no `Call` to `Config` has zero args, rather than substring scanning.

### IN-02: Stale `sdet`/`gen-sdet-classes` references in the touched scenario file

**File:** `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py:45,56,62,72,83,107`
**Issue:** The file the diff modifies still refers to `cfg.sdet.generated_root` (the attribute is
actually `cfg.test_code.generated_root`, per `config.py:61` / the code on line 73) and instructs
operators to run `gen-sdet-classes` (lines 82, 99). Per CLAUDE.md the public surface is
`test_code` as of v1.4 and `sdet` is a deprecation shim until v1.5; with the date at 2026-05-27
these operator-facing strings are stale. The 34-09 diff did not introduce these, but it edited
the very function (`_load_generated_homelab_mcp`) whose docstring and surrounding comments carry
the stale `sdet` naming, so they were in the editor's hands.
**Fix:** Out of strict 34-09 scope; flag for the v1.5 EOL/scrub pass. When touched, replace
`cfg.sdet.generated_root` -> `cfg.test_code.generated_root` and `gen-sdet-classes` ->
`gen-test-classes` in lines 45/56/62/72/83/107 and the two `_pytest_exit`/`FileNotFoundError`
next-steps.

### IN-03: Typo in regression-test assertion comment

**File:** `tests/framework/unit/test_bare_config_construction.py:79`
**Issue:** Comment reads `# No bare bare bare Config() call:` — the word "bare" is accidentally
repeated three times.
**Fix:** Reduce to `# No bare Config() call:`.

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
