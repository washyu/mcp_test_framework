# Phase 27: `register()` API + contracts sub-package + test extraction (LIB) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 27-register-api-contracts-sub-package-test-extraction-lib
**Areas discussed:** register() kwarg surface (pivoted), tools kwarg shape (mooted by pivot), judge kwarg form (mooted by pivot), test extraction + nodeid shape, env var fate, failure modes

---

## Area 1: register() kwarg surface — PIVOTED MID-DISCUSSION

| Option | Description | Selected |
|---|---|---|
| Lean (server argv + tools + split judge_*) | Minimum LIB-01..08 satisfaction; defer config=/config_file= to v1.5 | |
| Lean + config= + config_file= | Add escape hatches Phase 30 + Phase 28 reference; behavior stubbed | (proposed; user said "not sure") |
| Comprehensive (every Config field as kwarg) | Maximum kwarg surface, no Config() construction needed | |
| Lean + config= only | Minimal v1.4 footprint; config_file= waits until Phase 28 | |

**User's choice:** Pivoted away from `register()` entirely. The discussion exposed that pytest already has five established config surfaces (`pyproject.toml [tool.pytest.ini_options]`, `pytest.ini`, `tox.ini`, `setup.cfg`, `addoption`/`addini`) — operator's question was essentially "can't we just point at the YAML via one of these?"

**Notes:** User explicitly stated dislike of CLI args ("messy... cumbersome... need short args... huge help files"). Pivot driver was the vibe-coded-operator persona (memory: `project_vibe_coded_persona`) — simpler indirection fits a non-Python-expert operator better than a Python registration API. Claude recommended Approach A (pyproject ini line pointing at `config.yaml`); user agreed: "lets just do a". Major downstream impact on REQUIREMENTS.md LIB-01..08 + CFG-01..02 + ROADMAP.md milestone goal text + Phase 28 + Phase 30 — captured in CONTEXT.md `<downstream_impact>` section.

---

## Area 2: tools kwarg shape — MOOTED BY PIVOT

| Option | Description | Selected |
|---|---|---|
| list[str] of names only | Per-tool call_arguments via separate mechanism | |
| dict[str, ToolOptions] | Matches today's v1.3 YAML registry shape | (effective — YAML reuses) |
| Both forms accepted | list[str] simple case, dict for advanced | |

**User's choice:** Mooted. With the pivot to YAML-driven config, today's `tools: dict[str, ToolOptions]` schema is reused verbatim — no new kwarg shape to design.

**Notes:** Discussion frame collapsed when the `register()` API was dropped.

---

## Area 3: judge kwarg form — MOOTED BY PIVOT

| Option | Description | Selected |
|---|---|---|
| URL string (`judge="ollama://..."`) | Roadmap goal text wording | |
| Split kwargs (`judge_backend=`/`judge_endpoint=`/`judge_model=`) | REQUIREMENTS.md deferred-items wording | (effective — YAML nested form) |
| Both as overloads | Maximum API surface | |

**User's choice:** Mooted. YAML config retains today's nested `ollama: {base_url, model, timeout_seconds}` shape — no new kwarg form to design.

**Notes:** Discussion frame collapsed when the `register()` API was dropped.

---

## Area 4a: Ini key name (post-pivot)

| Option | Description | Selected |
|---|---|---|
| `mcp_config_file` | Descriptive, parallels MCPTF_CONFIG_FILE env var | ✓ |
| `mcp_contracts_config` | Branded to dist name `mcp-contracts` | |
| `mcp_config` | Terse, matches `mcp_*` fixture prefix | |

**User's choice:** `mcp_config_file`. User: "the first one"

**Notes:** Locked as part of the public-surface freeze (joins the v1.5 API-stability set).

---

## Area 4b: Contract-test body extraction strategy

| Option | Description | Selected |
|---|---|---|
| Move + dogfood now | Delete `tests/contract/test_mcp_tool_contract.py` + `pytest_generate_tests`; framework's CI runs through library-mode injection. Pulls Phase 30 CLOSE-01 dogfood work into Phase 27. | ✓ |
| Hybrid (canonical + thin re-export) | `_tests.py` canonical; existing test file shrinks to `from ... import *` | |
| (Copy was not seriously considered — clear code-drift loser) | | |

**User's choice:** "lets do what you suggest" — Move + dogfood. Claude's recommendation accepted.

**Notes:** Rationale — strongest possible regression test (every framework CI run is a live operator simulation); Phase 30 simplifies; single source of truth, no drift. Trade-off accepted: Phase 27 scope grows mechanically (one ini line, delete one hook, delete one test file).

---

## Area 5: `MCPTF_CONFIG_FILE` env var fate

