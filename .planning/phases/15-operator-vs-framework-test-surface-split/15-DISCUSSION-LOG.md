# Phase 15: Operator vs framework test surface split - Discussion Log

**Date:** 2026-05-11
**Audience:** Humans (audit / retrospective). Not consumed by downstream agents — they read CONTEXT.md.

---

## Areas Selected

User chose all four gray areas:
1. Opt-in flag spelling
2. Conftest split strategy
3. Ambiguous test classification
4. `--raw` semantics post-split

---

## Q1 — Opt-in flag spelling (SURFACE-02)

**Options presented:**
- `--with-framework` *(Recommended)* — matches REQUIREMENTS.md verbatim, reads naturally
- `--all` — shortest, but ambiguous as more scopes are added
- `--include-framework` — verbose, no clear win over `--with-framework`
- `--scope=contract|framework|all` — composable, future-proof, but over-engineered for two scopes

**User selection:** `--with-framework`

**Locked in CONTEXT.md as:** D-01

---

## Q2 — Opt-in flag effect (append vs replace)

**Options presented:**
- **Append (both)** *(Recommended)* — `--with-framework` collects contract + framework
- **Replace (framework only)** — collects only framework

**User selection:** Append (both)

**Locked in CONTEXT.md as:** D-02 / D-03

---

## Q3 — Conftest split strategy

**Options presented:**
- **Keep top-level as-is** *(Recommended)* — pytest_generate_tests is no-op for non-target_tool tests, black-box guard applies to both subtrees
- **Split** — framework guard top-level, discovery scoped to `tests/contract/`
- **Full split** — delete top-level, two scoped conftests

**User selection:** Keep top-level as-is

**Locked in CONTEXT.md as:** D-04 / D-05

---

## Q4 — Classification of `tests/smoke/`

**Options presented:**
- `tests/framework/smoke/` *(Recommended)* — smoke tests hardcode homelab-mcp + live Ollama, conceptually framework reachability checks
- `tests/contract/smoke/` — they touch live MCP/Ollama like contract tests, but hardcode homelab-mcp specifics
- Delete or skip-by-default — defer audit to separate phase

**User selection:** `tests/framework/smoke/`

**Locked in CONTEXT.md as:** D-08

---

## Q5 — Classification of `test_runner_live_smoke.py`

**Options presented:**
- `tests/framework/` *(Recommended)* — tests the wrapper itself (self-test)
- `tests/contract/` — touches live external systems

**User selection:** `tests/framework/`

**Locked in CONTEXT.md as:** D-09

---

## Q6 — `--raw` scope post-split

**Options presented:**
- **`--raw` follows operator default (`tests/contract/` only)** *(Recommended)* — three independent axes: scope (`--with-framework`), rendering (`--raw`), verbosity (`-q`/`--debug`)
- **`--raw` means `tests/` (both)** — preserves Phase 14 D-11 wording verbatim, but contradicts the operator-noise-reduction goal of Phase 15
- **`--raw` collects whatever the wrapper would collect** — functionally identical to option 1, more wording to maintain

**User selection:** `--raw` follows operator default (`tests/contract/` only)

**Locked in CONTEXT.md as:** D-11 / D-12

---

## Claude's Discretion Items

User did not lock these; they remain planner judgment calls (captured in CONTEXT.md §"Claude's Discretion"):

- Plan ordering within Phase 15
- Whether to hoist `test_banned_imports.py` out of `tests/framework/unit/` for SURFACE-04 path literalism
- README / docs anchor updates (pending grep verification)
- Whether to refresh `tests/conftest.py` module docstring
- How strictly to interpret SURFACE-04's literal path

---

## Deferred Ideas

- Smoke-test audit / prune (separate phase or Phase 11 / SEED-013 territory)
- File renaming for clarity (history preservation comes first per SURFACE-03)
- CI workflow files (no `.github/workflows/` in repo)
- Phase 16 owns pre-run digest polish, `--explain`, N=70 readability

---

## Notes

- No scope creep redirects this session — every selected gray area was within SURFACE-01..04.
- All 4 areas resolved in single-question turns; no follow-up rounds needed.
- Phase 14's deferred §"Cross-phase tasks (Phase 15)" pre-armed the seam (`_runner.py:95` single-string flip) — Phase 15 is mostly mechanical.
