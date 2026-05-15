# Phase 23: Test suite debt cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 23-test-suite-debt-cleanup
**Areas discussed:** Config policy, parents[N] fix, README fix, Scope

---

## Config policy (Cluster A)

Frame: Phase 21.1 RELOC-01 made `Config.sdet` required with no default. Five tests + the production `fixtures.py:101 config` fixture blow up with `pydantic.ValidationError: sdet Field required` when constructing `Config()` bare.

| Option | Description | Selected |
|--------|-------------|----------|
| Tests adapt — push `_SDET_STUB` everywhere | Every Config()-constructing test (and the fixtures.py:101 fallback) explicitly provides an `SdetConfig(generated_root="tests/sdet/_generated")`. Preserves Phase 21.1's 'required, no surprise default' design. ~6 sites changed. | ✓ |
| Reintroduce a framework default for `Config.sdet` | Soften Phase 21.1: `sdet` defaults to `SdetConfig(generated_root="src/mcp_test_framework/sdet/_generated")` (or similar). Tests need no changes. Reopens part of the RELOC-01 decision. | |
| Add a `Config.for_tests()` factory + fixture helper | Test-only construction helper in `tests/conftest.py` that provisions sdet. Framework src stays untouched (SEED-022-friendly); ergonomics localized to tests. Still touches the `fixtures.py:101 config` production fallback. | |

**User's choice:** Tests adapt
**Notes:** RELOC-01 stays intact. Production `fixtures.py:101 config` itself is not modified — the single test that uses it (`test_isolation::test_real_state_unchanged`) gets a test-side override (e.g., `tests/framework/conftest.py` shadow) so `src/` is untouched. Bulk-run env pollution (test passes alone, fails in suite) noted as part of the cluster — planner verifies the fix holds under the full-suite invocation.

---

## parents[N] fix (Cluster B)

Frame: After Phase 15 split tests into `tests/framework/unit/`, two tests (`test_migration_doc.py:14` and `test_cli_errors.py:408`) compute `_repo_root()` as `Path(__file__).resolve().parents[2]`, which now lands on `tests/` instead of repo root.

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical bump — `parents[2]` → `parents[3]` at each site | Two-line surgical fix. Stays in scope; matches roadmap framing of 'debt cleanup'. Brittle to future folder moves but no other folder moves are planned. | ✓ |
| Inline walk-to-pyproject (match `test_doc_scrub.py:16-21`) | Replace each `_repo_root()` with a walk-up looking for `pyproject.toml`. Two files changed, ~5 lines each. Resilient to future restructures; precedent already exists in the codebase. | |
| Shared `repo_root()` helper in `tests/conftest.py` | Introduce one canonical helper, import from both sites + retrofit `test_doc_scrub.py`. Cleanest single source of truth but adds an abstraction during a cleanup phase. | |

**User's choice:** Mechanical bump
**Notes:** Heterogeneous path-resolution styles across `tests/framework/` are acceptable for a debt-cleanup phase. Consolidating to a shared helper is deferred.

---

## README fix (Cluster C)

Frame: README has (1) a bare `$ mcp-test-framework run --explain` on line 104 (no `--config` pairing per Phase 12 D-08), and (2) banned tokens (`Phase N` / `D-NN` / `src/...py:NN`) per `test_readme_exists_and_no_banned_tokens` `BASE_BANNED` regex.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix the README to satisfy the existing rules | Pair line-104 with `--config config.yaml`; scrub any banned tokens (Phase 12 D-10 'semantic rewrite, not regex strip' precedent). Tests stay strict. Matches `project_config_discovery_and_safety` memory: operator-facing examples must show the config flag because discovery silently fails without it. | ✓ |
| Add exemptions to the doc-scrub rules | Allow `--explain` standalone (as a 'flag-demo' example) and/or add a narrow allowlist for any banned tokens. Faster but trades operator clarity for test ergonomics. | |
| Mixed — scrub banned tokens, but exempt pedagogical flag-demos | Tighten the README content (scrub Phase/D-NN refs) but loosen the line-104-style rule to permit invocations whose explicit purpose is demonstrating a flag in isolation. Documented in the test's exemption block. | |

**User's choice:** Fix the README to satisfy the existing rules
**Notes:** Hard-zero policy (mirrors Phase 22 D-04). Planner runs the test to enumerate exact banned-token hits before drafting rewrites — do not guess from grep.

---

## Scope (close-gate definition)

Frame: ROADMAP says "11 fails + 1 error" (Phase 20 UAT snapshot); current state is "12 fails + 1 error". One extra red slipped in since the inventory was taken.

| Option | Description | Selected |
|--------|-------------|----------|
| Pragmatic — fix whatever's red on `main` at phase start | Phase 23 = `tests/framework/` runs green (0 failed / 0 errored, excluding `live_homelab` / `live_ollama` deselections). Doesn't matter if it's 11, 12, or 13; the goal is a green close gate. Aligns with the roadmap's 'v1.3 close ships a green framework suite' framing. | ✓ |
| Strict count — fix only the 11+1 enumerated in Phase 20 UAT | Document the 12th failure as a separately-tracked deferred item; verifier passes once the original inventory is clean even if one new red remains. Preserves audit trail of exactly-what-was-scoped. | |
| Pragmatic + regression-prevention gate | Same as pragmatic, plus add a CI/Makefile-style assertion or doc note so the dev surface can't silently regress to red between v1.3 close and v1.4 open. Risk: scope creep into tooling work that isn't really debt cleanup. | |

**User's choice:** Pragmatic
**Notes:** Verification gate is `uv run pytest tests/framework/ --tb=no -q` exits with `failed == 0 and errored == 0`. Regression-prevention tooling captured as deferred for future hygiene phase.

---

## Claude's Discretion

- **Plan granularity** — one plan per cluster (A / B / C) plus a final close-gate plan, vs. a single sweep plan with cluster-grouped tasks. The three clusters share no fix-site overlap so wave-1 parallel plans are defensible. Planner decides.
- **Conftest seam for D-02** — `tests/framework/conftest.py` fixture override vs. test-local Config construction in `test_isolation.py`. Both keep `src/` untouched. Planner picks the cleanest seam.
- **`tests/framework/conftest.py` creation if absent** — discovery + creation handled by planner.

## Deferred Ideas

- **CI regression gate for `tests/framework/` green-on-merge** — Makefile target / PR-check hook. Scope creep for a debt-cleanup phase; reconsider for v1.4 open or a future hygiene phase.
- **Consolidate `_repo_root()` helpers across `tests/framework/`** — heterogeneous path-resolution styles. Cleanup, not debt; reconsider if path resolution breaks again.
- **`fixtures.py` production-fixture ergonomics** — operators with no `config.yaml` at all currently hit a `ValidationError`. By-design after RELOC-01 + `project_config_discovery_and_safety`; surface for v1.4 operator-DX review if operators trip over it.
- **Env-pollution audit (`MCPTF_*` env-var bleeding between tests)** — if D-03 root-causes a specific test leaking `os.environ` mutations, capture as a follow-up to add test-isolation primitives.
</content>
</invoke>