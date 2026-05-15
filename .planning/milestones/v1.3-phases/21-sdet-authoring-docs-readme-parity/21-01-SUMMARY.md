---
phase: 21-sdet-authoring-docs-readme-parity
plan: "01"
subsystem: docs
tags: [docs, sdet, codegen, recipe-absorption, skip-recipe]
dependency_graph:
  requires:
    - "19-04: ProxmoxVmLifecycleState dataclass, module-scope yield fixture pattern, _CpuBumpManageVmParams subclass"
    - "19-04: .planning/recipes/pytest-order.md content (absorbed verbatim)"
    - "20-04: deletion of tests/sdet/test_proxmox_vm_lifecycle.py (doc is now canonical home for the scenario)"
    - "17-xx: gen-sdet-classes CLI command + generated module path convention"
    - "18-xx: mcp_session fixture, tool() factory, ToolCallError class"
  provides:
    - "docs/SDET-AUTHORING.md — single SDET authoring guide covering regen, imports, first test, module-scope fixtures, ordering, skip recipe, failure handling, future CI"
    - "README.md '## Further reading' cross-link to docs/SDET-AUTHORING.md"
  affects:
    - "Plan 21-02 (README '## SDET scenarios' sample) — depends on docs/SDET-AUTHORING.md as the worked-example backbone"
    - "Plan 21-03 (CLAUDE.md persona note) — will reference docs/SDET-AUTHORING.md"
tech_stack:
  added: []
  patterns:
    - "Single new doc per major capability (matches docs/EXTENDING.md, docs/ERROR-STYLE.md, docs/MIGRATION-v1-to-v2.md precedent)"
    - "Recipe absorption from .planning/ artifact into public doc (eliminates broken-link risk on public docs)"
    - "Author-defined _probe() with @pytest.mark.skipif (no framework-side probe primitives — SEED-022)"
key_files:
  created:
    - docs/SDET-AUTHORING.md
  modified:
    - README.md
  deleted: []
decisions:
  - "Failure-handling section uses 'FAIL test_name —' as the rendered example shape instead of the literal ballot-x glyph (zero-emoji constraint)"
  - "Module-scope fixture worked example in '## Sharing state across tests' includes only the create/yield/delete teardown wiring inline; the modify-step test stays in its own block so the inputSchema-bug section's _CpuBumpManageVmParams subclass appears with full ConfigDict-import context"
  - "Skip recipe's third probe shape (MCP capability check) shows the fixture-side pytest.skip() pattern because @pytest.mark.skipif evaluates at collection time — readers learn both shapes and when to reach for each"
  - "Used D-08 'no this-file-used-to-ship-in-tree footnote' verbatim — doc reads as the source of truth, no Phase 20 deletion mention"
metrics:
  duration: "~20min"
  completed: "2026-05-14"
  tasks_completed: 4
  files_created: 1
  files_modified: 1
---

# Phase 21 Plan 01: SDET Authoring Doc + README Further Reading Summary

New `docs/SDET-AUTHORING.md` ships as the canonical SDET authoring guide (460 lines, 10 H2 sections in canonical order), the Phase 19 `pytest-order` cross-file recipe is absorbed verbatim into its `## Ordering across files` section, the conditional skip recipe ships with three `_probe()` shapes plus the operator-domain reason-string convention, and `README.md`'s `## Further reading` cross-links to the new doc — four atomic commits, zero `src/` changes.

## What Was Built

### Task 1 — `docs/SDET-AUTHORING.md` scaffold (commit `38667e0`)

Created the new doc with all 10 H2 sections in plan-mandated order:

