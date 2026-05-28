---
phase: 34-opt-in-host-isolation-passthrough-999-3
verified: 2026-05-28T00:00:00Z
status: passed
score: 5/5 success criteria verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "ISOL-05 partial: bare Config() sites at proxmox module-level, proxmox fixture-body, fixtures.py fallback, session.py fallback now use explicit Config(test_code=TestCodeConfig(generated_root='tests/test_code/_generated')); audit doc corrected to state ValidationError behavior; CR-02 hoist completed; regression pin added"
  gaps_remaining: []
  regressions: []
---

# Phase 34: Opt-in host isolation passthrough (999.3) Verification Report

**Phase Goal:** Operator can opt into `host_isolation: passthrough` so live-UAT and SDET scenarios reach the operator's real credentials, HOME, and keyring — at the explicit cost of xdist parallelism — while every bare `Config()` caller in src/ + tests/ is audited so neither mode silently leaks env across the seam.

**Verified:** 2026-05-28
**Status:** passed
**Re-verification:** Yes — after gap closure by Plan 34-09 (ISOL-05)

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator setting `host_isolation: passthrough` sees the spawned MCP subprocess inherit operator's real HOME/USERPROFILE/TEMP/full env; null-keyring backend NOT injected | VERIFIED | `_isolation.py:111-122` `_build_passthrough_env()` returns literal `dict(os.environ)`. Wired at `fixtures.py:446` and `mcp_client.py:211` via dispatcher. Pinned by `test_isolation_dispatcher.py::test_passthrough_returns_dict_of_os_environ` (passes). Unchanged from prior pass. |
| 2 | Operator leaving unset / setting `strict` sees v1.0–v1.4 always-on isolation behavior unchanged | VERIFIED | `config.py:67` default `Literal['strict', 'passthrough'] = 'strict'`. `_build_isolated_env(isolated_home)` unchanged at `_isolation.py:82-108`. Dispatcher delegates strict-branch verbatim. Pinned by `test_isolation_dispatcher.py::test_strict_delegates_to_build_isolated_env`. Unchanged from prior pass. |
| 3 | `pytest -n 4 + host_isolation: passthrough` sees worker count clamped to 1 with operator-tone banner; `strict` preserves xdist | VERIFIED | `_plugin.py:160` `@pytest.hookimpl(tryfirst=True)`; clamp block at L259-280 mutates BOTH `numprocesses=1` AND `tx=["popen"]`. Banner emitted via `_mcptf_formatwarning` swap, UserWarning category. Three banner phrases pinned by `test_xdist_clamp.py`. Unchanged from prior pass. |
| 4 | Every bare `Config()` site in src/+tests/ identified, documented, routed through the resolved-config seam | VERIFIED | All four former bare `Config()` sites now use explicit `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`: `fixtures.py:114`, `test_code/session.py:79`, `proxmox scenario:72`, `proxmox scenario:204`. No bare `cfg = Config()` matches in src/ or proxmox scenario file. Audit doc corrected: "inherits strict default" count = 0; "RAISES ValidationError" present. CR-02 hoist: `check_black_box()` and stash assignment each appear exactly once inside the `try` block at `_plugin.py:234,236`. Regression pin `test_bare_config_construction.py` passes (3 tests). Framework suite: 788 passed, 0 failed. |
| 5 | Operator reading README + docs/LIBRARY-MODE.md finds the strict-vs-passthrough trade-off documented, safety-delegation doctrine cited, no-keyring-faking lock surfaced, xdist incompatibility called out in same section | VERIFIED | `README.md:465-512` §"Host isolation: strict vs passthrough". `docs/LIBRARY-MODE.md:225-277` §"Host isolation". `docs/ERROR-STYLE.md:78-94` registers `host_isolation literal_error`. `docs/EXTENDING.md` clean of stale "ALWAYS-ON" framing. Unchanged from prior pass. |

