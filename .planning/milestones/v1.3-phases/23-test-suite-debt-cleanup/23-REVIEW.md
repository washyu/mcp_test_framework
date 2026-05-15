---
phase: 23-test-suite-debt-cleanup
reviewed: 2026-05-15T05:00:48Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - README.md
  - tests/framework/conftest.py
  - tests/framework/smoke/test_smoke_homelab_mcp.py
  - tests/framework/smoke/test_smoke_ollama_judge.py
  - tests/framework/test_config_init_cli.py
  - tests/framework/test_isolation.py
  - tests/framework/test_tool_config.py
  - tests/framework/unit/test_cli_errors.py
  - tests/framework/unit/test_migration_doc.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-05-15T05:00:48Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 23 closes pre-existing red tests in `tests/framework/` via three mechanical
clusters and a recovery commit. Mechanically the changes are correct: the
`_SDET_STUB` pattern is consistently applied, `parents[3]` calculations resolve
to the repo root, the contract import is retargeted to `tests.contract.*`, and
`tests/framework/test_isolation.py` gains the `live_homelab` marker so the
default addopts filter deselects it.

The new `tests/framework/conftest.py` `config`-fixture override is the
load-bearing addition — it shadows the production session-scoped fixture so
framework-only tests pick up a stub `SdetConfig` instead of crashing in
Pydantic. Two structural concerns surface around that override (it discards
`MCPTF_CONFIG_FILE` for `live_homelab` smoke/isolation tests under
`tests/framework/`, and the `--config` flag has no effect there either). One
attribute-access bug (`cfg.target.tool_name`) survives in the smoke test that
Phase 23 actively edited — `target` was removed from `Config` in Phase 13, so
that smoke test stays red the moment `live_homelab` is selected. The remaining
findings are doc / code-smell.

No critical issues (no security, data-loss, or destructive-mutation defects in
scope).

## Warnings

### WR-01: Smoke test references attribute that no longer exists on `Config`

**File:** `tests/framework/smoke/test_smoke_homelab_mcp.py:58, 75`
**Issue:** Both test bodies access `cfg.target.tool_name`, but `Config` has no
`target` field — Phase 13's v2-schema rework removed it (`extra="forbid"`,
documented in `tests/framework/test_tool_config.py:248-256`). When `pytest -m
live_homelab` runs (the explicit opt-in path documented in the module
docstring), both tests will fail with `AttributeError: 'Config' object has no
attribute 'target'` long before reaching the SC#1/SC#2 assertions they are
supposed to prove.

This is in scope for Phase 23 — the file was edited in Cluster A (the
`_SDET_STUB` insertion) and the phase title is "Test suite debt cleanup". The
mechanical `_SDET_STUB` patch fixed the bare-`Config()` red but left a second
red one line below it.