1. `## Prerequisites` — configured MCP server, `mcp-test-framework` installed, `tests/sdet/` discovery scope, async-only + strict-mode + `loop_scope="session"` invariant.
2. `## Regenerating codegen` (DOC-SDET-02) — when to regen, the `uv run mcp-test-framework gen-sdet-classes` command, the `src/mcp_test_framework/sdet/generated/<server_slug>/` overwrite scope, the "do not hand-edit" header convention, the mypy/pyright drift signal, the import surface as the stable contract.
3. `## Importing generated Params and Response classes` — literal import lines using the Proxmox tools as the running example; explanation of the `Params` BaseModel surface and the uniform `.raw` / `.data` / `.text` / `.is_error` `Response` attribute set.
4. `## Writing your first test` — single async test calling `tool("create_proxmox_vm").call(params)`, with `@pytest.mark.asyncio(loop_scope="session")` and the explicit warning that bare `@pytest.mark.asyncio` hangs at the first wire `await`.
5. `## Sharing state across tests with a module-scope yield fixture` — `ProxmoxVmLifecycleState` dataclass, `@pytest_asyncio.fixture(scope="module", loop_scope="session")` yield fixture with `try` / `yield state` / `finally` teardown, three file-ordered tests (`test_create_returns_pending_vm`, `test_modify_accepts_cpu_increase`, `test_delete_returns_ok`), explicit note that pytest collects tests in source order without markers.
6. `## The inputSchema workaround (and why the framework does not mask it)` (D-06) — `_CpuBumpManageVmParams(ManageProxmoxVmParams)` subclass with `model_config = ConfigDict(extra="allow")`, three-bullet rationale: upstream homelab-mcp bug, framework refuses to mask it (SEED-022 — `project_framework_primitives_sdet_safety_principle.md`), escape hatch lives in the scenario file.
7. `## Ordering across files` — HTML-comment placeholder for Task 2.
8. `## Skipping when dependencies are unreachable` — HTML-comment placeholder for Task 3.
9. `## Failure handling: ToolCallError` — `.tool` / `.code` / `.message` / `.raw` attribute walkthrough, em-dash render under default output, raw `CallToolResult` under `--debug`, `tests/sdet/conftest.py` JUnit `user_properties` hook described as framework-infra that readers do NOT modify.
10. `## Future: CI-runnable scenarios` (D-12) — one-paragraph forward reference to the planned hello-world MCP fixture; scenarios bound to live infrastructure SKIP in CI today.
11. `## Further reading` — `docs/EXTENDING.md`, `README.md`, generated module path.

One auto-fix during this task: the failure-handling section originally used the literal `✗` ballot-x glyph in the rendered-output example, which tripped the zero-emoji constraint. Replaced with the literal `FAIL` token (renders identically as ASCII-only).

### Task 2 — pytest-order recipe absorbed into `## Ordering across files` (commit `9ebb533`)

Replaced the TASK 2 placeholder with the body of `.planning/recipes/pytest-order.md`, adapted per the plan:

- Dropped the recipe's H1 (`# Cross-file SDET scenario ordering with pytest-order`) — the H2 in the doc already serves.
- Reproduced both prose paragraphs verbatim ("The framework ships no custom cross-file ordering mechanism..." and "If your scenario spans multiple files...").
- Demoted `## Worked example` and `## Why this is not framework-internal` to H3 under the parent H2.
- Reproduced both Python code blocks (`tests/sdet/test_provision.py` and `tests/sdet/test_drive.py`) verbatim with their `python` language tags. The literal phrases `@pytest.mark.order(1)`, `@pytest.mark.order(2)`, `tests/sdet/test_provision.py`, `tests/sdet/test_drive.py` are all present.
- Dropped the third "why-not-internal" bullet (`Per Phase 19 D-11, pytest-order is NOT added to pyproject.toml`) — planning-decision-ID phrasing.
- Reworded the first "why-not-internal" bullet to drop the `tests/sdet/test_proxmox_vm_lifecycle.py` cross-reference (Phase 20 deleted that file). The replacement reads: *"The framework itself ships no SDET scenarios, so the framework's own dependencies never include `pytest-order`."*
- Omitted the `## Phase 21 absorption` section entirely.
- No cross-link to `.planning/recipes/pytest-order.md` from the public doc (D-04).

### Task 3 — Skip recipe filled into `## Skipping when dependencies are unreachable` (commit `a4bec90`)

Replaced the TASK 3 placeholder with:

1. **Opening paragraph** — framework owns no probe primitives; SDET decides what counts as "dependency reachable" via author-defined `_probe()` wired into `@pytest.mark.skipif`. Cites the framework-primitives principle and the in-repo memory file name.
2. **Canonical recipe block** — env-var-gated TCP reachability probe combining `os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST")` + `socket.create_connection((host, 22), timeout=2)` inside a try/except, then a `@pytest.mark.skipif(not _probe(), reason="Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)")` example applied above an async test.
3. **`### Reason-string convention`** subsection (D-10) — reason strings MUST name the dependency in operator-domain terms AND the env var to set. Two examples: the Proxmox reason and `"Ollama judge offline (set MCPTF_OLLAMA_HOST and start the daemon)"`. Rationale: SKIP rows under `_render_per_tool_rows` surface the reason string directly.
4. **`### Other probe shapes`** subsection — two more `_probe()` variants:
   - Env-var-only probe (`return bool(os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST"))`) — for when the wire call itself is cheap.
   - Async MCP capability probe via `mcp_session.list_tools()` — with explicit explanation that this shape does NOT wire into `@pytest.mark.skipif` (marker evaluates at collection time before fixtures), and the practical pattern is `pytest.skip(reason=...)` inside fixture setup. A short fixture-side example accompanies the prose.