**Score:** 5/5 success criteria fully verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/config.py` | Top-level `host_isolation: Literal['strict','passthrough'] = 'strict'` | VERIFIED | Line 67. `Literal` imported from `typing`. |
| `src/mcp_test_framework/_isolation.py` | `_build_passthrough_env()` + dispatcher; legacy `_build_isolated_env` unchanged | VERIFIED | Functions at L111-144. |
| `src/mcp_test_framework/fixtures.py` | `_isolated_home` short-circuits to `None` under passthrough; stash-miss fallback uses explicit construction | VERIFIED | Explicit construction at L114: `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`. No bare `Config()`. |
| `src/mcp_test_framework/mcp_client.py` | `__init__` extended with kw-only `host_isolation`; `__aenter__` gates tempdir alloc | VERIFIED | L117, L124, L198, L211. |
| `src/mcp_test_framework/_plugin.py` | `pytest_configure` decorated `@pytest.hookimpl(tryfirst=True)`; clamp block; stash + black-box guard inside try (CR-02) | VERIFIED | Decorator at L160. Clamp at L251-280. `check_black_box()` at L234 and stash assignment at L236 — both inside the `try` block (L226-251), before the `except ValidationError`. Exactly 1 occurrence of each (no duplicate outside try). |
| `src/mcp_test_framework/cli.py` | `(literal_error, ('host_isolation',))` branch + scaffold emit | VERIFIED | Branch at L344-369; scaffold emits `host_isolation: strict` block. |
| `src/mcp_test_framework/test_code/session.py` | `mcp_session` fixture routes through plugin stash; stash-miss fallback uses explicit construction | VERIFIED | Stash-lookup at L74-76. Explicit fallback at L79: `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`. No bare `Config()`. |
| `tests/framework/unit/test_config.py` | `test_host_isolation_default_is_strict` pin | VERIFIED | Present and passes. |
| `tests/framework/unit/test_error_style.py` | `test_error_style_host_isolation_literal_rejection` pins verbatim phrases | VERIFIED | Passes. |
| `tests/framework/unit/test_isolation_dispatcher.py` | 3 dispatcher contract pins | VERIFIED | All 3 pass. |
| `tests/framework/unit/test_xdist_clamp.py` | Dual-mutation invariant + banner phrases + strict-mode no-op + no-xdist no-op | VERIFIED | All 3 tests pass. |
| `tests/framework/unit/test_bare_config_construction.py` | 3 regression pins for corrected Config construction | VERIFIED | Created by Plan 34-09 Task 4. All 3 pass: `test_bare_config_raises_validation_error`, `test_explicit_construction_succeeds_with_strict_default`, `test_proxmox_scenario_module_has_no_bare_config`. |
| `tests/framework/test_config_init_cli.py` | Round-trip scaffold pin | VERIFIED | Scaffold emits `host_isolation: strict`; parses back with strict default preserved. |
| `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` | Explicit Config construction at both former bare-Config() sites | VERIFIED | `TestCodeConfig(generated_root=` appears exactly 2 times (L72 and L204). `cfg = Config()` appears 0 times. |
| `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md` | Corrected audit rows — raises ValidationError; explicit construction | VERIFIED | "inherits strict default" count = 0. "RAISES ValidationError" present. "Mode-agnostic; framework-self-test fallback" (implying bare Config() works) count = 0. Phase 34-09 correction section at top. Anti-goals section (SEED-022 / no-keyring-faking) retained. |
| `README.md` + `docs/LIBRARY-MODE.md` + `docs/ERROR-STYLE.md` + `docs/EXTENDING.md` | ISOL-06 doc landings | VERIFIED | All four landed. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `fixtures.py:mcp_client` | `_isolation._build_subprocess_env` | dispatcher call | WIRED | `env=_build_subprocess_env(mcp_config.host_isolation, _isolated_home)` |
| `mcp_client.py:__aenter__` | `_isolation._build_subprocess_env` | dispatcher call | WIRED | `env=_build_subprocess_env(self._host_isolation, isolated_home)` |
| `_plugin.py:_discover_tools_live` | `McpTestClient.__init__(host_isolation=...)` | kw arg | WIRED | `host_isolation=cfg.host_isolation` |
| `cli.py:literal_error branch` | `docs/LIBRARY-MODE.md §host-isolation` | next_step pointer | WIRED | Branch's next_step quotes docs/LIBRARY-MODE.md §host-isolation. |
| `_plugin.py:pytest_configure` | xdist NodeManager | `tryfirst=True` hook + both `numprocesses` and `tx` mutations | WIRED | Hook ordering correct; load-bearing dual mutation present. |
| `ERROR-STYLE.md` entry | `test_error_style_host_isolation_literal_rejection` | pin-test reference | WIRED | Three-way lock established. |
| `_plugin.py pytest_configure` | `config._mcp_contracts_config = cfg` | assignment inside try (only on success path, CR-02 closed) | WIRED | `check_black_box()` at L234 and stash assignment at L236 are lexically inside the `try` at L226, before `except ValidationError` at L237. Previously UNCERTAIN — now WIRED. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `_build_passthrough_env` | env dict | `dict(os.environ)` | YES | FLOWING |
| `_build_isolated_env` | env dict | os.environ + isolated_home Path | YES | FLOWING |
| `mcp_client` fixture | env passed to StdioServerParameters | `mcp_config.host_isolation` + `_isolated_home` | YES | FLOWING |
| Passthrough xdist clamp banner | warnings.warn message | hardcoded three-part string | YES | FLOWING |
| `fixtures.py` stash-miss fallback | resolved Config | explicit construction (no longer bare) | YES — constructs without raising | FLOWING |
| `session.py` stash-miss fallback | resolved Config | explicit construction (no longer bare) | YES — constructs without raising | FLOWING |
| `proxmox scenario` Config usage | resolved Config at module-level + fixture-body | explicit construction at both sites | YES — module-level no longer hits wrong-reason skip; fixture-body no longer raises ValidationError | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| New regression pin passes | `uv run pytest tests/framework/unit/test_bare_config_construction.py -q` | 3 passed | PASS |
| Full framework suite passes | `uv run pytest tests/framework/ -q --tb=no` | 788 passed, 2 skipped, 18 deselected, 1 xfailed, 0 failed | PASS |
| No bare `Config()` in src/ | grep for `cfg = Config()` in src/mcp_test_framework/ | 0 matches | PASS |
| No bare `Config()` in proxmox scenario | grep for `cfg = Config()` in proxmox file | 0 matches | PASS |
| Audit doc clean | "inherits strict default" count in audit doc | 0 | PASS |
| Explicit construction works | `Config(test_code=TestCodeConfig(generated_root='tests/test_code/_generated')).host_isolation` | `strict` | PASS |
| CR-02: single check_black_box call inside try | count of `check_black_box()` in `_plugin.py` | 1, lexically inside `try` block at L226 | PASS |
| CR-02: single stash assignment inside try | count of `_mcp_contracts_config = cfg` in `_plugin.py` | 1, lexically inside `try` block at L226 | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| ISOL-01 | 34-01, 34-02, 34-07 | Top-level `host_isolation: strict\|passthrough` Config field with `strict` default | SATISFIED | `config.py:67` field + `cli.py` literal_error branch + scaffold emit + test_host_isolation_default_is_strict pin |
| ISOL-02 | 34-03, 34-04 | `passthrough` mode inherits full env (HOME/USERPROFILE/TEMP/full env vars) | SATISFIED | `_build_passthrough_env() -> dict(os.environ)` wired at both spawn sites; pinned by `test_passthrough_returns_dict_of_os_environ` |
| ISOL-03 | 34-03, 34-04 | `passthrough` does NOT inject null-keyring backend | SATISFIED | `_build_passthrough_env` does not call `_KEYRING_OVERRIDES`; pinned by assertion in dispatcher test |
| ISOL-04 | 34-05 | `passthrough` clamps pytest-xdist to 1 worker with operator-tone banner; strict unchanged | SATISFIED | tryfirst hook + dual mutation (numprocesses + tx) + 3 banner phrases + UserWarning category; 3 unit tests pin all branches |
| ISOL-05 | 34-04, 34-06, 34-09 | Bare `Config()` callers audited and documented; routed through resolved-config seam | SATISFIED | All four bare-Config() sites replaced with explicit construction. Audit doc corrected. CR-02 hoist completed. Regression pin (3 tests) guards against reversion. No bare `Config()` in src/ or proxmox scenario. No false "inherits strict default" claims. |
| ISOL-06 | 34-08 | README + LIBRARY-MODE.md document trade-off, SEED-022, no-keyring-faking, xdist incompatibility | SATISFIED | Both files carry §host-isolation with Proxmox repro, banner verbatim, SEED-022 + no-keyring-faking + xdist callout. ERROR-STYLE.md registers reference message. EXTENDING.md clean of stale phrasing. |

All six requirement IDs accounted for. No orphaned requirements.

### Anti-Patterns Found

(Carried from prior verification for completeness. None are blockers. The former blocker CR-01 and warning WR-05 are resolved by Plan 34-09.)

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/mcp_test_framework/_isolation.py` | 52 | `_PASSTHROUGH_ALLOWLIST` named for legacy term-of-art; Phase 34 redefined "passthrough" | Warning (WR-01) | Naming hazard, not active bug. |
| `src/mcp_test_framework/mcp_client.py` | 172 | `_wrap` classmethod hardcodes `_host_isolation='strict'` regardless of actual operator mode | Warning (WR-02) | Latent; no in-tree consumer reads this. |
| `src/mcp_test_framework/_plugin.py` | 259-280 | xdist clamp guards on stash presence, not on resolved Config directly | Warning (WR-03) | Out-of-band Config() without ini-driven load bypasses clamp. Currently only hypothetical. |
| `src/mcp_test_framework/fixtures.py` | 170-181 | `iter_markers` partial guard — `getattr(item, "iter_markers", None)` catches missing attr but not non-callable | Warning (WR-04) | No in-tree trigger today. |
| `src/mcp_test_framework/fixtures.py` | 397-401 | `TemporaryDirectory` cleanup without `ignore_cleanup_errors=True` | Info (IN-01) | Windows PermissionError at teardown can mask actual test failure. Pre-Phase-34 pattern. |
| `src/mcp_test_framework/_plugin.py` | 237-242 | Operator-tone wording diverges from cli.py wording when ini-path YAML fails validation | Info (IN-02) | Redundant noise. |

WR-01..04 and IN-01..02 are warnings or info — they do not block any success criterion and may defer to Phase 35 or a closure-cleanup pass.

### Human Verification Required

None. All success criteria verified programmatically. The human-verify checkpoint embedded in Plan 34-08 Task 5 was approved by the operator in 34-08-SUMMARY.md.

### Gaps Summary

No gaps. The ONE remaining gap from the prior verification pass (ISOL-05 PARTIAL — audit deliverable contained factually incorrect "inherits strict default" claims and bare `Config()` call sites that would raise ValidationError at runtime) has been fully resolved by Plan 34-09:

- All four bare `Config()` sites replaced with explicit construction.
- Proxmox module-level loader no longer hits a ValidationError-driven wrong-reason `pytest.skip`.
- Proxmox fixture-body no longer raises ValidationError on live_homelab runs.
- `fixtures.py` and `session.py` stash-miss fallbacks now construct correctly.
- `_plugin.py` CR-02 closed: `check_black_box()` and stash assignment inside the `try`.
- `34-BARE-CONFIG-AUDIT.md` corrected: no "inherits strict default" claims, ValidationError behavior documented at all sites.
- Regression pin `test_bare_config_construction.py` (3 tests) guards against reversion.
- Framework suite: 788 passed, 0 failed.

The previously-UNCERTAIN key link (`_plugin.py pytest_configure` → stash assignment on success path only) is now WIRED — the CR-02 hoist makes the control flow explicit and safe without the fragile NoReturn dependency.

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier)_