**Fix:** Pin the target tool name to a literal (matches the rest of the
framework's "operator config drives target" model post Phase 13) and drop
`cfg.target.*`:
```python
# Module-level constant near _SDET_STUB:
_TARGET_TOOL_NAME = "list_keyring_credentials"  # pin to the v1.1 surface

# In test_raw_stdio_lists_target_tool:
target = _TARGET_TOOL_NAME

# In test_wrapper_call_tool_returns_non_error_with_content:
result = await client.call_tool(_TARGET_TOOL_NAME, {})
```

### WR-02: `tests/framework/conftest.py` override silently drops `MCPTF_CONFIG_FILE` overlay

**File:** `tests/framework/conftest.py:22-24`
**Issue:** The override returns `Config(sdet=_SDET_STUB)` unconditionally. In
the production fixture at `src/mcp_test_framework/fixtures.py:89-101`, bare
`Config()` consults `MCPTF_CONFIG_FILE` via `settings_customise_sources` so an
operator-resolved YAML overlays the defaults. The override drops that pathway
because the stub `sdet` kwarg supplies the field that was triggering the
Pydantic error, but the YAML loader still runs — and `init_settings` wins over
the YAML source in `Config.settings_customise_sources` (line 114-118), so any
operator who sets `MCPTF_CONFIG_FILE` while running `tests/framework/...` will
silently get default `mcp_server.command="homelab-mcp"`, default
`ollama.base_url`, default `tools={}`, etc. — not the values from their YAML.

This bites the two `live_homelab` test files under `tests/framework/`
(`test_isolation.py` after WR-04 and the two smoke tests) and any future
framework test that requests the `config` fixture.

**Fix:** Mirror the production fixture's pattern but layer the stub atop the
overlay (let YAML supply `sdet` when present, fall back to the stub when not):
```python
@pytest.fixture(scope="session")
def config() -> Config:
    try:
        return Config()  # picks up MCPTF_CONFIG_FILE if set
    except ValidationError:
        # Operator's YAML didn't supply sdet (or no YAML present);
        # framework tests don't exercise SDET codegen, so a stub is safe.
        return Config(sdet=_SDET_STUB)
```
Or, if the explicit "framework tests never honour overlay" stance is
intentional, document that decision in the module docstring so future
operators don't debug missing overlay values for an hour.

### WR-03: `tests/framework/conftest.py` override ignores `--config` (CLI) values

**File:** `tests/framework/conftest.py:22-24`
**Issue:** Same shape as WR-02 but for the explicit `mcp-test-framework run
--with-framework --config /path/to/yaml` path. The CLI sets
`MCPTF_CONFIG_FILE` (cli.py:299) before launching the inner pytest session,
and the production `config` fixture honours it. The override here returns a
stub regardless of the operator's `--config` flag, which means the documented
`--with-framework` flag (README:50-54) yields a different `config` value
inside `tests/framework/` than inside `tests/contract/` — silently. Pair with
the project memory about `.env beats --config` precedence-confusion bugs; this
is a symmetric defect.

**Fix:** Same as WR-02. If the override is kept as-is, `tests/framework/`
tests effectively run under hard-coded defaults whenever they request the
fixture — surface that explicitly in the module docstring (and in
`docs/SDET-AUTHORING.md` if `--with-framework` is supposed to inherit overlay
values).

### WR-04: `_session_needs_preflight` does not include `tests/framework/` live tests

**File:** `tests/framework/test_isolation.py:52-55` (in conjunction with
`src/mcp_test_framework/fixtures.py:117`)
**Issue:** Phase 23 added `pytest.mark.live_homelab` to `test_isolation.py` so
the default addopts filter deselects it. Good. But `_session_needs_preflight`
(`fixtures.py:117`) only returns True when an item is under `tests/contract/`
or `tests/sdet/`. `tests/framework/test_isolation.py` is under neither, so the
autouse `_preflight` gate never fires when an operator opts in via `pytest -m
live_homelab`. The test then proceeds straight to the `mcp_client` fixture's
subprocess spawn and either crashes hard or hangs on the MCP handshake when
`homelab-mcp` is not on PATH — instead of the operator-tone `pytest.exit(...,
returncode=2)` the preflight gate is supposed to render.

Same applies to the two `tests/framework/smoke/test_smoke_*` files. These are
all `live_homelab`/`live_ollama`-marked under `tests/framework/`.

This is partially pre-existing but Phase 23 actively re-introduced the
exposure by adding the `live_homelab` marker without extending
`_LIVE_PREFIXES`.

**Fix:** Either extend `_LIVE_PREFIXES` to include the live-marked subtrees:
```python
# fixtures.py:117
_LIVE_PREFIXES: tuple[str, ...] = (
    "tests/contract/",
    "tests/sdet/",
    "tests/framework/smoke/",
    "tests/framework/test_isolation.py",
)
```
Or switch the predicate from a path-prefix check to a marker check (any item
carrying `live_homelab` or `live_ollama`):
```python
def _session_needs_preflight(request) -> bool:
    items = getattr(request.session, "items", []) or []
    return any(
        item.get_closest_marker("live_homelab")
        or item.get_closest_marker("live_ollama")
        for item in items
    )
```
The marker-based version is the more durable fix and removes the path-list
maintenance cost.

## Info

### IN-01: Duplicate `_SDET_STUB` literal across files invites drift

**File:** `tests/framework/conftest.py:19`,
`tests/framework/smoke/test_smoke_homelab_mcp.py:42`,
`tests/framework/test_tool_config.py:38`,
`tests/framework/test_config_init_cli.py:135`,
`tests/framework/smoke/test_smoke_ollama_judge.py:83`
**Issue:** The literal `SdetConfig(generated_root="tests/sdet/_generated")`
now appears in five places (the conftest stub plus four sites that still
inline it). The CONTEXT.md commentary in each file points back to
`tests/framework/unit/test_homelab_config.py:51-58` as the "locked source",
which is a sixth copy. If the recommended `generated_root` convention ever
changes, all six sites must update in lockstep — a classic drift hazard.

**Fix:** Promote a single helper module (e.g. `tests/_helpers/sdet_stub.py`
or extend the existing `tests/framework/conftest.py` to export `_SDET_STUB`
as `SDET_STUB` for re-use):
```python
# tests/framework/conftest.py
SDET_STUB: Final = SdetConfig(generated_root="tests/sdet/_generated")

@pytest.fixture(scope="session")
def config() -> Config:
    return Config(sdet=SDET_STUB)
```
Other files import `from tests.framework.conftest import SDET_STUB` (or
better, a dedicated helper module to avoid importing-from-conftest patterns).
Low priority — this is a maintainability concern, not a correctness one.

### IN-02: Phase-ID leakage in test docstrings violates project banned-token discipline

**File:** `tests/framework/conftest.py:1, 5, 11`,
`tests/framework/smoke/test_smoke_homelab_mcp.py:39-41`,
`tests/framework/smoke/test_smoke_ollama_judge.py:80-82`,
`tests/framework/test_config_init_cli.py:131-134`,
`tests/framework/test_tool_config.py:35-38, 56-62, 124-133, 148-156`,
`tests/framework/unit/test_cli_errors.py:91-100, 360-371`
**Issue:** Test docstrings carry "Phase 21.1 RELOC-01", "Phase 23 D-01
(Cluster A) Pattern S1", "Plan 14-05", "TOOLCFG-04", "SAFE-06", etc. — the
exact tokens `tests/framework/unit/test_no_planning_ids_in_src.py` and the
docs-scrub tests forbid in operator-facing surfaces. These are test files
(not operator-facing), so the banned-token tests do not flag them, but the
project memory notes (`project_doc_scrub_planning_artifacts.md`) call out
that planning IDs date the codebase and require future scrubs.

This is a long-standing convention question, not a Phase 23 regression — the
phase merely added more tokens of the same flavour. Worth flagging only so
the eventual scrub knows the test tree has accreted ~15 new planning-ID
references in this single phase.

**Fix:** Optional. If the project decides test-tree planning IDs are
acceptable (they survive in git history regardless), close as Won't-Fix. If
they should match the operator-facing scrub policy, replace each "Phase X
D-Y" preamble with a one-sentence functional description:
```python
# Before:
# Phase 23 D-01 (Cluster A) Pattern S1: Config.sdet is REQUIRED post Phase
# 21.1 RELOC-01. ...

# After:
# Config.sdet is required (no default), so bare Config() raises
# ValidationError; supply a stub so the test exercises the framework
# rather than the missing-field error.
```

### IN-03: README still has trailing whitespace / em-dash mix in narrative blocks

**File:** `README.md:79, 83, 92, 95, 116, 132, 200, 234, 236, 238, 241, 243`
(non-exhaustive)
**Issue:** README mixes em-dashes (`—`) with double-hyphens (`--`) inconsistently
within the same document. The Phase 23 README scrub touched only the
`--config config.yaml` pairing (line 104) and the comment line 274. The
ERROR-STYLE.md / `test_migration_doc_uses_ascii_dashes_not_emdash` discipline
applies to operator-facing error messages, not the README — but the README is
also operator-facing, so the inconsistency reads as accidental.

**Fix:** Optional / out-of-scope for Phase 23. Defer to a v1.3 doc-style
sweep. Flagged here only because the diff touched README and the
inconsistency was visible in the immediate vicinity.

---

_Reviewed: 2026-05-15T05:00:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
