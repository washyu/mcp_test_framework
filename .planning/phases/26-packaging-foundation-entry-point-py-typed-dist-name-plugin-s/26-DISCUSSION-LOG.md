# Phase 26: Packaging foundation — Discussion Log

**Captured:** 2026-05-15
**Purpose:** Human-readable record of what was asked, what was selected, and why. Not consumed by downstream agents — they read CONTEXT.md.

---

## Pre-discussion findings (research surfaced before gray-area selection)

- **PyPI conflict:** The name `mcp-test-framework` referenced throughout ROADMAP.md / REQUIREMENTS.md PACK-03 is **already taken** — published 2026-02-07 by user `aryanaidev` (GitHub `aryanjp1/pytest-mcp`), currently at version 0.1.1. Different project (streamlit/UI-driven MCP tool inspector) but adjacent positioning. The original PACK-03 plan ("rename to `mcp-test-framework` with a one-milestone shim under `mvp-test-framework`") cannot land as written.
- **`mvp-test-framework`:** never published — no installed user base to migrate.
- **Implication:** the rename target needs to change; PACK-03 / SC1 wording will need a one-line amendment during planning.

---

## Gray areas selected

User selected all four offered gray areas. Wheel-introspection venue and PyPI publish timing went to Claude's discretion with sensible defaults.

1. Dist-name rename + shim mechanics (PACK-03)
2. Plugin skeleton scope (PACK-01)
3. `contracts/` subpackage stub
4. Fixture collision shim (SC5)

---

## Q1 — Dist-name conflict resolution (pre-gray-area blocker)

**Question:** How to handle the PyPI conflict before discussing the other gray areas?

**Options presented:**
- Pick a different name now
- Try to acquire `mcp-test-framework` via PEP 541 or direct contact
- Defer dist-name decision — Phase 26 ships everything except PACK-03/SC1
- Keep `mvp-test-framework` permanently — drop PACK-03

**User selection:** **Pick a different name now.**

**Rationale captured in conversation:** PEP 541 is slow and rarely succeeds against active packages; deferring would push the publish-readiness decision into a later phase unnecessarily; "mvp-test-framework" is misleading branding for a v1.4 framework.

---

## Q2 — Candidate name pick

**Pre-checked PyPI availability for candidate names:**
- Available: `mcp-contracts`, `mcp-contract-test`, `pytest-mcp-contracts`, `mcp-test-suite`, `mcp-blackbox`, `mcp-conformance`, `mcp-conformance-test`, `pytest-mcp-conformance`, `mcptf`, `mcp-tf`, `mcpcontract`, `pytest-mcp-judge`, `mcp-judges`, `mcp-judging`.
- Taken: `mcp-tester`, `mcp-validate`, `mcp-verify`, `mcp-judge` (Nilavo Boral, 0.1.4, 2025-11-07).

**Options presented:** `mcp-contracts`, `pytest-mcp-contracts`, `mcp-conformance`, `mcp-blackbox`.

**User selection:** **`mcp-contracts`.**

**Rationale:** Dist name aligns with planned `mcp_test_framework.contracts.register()` API surface from SEED-015 / Phase 27. Operator's mental model: "I'm installing the contracts library." Short, easy to type in pyproject.toml dev-deps.

**Side note (user-volunteered):** The original conflict (`aryanjp1/pytest-mcp` on PyPI as `mcp-test-framework`) is an interesting adjacent product — it's the codegen-via-fixture slice of our framework, packaged simply. User flagged "I hadn't thought of doing that" — not in Phase 26 scope but recorded.

---

## Q3 — Importable package name

**Question:** Does the importable Python package name also change to match the new dist?

**Options presented:**
- Keep `mcp_test_framework` (decoupled from dist)
- Rename to `mcp_contracts`
- Rename to `mcp_contracts` + keep one-milestone `mcp_test_framework` shim

**User selection:** **Keep `mcp_test_framework` (Recommended).**

**Rationale:** Phase 25 just locked the import surface (`from mcp_test_framework.test_code import mcp_session`). Renaming the importable package now would reopen that freeze, churn every internal import in `src/`, and require another deprecation shim layer. Decoupling dist name from import name is the conventional Python pattern (Pillow/PIL, beautifulsoup4/bs4) — costs nothing.

---

## Q4 — CLI script name

**Question:** Currently `mcp-test-framework`. Change to match new dist?

**Options presented:**
- Keep `mcp-test-framework`
- Rename to `mcp-contracts`
- Ship both — `mcp-contracts` primary, `mcp-test-framework` as permanent alias

