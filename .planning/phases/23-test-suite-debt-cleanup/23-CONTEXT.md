# Phase 23: Test suite debt cleanup - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Restore `tests/framework/` to a green run so v1.3 closes with no carried-over test debt. The current debt is a cluster of three independent root causes that surfaced during Phase 20 UAT and have accumulated through subsequent phases:

1. **Cluster A — Config v2 / `sdet` required field** (5 fails + 1 error): Phase 21.1 RELOC-01 made `Config.sdet` required with no default. Tests that construct `Config()` with no args, and the production session-scoped `config` fixture in `src/mcp_test_framework/fixtures.py:101`, now blow up with `pydantic.ValidationError: sdet Field required`.
2. **Cluster B — `parents[N]` off-by-one after Phase 15 folder split** (5 fails): `test_migration_doc.py:14` and `test_cli_errors.py:408` use `parents[2]` which resolved to repo-root before the `tests/framework/unit/` split; it now resolves to `tests/`.
3. **Cluster C — README content drift** (2 fails): `test_doc_scrub` flags README line 104 (bare `$ mcp-test-framework run --explain`, no `--config` pairing per Phase 12 D-08 rule) and one or more banned-token hits (`Phase N` / `D-NN` / `src/...py:NN`).

**In scope:**
- All red tests under `tests/framework/` at phase start (currently 12 failed + 1 error against `main`).
- Fix sites in test code (`tests/framework/**`), one production-fixture override seam (test-side, not `src/`-side), and `README.md`.

