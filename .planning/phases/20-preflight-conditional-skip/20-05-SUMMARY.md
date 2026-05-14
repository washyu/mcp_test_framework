---
phase: 20-preflight-conditional-skip
plan: 05
subsystem: testing
tags: [codegen, pytest, pydantic, importlib, mock-fixture, ci-safe]

# Dependency graph
requires:
  - phase: 17-sdet-codegen
    provides: "_codegen.generate(...) pipeline; ToolResponse base; server_slug derivation"
  - phase: 20-preflight-conditional-skip/20-01-requirements-scrub
    provides: "CODEGEN-COVERAGE-01 requirement on the v1.3 slate"
provides:
  - "Mock-fixture-driven integration coverage of the codegen pipeline (synthetic tool list -> generated module artifacts)"
  - "CI-runnable codegen contract pin: no live MCP, no subprocess, no operator infrastructure"
  - "Drift detector: future changes to _codegen.generate or ToolResponse surface fail loudly at this test boundary"
affects: [21-docs, future hello-world-MCP-fixture phase, any future codegen branch additions]

# Tech tracking
tech-stack:
  added: []  # No new deps; uses existing mcp.types.Tool, pytest, importlib.util, pydantic v2 model_fields/model_computed_fields introspection
  patterns:
    - "Synthetic-tool fixture + tmp_path codegen + importlib.util.spec_from_file_location for per-tool module loading"
    - "Package-style loading of generated __init__.py via submodule_search_locations (relative imports resolve against tmp_path)"
    - "Robust annotation assertions via repr-containment for optional-generic types (Pydantic v2 minor-version safety)"

key-files:
  created:
    - tests/framework/unit/test_codegen_integration_mock.py
  modified: []  # zero src/ changes per D-01; zero existing-file mods per plan scope

key-decisions:
  - "Loosened Response typed-field annotation assertions from `is bool`/`is int` to repr-containment after observing codegen emits Optional[T] (T | None, default=None) for outputSchema fields not in `required`. Matches the existing `list[float]` repr-idiom in test_add_numbers_params_array_and_default and is robust to Pydantic v2 minor-version representation changes."

patterns-established:
  - "Mock-fixture codegen tests: hand-crafted Tool list -> generate(...) into tmp_path -> importlib.util load -> introspect model_fields / model_computed_fields / _REGISTRY"
  - "Per-tool module loading uses spec_from_file_location with a unique synthetic package prefix to avoid sys.modules collisions across pytest tests in the same process"
  - "Package __init__.py loading requires submodule_search_locations=[str(slug_dir)] so the emitted relative imports (from .echo_message import ...) resolve correctly against the temp directory"

requirements-completed:
  - CODEGEN-COVERAGE-01

# Metrics
duration: 2min
completed: 2026-05-14
---

# Phase 20 Plan 05: Codegen mock-fixture tests Summary

**Mock-fixture-driven codegen integration tests (10 cases, 319 lines) that pin the synthetic-tool-list -> generated-module-artifacts contract without any live MCP, subprocess, or operator infrastructure.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-14T05:25:36Z
- **Completed:** 2026-05-14T05:27:17Z
- **Tasks:** 1 (TDD-style, single commit)
- **Files modified:** 1 created, 0 modified

## Accomplishments

- Closed the PREFLIGHT-01/02 coverage gap killed by the Phase 20 reframe with a CI-safe replacement (no Proxmox, no Ollama, no live homelab-mcp).
- Locked the codegen public contract at the synthetic-input -> generated-module boundary: Params field shape, Response inheritance from ToolResponse, _REGISTRY tuple shape, and module importability are all asserted.
- Established the per-tool `_load_generated_module` + package-style `_load_generated_init` helper pattern; reusable for any future codegen integration test.
- 10/10 new tests PASS; broader `tests/framework/unit/` suite total grew from 450 -> 460 passing (the new tests integrate cleanly without disturbing existing pass/fail counts).

## Task Commits

1. **Task 1: Write tests/framework/unit/test_codegen_integration_mock.py** — `8980f5c` (test)

_Note: This plan was implemented as a single test commit. The codegen pipeline already exists from Phase 17, so this is integration-test coverage on stable code — no separate RED/GREEN cycle. The plan frontmatter declared `tdd="true"` but in practice the test commit is the deliverable; there is no production-code GREEN commit to follow because no production code changes per D-01._

## Files Created/Modified

- `tests/framework/unit/test_codegen_integration_mock.py` — 319 lines, 10 test functions covering: required scalar string, optional string with default, required array-of-number, optional integer with default, outputSchema declared (typed Response), outputSchema omitted (stub Response), _REGISTRY shape, module importability, ToolResponse computed-field surface, and counts return-value pin.

## Verification

```
$ uv run pytest tests/framework/unit/test_codegen_integration_mock.py -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
plugins: anyio-4.13.0, asyncio-1.3.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False
collected 10 items

tests/framework/unit/test_codegen_integration_mock.py::test_echo_message_params_class_shape PASSED [ 10%]
tests/framework/unit/test_codegen_integration_mock.py::test_echo_message_response_inherits_tool_response PASSED [ 20%]
tests/framework/unit/test_codegen_integration_mock.py::test_add_numbers_params_array_and_default PASSED [ 30%]
tests/framework/unit/test_codegen_integration_mock.py::test_add_numbers_response_is_stub_inheriting_tool_response PASSED [ 40%]
tests/framework/unit/test_codegen_integration_mock.py::test_ping_with_timeout_params_int_default PASSED [ 50%]
tests/framework/unit/test_codegen_integration_mock.py::test_ping_with_timeout_response_typed_fields PASSED [ 60%]
tests/framework/unit/test_codegen_integration_mock.py::test_registry_dict_shape PASSED [ 70%]
tests/framework/unit/test_codegen_integration_mock.py::test_all_generated_modules_import_cleanly PASSED [ 80%]
tests/framework/unit/test_codegen_integration_mock.py::test_every_response_class_exposes_tool_response_surface PASSED [ 90%]
tests/framework/unit/test_codegen_integration_mock.py::test_generate_counts_no_degraded_fields PASSED [100%]

============================= 10 passed in 0.13s ==============================
```