**User selection:** **Rename to `mcp-contracts`.**

**Rationale:** Dist + CLI fully aligned reduces operator confusion. The deprecation-shim cost is small — one extra `[project.scripts]` entry pointing at a wrapper module, removed in v1.5 alongside every other Phase 25/26 shim. Mirrors Phase 25 D-04 (`gen-sdet-classes` → `gen-test-classes`) precedent.

---

## Q5 — Plugin skeleton scope (PACK-01)

**Question:** What does the pytest11 plugin module contain at end of Phase 26?

**Options presented:**
- Pre-declared hooks, no-op bodies
- Bare minimum — empty plugin
- Plugin + framework fixtures already wired

**User selection:** **Pre-declared hooks, no-op bodies (Recommended).**

**Rationale:** Locks the hook surface now without committing to behavior. Phase 27 fills the bodies. Operator sees the framework listed in `pytest --trace-config` (PACK-01 / SC2 passes). The plugin module ALSO declares the renamed framework fixtures + deprecation aliases per SC5 — see Q7.

---

## Q6 — `contracts/` subpackage stub

**Question:** Create `contracts/` subpackage stub now or defer to Phase 27?

**Options presented:**
- Stub now — empty `__init__.py` + `py.typed`
- Stub + explicit `NotImplementedError` on attribute access
- Defer entirely — amend SC3

**User selection:** **Stub now — empty `__init__.py` + `py.typed` (Recommended).**

**Rationale:** SC3 passes as written — `pyright` resolves `from mcp_test_framework.contracts import ...` without missing-stubs noise. Phase 27 fills the module with `register()`. The wheel-introspection gate (PACK-04) can already check that `contracts/py.typed` ships, validating the typed surface end-to-end.

---

## Q7 — Fixture collision shim (SC5)

**Question:** Prefix + alias mechanics?

**Options presented:**
- `mcp_` prefix + separate fixture defs as aliases (mirrors Phase 25 D-01..D-05)
- `mcp_` prefix only, NO unprefixed aliases (amend SC5)
- `mcp_test_framework_` prefix (collision-proof, verbose)

**User selection:** **`mcp_` prefix + separate fixture defs as aliases (Recommended).**

**Rationale:** Mirrors Phase 25 D-01..D-05 deprecation discipline exactly — same warning copy template, same removal milestone (v1.5), same `stacklevel=2` + once-per-process firing. Operator-facing surface is clean (`def test_x(mcp_config): ...`); pre-Phase-26 users on the unprefixed names get a one-milestone soft landing.

**Follow-up decision (D-16) captured in CONTEXT.md:** The three rubric fixtures (`clarity_rubric`, `disambiguation_rubric`, `parameters_rubric`) are NOT in SC5's explicit collision list but ARE generic-enough to collide. Default decision: also prefix to `mcp_*` with deprecation aliases. Planner may defer if scope explodes.

---

## Claude's discretion items (captured for the record)

- **Plugin module file name:** `_plugin.py` (recommended) vs `plugin.py`. Planner picks.
- **Wheel-introspection venue:** `tests/framework/test_wheel_shape.py`, stdlib `zipfile`, runs in framework's normal pytest suite + CI.
- **PyPI publish timing:** Phase 26 ships TestPyPI dry-run + local-install verification only. Production PyPI publish defers to Phase 30. SC1 needs a one-line amendment during planning.
- **hatchling marker-file handling:** planner verifies during research whether `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` already ships `py.typed` markers, or whether `force-include` is needed.
- **`pyright` / `mypy` resolution check (PACK-02):** add a CI step / test that imports operator-imported subpackages from an installed-wheel virtualenv and runs pyright over a fixture file. Planner picks scope.
- **Internal-test fixture migration (D-19):** planner decides whether to migrate framework's own `tests/` off the deprecated unprefixed fixture names in Phase 26 or as a follow-up.

---

## Deferred ideas (logged for future phases)

All deferrals captured in CONTEXT.md `<deferred>` section. Summary:
- Phase 27: `register()` API body, contracts module logic, hook bodies.
- Phase 28: Library-mode config seam, codegen output path defaults.
- Phase 29: `--mcp-domain-ui` reporter plugin.
- Phase 30: Production PyPI publish, README rewrite, carry-forward live UATs, library-mode dogfood.
- v1.5: Coherent removal of every Phase 25 + Phase 26 deprecation shim in one phase.

No scope creep was raised by the user during discussion.

---

*Phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-skeleton*
*Discussion: 2026-05-15*