5. **Closing pointer** — short sentence pointing forward to `## Future: CI-runnable scenarios` for the planned hello-world MCP fixture.

Three `def _probe(` occurrences in this section (canonical TCP + env-only + async MCP capability), matching the plan's "at least two concrete `_probe()` examples" floor.

### Task 4 — README `## Further reading` link (commit `ae2b7f6`)

Added one bullet to `README.md` line 323, immediately after the `docs/EXTENDING.md` bullet and before the `.planning/PROJECT.md` bullet:

```markdown
- [`docs/SDET-AUTHORING.md`](docs/SDET-AUTHORING.md) -- author SDET scenarios: codegen regen, module-scope fixtures, cross-file ordering, conditional skip recipe.
```

`--` em-dash separator matches the most recent style on the same list. `git diff --stat README.md` shows a single one-line insertion; no other section touched.

## Acceptance Gate Results

| Gate | Expected | Actual | Status |
|------|----------|--------|--------|
| `docs/SDET-AUTHORING.md` exists | true | true | PASS |
| H2 `## Prerequisites` present | 1 | 1 | PASS |
| H2 `## Regenerating codegen` present | 1 | 1 | PASS |
| H2 `## Importing generated Params and Response classes` | 1 | 1 | PASS |
| H2 `## Writing your first test` | 1 | 1 | PASS |
| H2 `## Sharing state across tests with a module-scope yield fixture` | 1 | 1 | PASS |
| H2 `## The inputSchema workaround (and why the framework does not mask it)` | 1 | 1 | PASS |
| H2 `## Ordering across files` (filled in Task 2) | 1 | 1 | PASS |
| H2 `## Skipping when dependencies are unreachable` (filled in Task 3) | 1 | 1 | PASS |
| H2 `## Failure handling: ToolCallError` | 1 | 1 | PASS |
| H2 `## Future: CI-runnable scenarios` | 1 | 1 | PASS |
| H2 `## Further reading` | 1 | 1 | PASS |
| Literal `from mcp_test_framework.sdet.generated.homelab_mcp import` | >= 1 | 4 | PASS |
| Literal `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError` | >= 1 | 1 | PASS |
| Literal `SEED-022` reference | >= 1 | 1 | PASS |
| Literal `project_framework_primitives_sdet_safety_principle` reference | >= 1 | 2 | PASS |
| Literal `_CpuBumpManageVmParams` | >= 1 | 3 | PASS |
| Literal `extra="allow"` | >= 1 | 2 | PASS |
| Literal `@pytest_asyncio.fixture(scope="module", loop_scope="session")` | >= 1 | 1 | PASS |
| Literal `ProxmoxVmLifecycleState` | >= 1 | 2 | PASS |
| Literal `gen-sdet-classes` | >= 1 | 1 | PASS |
| Literal `mypy` | >= 1 | 1 | PASS |
| `<!-- TASK 2 absorbs ... -->` removed | 0 | 0 | PASS |
| `<!-- TASK 3 fills ... -->` removed | 0 | 0 | PASS |
| Literal `@pytest.mark.order(1)` | >= 1 | 1 | PASS |
| Literal `@pytest.mark.order(2)` | >= 1 | 2 | PASS |
| Literal `tests/sdet/test_provision.py` | >= 1 | 1 | PASS |
| Literal `tests/sdet/test_drive.py` | >= 1 | 1 | PASS |
| H3 `### Worked example` (Task 2 demotion) | >= 1 | 1 | PASS |
| H3 `### Why this is not framework-internal` (Task 2 demotion) | >= 1 | 1 | PASS |
| Substring `Phase 21 absorption` (planning chatter must be absent) | 0 | 0 | PASS |
| Substring `.planning/recipes/pytest-order.md` (no cross-link to planning artifact) | 0 | 0 | PASS |
| Substring `D-11` (planning decision ID must be absent) | 0 | 0 | PASS |
| `def _probe(` count (canonical + env-only + async MCP capability) | >= 3 | 3 | PASS |
| Literal `@pytest.mark.skipif` | >= 1 | 3 | PASS |
| Literal `socket.create_connection` | >= 1 | 1 | PASS |
| Literal `os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST")` | >= 1 | 2 | PASS |
| Literal operator-domain reason `Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)` | >= 1 | 2 | PASS |
| H3 `### Reason-string convention` | 1 | 1 | PASS |
| H3 `### Other probe shapes` | 1 | 1 | PASS |
| README link `[\`docs/SDET-AUTHORING.md\`](docs/SDET-AUTHORING.md)` | 1 | 1 | PASS |
| README link appears under `## Further reading` (line 323 > 319) | true | true | PASS |
| Zero `.planning/` path references in docs/SDET-AUTHORING.md body | 0 | 0 | PASS |
| Zero emoji characters in docs/SDET-AUTHORING.md | 0 | 0 | PASS |
| Zero `src/` files modified in this plan | 0 | 0 | PASS |