**Out of scope:**
- Behavioral changes to `src/mcp_test_framework/` framework code (Phase 21.1's "sdet is required" stays).
- New regression-prevention tooling (CI gates, Makefile targets, marker policies). Captured as deferred.
- Phase 24 serializer fix (`tool().call()` `exclude_unset=True`). Independently scoped.
- Reopening Phase 21.1 RELOC-01 or Phase 15 folder-split decisions.
- The `live_homelab` / `live_ollama` deselected suites — Phase 23 verifies the default-run gate, not the live-environment gate.

</domain>

<decisions>
## Implementation Decisions

### Cluster A — Config-construction policy

- **D-01:** Tests adapt; framework does not. Every test that constructs `Config()` with no args adopts the `_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")` pattern already established in `tests/framework/unit/test_homelab_config.py:56-58` and passes it as `Config(sdet=_SDET_STUB)`. Phase 21.1 RELOC-01's "sdet is required, no surprise default" stays intact.
- **D-02:** The production `src/mcp_test_framework/fixtures.py:101 config` fixture is **not** modified. The single test that flows through that fixture (`tests/framework/test_isolation.py::test_real_state_unchanged`) gets a test-side override — either (a) a local fixture in `tests/framework/conftest.py` that shadows `config` with an explicit sdet stub, or (b) the test constructs its own `Config(...)` and ignores the production fixture. Planner picks the cleanest seam; both keep `src/` untouched.
- **D-03:** Bulk-run env pollution is in scope. `test_config_default_homelab` passes alone but fails in the full suite — the planner verifies the fix holds under `uv run pytest tests/framework/` (not just isolated `pytest tests/framework/unit/test_homelab_config.py`). Likely root cause: an upstream test mutates `os.environ` or leaves an `MCPTF_*` var set; fixture override (D-02) may or may not also resolve this depending on root cause.

### Cluster B — `parents[N]` fix strategy

- **D-04:** Mechanical bump only — change `parents[2]` to `parents[3]` at exactly two sites (`tests/framework/unit/test_migration_doc.py:14` `_repo_root()` and `tests/framework/unit/test_cli_errors.py` ~line 408). No shared helper, no walk-to-pyproject refactor. `test_doc_scrub.py:16-21` already uses the walk-up pattern and is left as-is — heterogeneous styles across test files are acceptable during a debt-cleanup phase; consolidation would be a separate refactor.

### Cluster C — README fix

- **D-05:** Fix the README to satisfy the existing rules; do not relax the tests. Line 104 `$ mcp-test-framework run --explain` gets paired with `--config config.yaml` (Phase 12 D-08 rule: operator-facing invocations show the config flag because config-discovery silently fails without it — see `project_config_discovery_and_safety` memory). Banned-token hits are scrubbed via the Phase 12 D-10 "semantic rewrite, not regex strip" precedent — preserve the prose meaning, drop the planning-system anchor.
- **D-06:** The exact banned-token regex enforced by `test_readme_exists_and_no_banned_tokens` is `BASE_BANNED + [r"src/[\w/.]+\.py:\d+"]` (see `tests/framework/unit/test_doc_scrub.py:31-39, 49`). The planner runs the test to enumerate the exact hits before drafting rewrites; do not guess from grep.

### Scope discipline (close-gate definition)

- **D-07:** Phase done = `uv run pytest tests/framework/` exits 0 with no failures and no errors (excluding the `not live_homelab and not live_ollama` deselections baked into `pyproject.toml addopts`). Inventory size floats — the ROADMAP-quoted "11 fails + 1 error" reflects the Phase 20 UAT snapshot; the actual current state is "12 fails + 1 error", and any additional reds that appear during phase execution are in scope. Aligns with the ROADMAP framing "v1.3 close ships a green framework suite".
- **D-08:** Verification gate (planner): after Plan N lands, run `uv run pytest tests/framework/ --tb=no -q` and assert `failed == 0 and errored == 0`. Pre-existing xfailed (currently 2) and skipped (currently 1) tests stay as-is — they are not red.

### Plan-granularity (Claude's Discretion)

- One plan per cluster (A / B / C) plus a final close-gate plan, or a single sweep plan with cluster-grouped tasks. Planner chooses. The three clusters share no fix-site overlap, so wave-1 parallel plans are defensible.
- Whether `tests/framework/conftest.py` exists yet (some test trees don't have one). Planner discovers and creates if needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-23 source-of-truth

- `.planning/ROADMAP.md` §"Phase 23: Test suite debt cleanup" — Goal sentence, scope bullets ("config schema v1→v2 mismatches", "`parents[2]` path resolution breakage", "missing `tests.test_mcp_tool_contract` module + `tests/docs/MIGRATION-v1-to-v2.md` doc", "README line-104 doc drift"), success framing ("v1.3 close ships a green framework suite").
- `.planning/phases/20-preflight-conditional-skip/20-UAT.md` line 36 — original failure-inventory categorization that motivated this phase.

### Decisions inherited from prior phases (do not reopen)

- `.planning/phases/21.1-sdet-generated-output-relocation-make-codegen-output-config-/21.1-CONTEXT.md` RELOC-01 — `Config.sdet` is REQUIRED; no default. D-01 here adapts tests rather than reverse this decision.
- `.planning/phases/15-operator-vs-framework-test-surface-split/` (folder-split phase) — established `tests/framework/unit/` depth that broke `parents[2]`. The split itself is locked; D-04 fixes downstream callers, not the split.
- `.planning/phases/12-doc-persona-foundation/12-CONTEXT.md` D-08 (operator invocations pair with `--config`) and D-10 ("semantic rewrite, not regex strip") — both load-bearing precedents for D-05.

### Test files that define the close gate

- `tests/framework/unit/test_doc_scrub.py:31-49` — `BASE_BANNED` regex list and README rule wording (single source of truth for D-06).
- `tests/framework/unit/test_migration_doc.py` and `tests/framework/unit/test_cli_errors.py:~408` — D-04 mechanical-bump targets.
- `tests/framework/unit/test_homelab_config.py:56-58` — the `_SDET_STUB` pattern D-01 propagates.

### Build-time configuration

- `pyproject.toml` `[tool.pytest.ini_options]` `addopts` — defines the `not live_homelab and not live_ollama` deselection; D-07 close gate is defined against this default.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_SDET_STUB` pattern** (`tests/framework/unit/test_homelab_config.py:56-58`) — already in the codebase; D-01 propagates this to every other `Config()`-constructing test.
- **Walk-to-pyproject `_repo_root()`** (`tests/framework/unit/test_doc_scrub.py:16-21`) — alternative path-resolution pattern. D-04 explicitly does NOT consolidate onto this; left for a future refactor.
- **`pyproject.toml addopts` markers** — the `not live_homelab and not live_ollama` filter is already wired; D-07 leverages it as the default-run gate definition.

### Established Patterns

- **Phase 12 D-08 doc-invocation rule** — operator-facing CLI invocations in README/EXTENDING.md pair with `--config config.yaml`. The `test_doc_invocations_consistently_pair_with_config` test enforces it; D-05 fixes the README to satisfy, not the test to exempt. Reinforced by `project_config_discovery_and_safety` user memory.
- **Phase 12 D-10 semantic-rewrite rule** — banned-token scrubs preserve prose meaning and cite surviving doc anchors; do not regex-strip. Applies to D-05 banned-token hits in README.
- **Phase 22 D-04 hard-zero allowlist policy** — no `# noqa` style exemptions for banned tokens. D-05 follows the same posture (no test-side allowlist add).

### Integration Points

- **`tests/framework/test_isolation.py::test_real_state_unchanged`** — only test that exercises the production `src/mcp_test_framework/fixtures.py:101 config` fixture in the red set. The conftest seam created by D-02 lives one level above this file (`tests/framework/conftest.py`).
- **`README.md` line 104** — single bare-invocation hit. Likely small surrounding context to keep intact.
- **`tests/framework/unit/test_doc_scrub.py:42-51`** — `_scan()` and `test_readme_exists_and_no_banned_tokens` are the close-gate for D-05 banned-token scrub; run the test to enumerate hits before rewriting.

</code_context>

<specifics>
## Specific Ideas

- The 12-vs-11 delta (one extra red since Phase 20 UAT) is most likely `test_call_arguments_forwarded_to_call_tool_via_asyncmock` in `tests/framework/test_tool_config.py` — same Cluster A root cause, just hadn't surfaced in the Phase 20 snapshot. Confirmed when the planner enumerates hits.
- `tests/docs/MIGRATION-v1-to-v2.md` (mentioned in ROADMAP scope bullet) is a **misread of the failure** — the doc actually exists at `docs/MIGRATION-v1-to-v2.md`. The test fails because `parents[2]` resolves under `tests/`, making the test look for `tests/docs/...`. Fixing D-04 makes the doc resolution work; no doc needs to be authored.
- "`tests.test_mcp_tool_contract` module" reference in the ROADMAP scope bullet is stale — no current red failure mentions this module name. Planner verifies during enumeration; likely already resolved by earlier phases or never reproduced post-Phase 20.

</specifics>

<deferred>
## Deferred Ideas

- **CI regression gate for `tests/framework/` green-on-merge** — A Makefile target or PR-check hook that asserts `tests/framework/` is green. Useful but adds tooling work to a debt-cleanup phase; scope creep. Capture for a future hygiene phase or v1.4 open.
- **Consolidate `_repo_root()` helpers across `tests/framework/`** — `test_doc_scrub.py` uses walk-up-to-pyproject; D-04 sites use `parents[N]`. Heterogeneous; consolidating to a shared helper in `tests/framework/conftest.py` is a legitimate cleanup but separate from this phase's "green gate" goal. Reconsider if path resolution breaks again.
- **`fixtures.py` production-fixture ergonomics** — The fact that `fixtures.py:101 config` blows up under bare `Config()` is by-design after RELOC-01, but it does mean the framework can't be used by an operator with no `config.yaml` at all. The "fail-loud on missing config" decision is from `project_config_discovery_and_safety` memory and is intentional. Surface for v1.4 operator-DX review if operators trip over it.
- **Env-pollution audit (`MCPTF_*` env-var bleeding between tests)** — If D-03 root-causes a specific test leaking `os.environ` mutations, capture as a follow-up to add test isolation primitives (monkeypatch-only enforcement, env snapshot/restore conftest). Out of scope for the green-gate run.

</deferred>

---

*Phase: 23-test-suite-debt-cleanup*
*Context gathered: 2026-05-14*
</content>
</invoke>