| Option | Description | Selected |
|---|---|---|
| Kill it entirely | Drop end-to-end in v1.4 with DeprecationWarning; remove in v1.5. CLI mode subprocesses `pytest -o "mcp_config_file=PATH"`. | ✓ |
| Library mode ignores; CLI mode keeps | Matches existing CFG-01 design but goes only halfway | |
| Both work in library mode; ini wins; warn on conflict | Maximum back-compat, maximum cognitive load (the precedence shape that already bit user three times) | |

**User's choice:** "kill it"

**Notes:** Strongly aligned with user memories: `project_dotenv_silently_beats_config`, `project_mcptf_config_file_silent_fail`. One-mechanism principle (D-09 + D-11 + D-12) collapses CLI mode + library mode onto a single ini-based config-resolution route. Deprecation warning v1.4; removal v1.5 alongside every other Phase 25/26/27 deprecation shim.

---

## Area 6: Nodeid shape in pytest output

| Option | Description | Selected |
|---|---|---|
| (a) Real installed-wheel path | `.venv/lib/.../mcp_test_framework/contracts/_tests.py::test_X[tool]` — IDE-clickable but noisy | |
| (b) Synthetic literal | `<mcp-contracts>::test_X[tool]` — Playwright-style, brand-aligned | ✓ |
| (c) Project-relative virtual | `tests/_mcp_contracts::test_X[tool]` — misleading | |

**User's choice:** "b"

**Notes:** Requires `nodeid` override on the synthesized `Module` returned from `pytest_collect_file`. Operators wanting source: `python -c "import mcp_test_framework.contracts._tests; print(_tests.__file__)"`.

---

## Area 7: Failure modes + operator ceremony

Five sub-decisions presented as a single matrix:

| Scenario | Behavior | Selected |
|---|---|---|
| `mcp_config_file` unset | Silent no-op (operator opted out / not onboarded) | ✓ |
| Path doesn't exist | Loud `pytest.exit(returncode=2)` with operator-tone error | ✓ |
| Malformed YAML / schema fail | Loud operator-tone error with file path + field + scaffolder pointer | ✓ |
| `tools:` empty dict | Silent no contract tests injected (matches Phase 13 SAFE-01 opt-in) | ✓ |
| Operator's `tests/conftest.py` | Zero ceremony — no `pytest_plugins`, no `register()`, no imports | ✓ |

**User's choice:** "lets do what you suggest" — Claude's full matrix accepted.

**Notes:** Aligns with `feedback_scaffold_completeness` + `project_mcptf_config_file_silent_fail` — fail loud on operator setup errors, silent on legitimate opt-out states. Black-box guard relocates from `tests/conftest.py:pytest_configure` to `src/mcp_test_framework/_black_box_guard.py` (LIB-08) and is invoked from plugin `pytest_configure`. `_preflight` predicate flips from path-prefix to marker-based per LIB-07.

---

## Claude's Discretion

- **Plugin hook choice** — `pytest_collect_file` vs `pytest_collection_modifyitems` for virtual module synthesis. Suggested: `pytest_collect_file` with custom Module subclass overriding `nodeid`.
- **`Config()` loader rewiring strategy** — refactor to accept explicit path argument vs internal env-var-set workaround. Suggested: refactor (option b reintroduces env-var-magic just killed).
- **`_session_needs_preflight()` marker-detection mechanics** — nodeid-prefix check vs `iter_markers` iteration. Suggested: marker iteration (semantically honest).
- **Deprecation copy literal for MCPTF_CONFIG_FILE** — `"MCPTF_CONFIG_FILE env var is deprecated since v1.4 and will be removed in v1.5 — use [tool.pytest.ini_options] mcp_config_file = PATH in pyproject.toml or pass --config PATH to mcp-contracts run instead."`
- **`gen-test-classes` CLI input-config rewire** — Phase 27 or Phase 28. Planner picks.

---

## Deferred Ideas

### Phase 28 (already roadmapped; scope shrinks per CONTEXT.md `<downstream_impact>`)
- Codegen output path defaults (CODEGEN-LIB-01/02).
- `gen-test-classes` CLI input-config rewire (if punted from Phase 27).

### Phase 29 (already roadmapped, unchanged)
- `--mcp-domain-ui` reporter plugin.

### Phase 30 (already roadmapped; CLOSE-01 dogfood pre-empted)
- Production PyPI publish, README rewrite leading with library mode, CLI demotion to appendix, carry-forward UATs.

### v1.5 cleanup
- `MCPTF_CONFIG_FILE` env var removal (deprecation lands Phase 27).
- Tool auto-discovery (`tools:` omitted → discover all).
- Multi-config (list of paths) for multi-server monorepos.

### Documentation amendments (post-Phase-27, pre-Phase-28)
- REQUIREMENTS.md LIB-01..08 + CFG-01..02 rewrites per CONTEXT.md `<downstream_impact>`.
- ROADMAP.md milestone goal + Phase 27 title + Success Criteria + Phase 28 + Phase 30 amendments.