All 44 acceptance gates passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ballot-x glyph (`✗`) violated zero-emoji constraint**

- **Found during:** Task 1 post-scaffold verification (Python emoji scan over the new doc).
- **Issue:** The `## Failure handling: ToolCallError` section originally illustrated the rendered FAIL row as ``(`✗ test_name — [CODE] message`)``. The `✗` codepoint U+2717 is in the symbols-and-pictographs range that the zero-emoji constraint forbids. The plan's task body did not explicitly call this out — the constraint comes from the plan's overall "no emoji" rule and from CLAUDE.md.
- **Fix:** Replaced ``✗ test_name`` with ``FAIL test_name`` — the exact token the underlying renderer prints in non-color mode, so the example stays faithful to the actual output shape while staying ASCII-clean.
- **Files modified:** `docs/SDET-AUTHORING.md` (one-line edit before the Task 1 commit landed).
- **Commit:** Folded into `38667e0` (Task 1 scaffold commit).

No other deviations. Tasks 2, 3, and 4 executed exactly as written.

## Threat Surface Scan

No new threat surface. The plan is doc-only and the two files modified (`docs/SDET-AUTHORING.md`, `README.md`) ship as static markdown — no runtime path, no input handling, no I/O at runtime, no secrets, no auth, no schema changes. Threat register entries: none. No threat flags raised.

## Stub Check

No stubs introduced. All worked-example code blocks are intentionally complete patterns the reader copies and adapts; the `...` ellipsis inside `test_create_returns_pending_vm` under the skip recipe is a deliberate "fill in your test body" marker, standard for SDET-authoring docs. No placeholder data flows to a UI, no "coming soon" prose, no TODO/FIXME markers.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `38667e0` | `docs(21-01): scaffold docs/SDET-AUTHORING.md with H2 outline + worked example` |
| 2 | `9ebb533` | `docs(21-01): absorb pytest-order recipe into '## Ordering across files'` |
| 3 | `a4bec90` | `docs(21-01): fill skip recipe section with canonical _probe() patterns` |
| 4 | `ae2b7f6` | `docs(21-01): add docs/SDET-AUTHORING.md link to README Further reading` |

## Requirements satisfied

- **DOC-SDET-01** — `docs/SDET-AUTHORING.md` ships with the full authoring walkthrough using the VM-lifecycle scenario as the worked example.
- **DOC-SDET-02** — Codegen regeneration workflow lives as the `## Regenerating codegen` section inside `docs/SDET-AUTHORING.md` (not a separate `CODEGEN.md`).

## Self-Check: PASSED

- FOUND: `docs/SDET-AUTHORING.md` (460 lines, 10 H2 sections + 4 H3 subsections)
- FOUND: README.md updated (one-line insert at line 323 under `## Further reading`)
- FOUND commit: `38667e0` (Task 1 scaffold)
- FOUND commit: `9ebb533` (Task 2 recipe absorption)
- FOUND commit: `a4bec90` (Task 3 skip recipe)
- FOUND commit: `ae2b7f6` (Task 4 README link)
- VERIFIED: zero `src/` files modified across all four commits (`git diff --name-only dca7af5..HEAD -- src/` returns empty)
- VERIFIED: zero `.planning/` path references in `docs/SDET-AUTHORING.md` body
- VERIFIED: zero emoji characters in `docs/SDET-AUTHORING.md`