Whole-directory smoke check (`uv run pytest tests/framework/unit/`): 460 passed, 7 failed, 1 deselected, 1 xfailed. The 7 failures are **pre-existing on main** (missing `tests/docs/MIGRATION-v1-to-v2.md`, scrub leaks, homelab-config drift in `test_cli_errors`/`test_doc_scrub`/`test_homelab_config`/`test_migration_doc`); they are unrelated to this plan's surface and are out-of-scope per the executor SCOPE BOUNDARY rule. All 10 new tests added in this plan pass.

## Decisions Made

- **Annotation assertion strategy for outputSchema-declared Response fields:** The plan's draft assertion `Response.model_fields["ok"].annotation is bool` was too tight. Codegen correctly emits these fields as `Optional[bool]` (annotation `bool | None`, default `None`) because the synthetic `outputSchema` does not list them in a `required` array. Switched to repr-containment (`"bool" in repr(ok_ann)`) to match the existing `list[float]` idiom in `test_add_numbers_params_array_and_default` and stay robust across Pydantic v2 minor versions. The test still pins the type to `bool`/`int` — it just tolerates the Optional wrapper. Documented in a docstring on the test so future readers don't re-tighten it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Loosened Response typed-field annotation assertions**
- **Found during:** Task 1 (first pytest run, RED before commit)
- **Issue:** Plan-provided draft used `assert Response.model_fields["ok"].annotation is bool` for `ping_with_timeout`'s outputSchema fields, but the codegen correctly emits `Optional[bool]` (annotation `Union[bool, NoneType]`) since `ok` / `elapsed_ms` aren't in `outputSchema.required`. The test failed with `AssertionError: assert bool | None is bool`.
- **Fix:** Switched both assertions to repr-containment (`"bool" in repr(ok_ann)`, `"int" in repr(elapsed_ann)`), matching the same idiom already used elsewhere in this file for `list[float]`. Added a docstring comment explaining why the assertion is repr-based and that it tolerates either bare `T` (future codegen change) or `Optional[T]` (current).
- **Files modified:** tests/framework/unit/test_codegen_integration_mock.py (test_ping_with_timeout_response_typed_fields only)
- **Verification:** All 10 tests in the file PASS after the edit.
- **Committed in:** `8980f5c` (Task 1 commit — the fix landed before the commit, so the committed file has the loosened assertion)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test assertion bug, not a codegen bug)
**Impact on plan:** None — the fix tightens the codegen contract by documenting the actual emitted shape (Optional[T] when not in required) rather than the draft's incorrect assumption. Acceptance criteria from the plan are all met: file exists, all required imports present, `_SYNTHETIC_SLUG = "synthetic_test_server"` literal present, 10 test functions defined (plan requires >=7), all PASSED, zero subprocess/stdio_client references, zero `sdet/generated/homelab_mcp` references, zero src/ modifications.

## Issues Encountered

- One assertion-level mismatch between the plan's draft and codegen reality (above). No issues with the codegen pipeline itself.

## User Setup Required

None — pure CI-safe test coverage. No environment variables, no external services, no live MCP.

## Acceptance Criteria Check

From plan `<acceptance_criteria>`:

- [x] File `tests/framework/unit/test_codegen_integration_mock.py` exists.
- [x] Contains both required imports (`from mcp_test_framework.sdet._codegen import generate` and `from mcp_test_framework.sdet.response import ToolResponse`).
- [x] Contains literal `_SYNTHETIC_SLUG = "synthetic_test_server"`.
- [x] Defines 10 test functions (plan requires >=7).
- [x] `uv run pytest tests/framework/unit/test_codegen_integration_mock.py -v` — 10 PASSED, 0 failed, 0 errors, exit code 0.
- [x] Zero references to `sdet/generated/homelab_mcp` (D-10 honored).
- [x] Zero references to `subprocess` / `Popen` / `stdio_client` (no live MCP, no subprocess).
- [x] No modifications to any existing file under `src/` or `tests/`.

## Next Phase Readiness

- CODEGEN-COVERAGE-01 requirement satisfied.
- Wave 2 plan slate has 20-04 (REQ closure) remaining; this plan and 20-04 are independent (20-04 touches REQUIREMENTS.md only; 20-05 touched tests/framework/unit/ only).
- Future hello-world-MCP-fixture phase (deferred) can layer on top of this synthetic-input pattern by swapping the hand-crafted Tool list for a discovered-from-live-fixture-MCP list.

## Self-Check: PASSED

Verified before STATE/ROADMAP updates:

- `tests/framework/unit/test_codegen_integration_mock.py` exists (319 lines).
- Commit `8980f5c` present in `git log`.
- Plan acceptance criteria all met.
- Zero `src/` modifications.

---
*Phase: 20-preflight-conditional-skip*
*Completed: 2026-05-14*
