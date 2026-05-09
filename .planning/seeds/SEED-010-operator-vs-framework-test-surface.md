---
id: SEED-010
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete + manual UAT (post-merge of v1.1.1 hotfix)
trigger_when: v1.2 milestone framing — surface during /gsd-new-milestone questioning step
scope: Small
---

# SEED-010: Separate operator-facing tests from framework self-tests

## Why This Matters

When an operator runs `mcp-test-framework run` to test their MCP, the framework currently sweeps the entire `tests/` directory — including ~107 framework self-tests (pure unit tests of `_extract_first_json_object`, rubric internals, ToolConfig schema, README snippets, banned imports, etc.) alongside the ~20 contract tests that actually exercise the MCP.

Real-world impact (observed 2026-05-08 manual UAT):
- Operator runs `mcp-test-framework run --config config.yaml -v` against `homelab-mcp`
- Output mixes 107 framework self-test pass/fail lines with 20 actual MCP contract test results
- The framework's own internals dominate the output; the signal (does my MCP pass?) is buried in the noise (does the framework's parser handle escape characters?)
- Operator quote: "we also need to find a way to not run the unit tests if this is meant to test the mcp the unit tests muddle the results"

This is a structural mistake from v1.0/v1.1 carrying through into v1.1.1. The framework was built developer-first — single `tests/` directory, single `pytest tests/` invocation, single CI surface. v1.2 needs to split the surface so operators see only operator-relevant tests.

## When to Surface

**Trigger:** v1.2 milestone framing — surface during `/gsd-new-milestone` questioning step

This seed should be presented when the new milestone scope mentions any of:
- Test structure / test layout / pytest layout
- Operator UX / vibe-coded persona / `mcp-test-framework run` surface
- CLI surface / what does `run` default to
- Reporter cleanup (compounds with SEED-008's pre-run digest — fewer tests in scope = smaller, more readable digest)

## Scope Estimate

**Small** — One phase. Mechanical work: restructure `tests/` directory, update `cli.py`'s `_build_pytest_args` to point at the new contract subdirectory, add an `--include-framework` flag (or separate `pytest tests/framework/` invocation) for framework dev.

## Two Candidate Designs

### Design A — Directory restructure (recommended)

```
tests/
  contract/                    # operator-facing — what `mcp-test-framework run` exercises
    test_mcp_tool_contract.py
    conftest.py                # shared fixtures (mcp_client, judge, target_tool, etc.)
  framework/                   # framework dev only — `pytest tests/framework/` for CI
    test_config.py
    test_reporter.py
    test_tool_config.py
    test_isolation.py
    test_readme_snippets.py
    test_config_init_cli.py
    test_banned_imports.py
    smoke/                     # framework smoke tests (existing tests/smoke/ moves here)
      test_smoke_homelab_mcp.py
      test_smoke_ollama_judge.py
      test_mcp_client_teardown_regression.py
    unit/                      # framework unit tests (existing tests/unit/ moves here)
      test_config.py
      test_mcp_client.py
      test_ollama_judge.py
      test_rubrics.py
      test_schema_validator.py
```

CLI changes:
- `mcp-test-framework run` defaults to `pytest tests/contract/`
- `--include-framework` flag (or separate invocation) targets `pytest tests/framework/`
- The `_build_pytest_args` helper changes from `["tests", *forwarded]` to `["tests/contract", *forwarded]`

Cost: lots of file moves. Mitigation: scripted `git mv` preserves history; each move is a no-op behavior change.

### Design B — Pytest markers (less restructure)

Mark contract tests with `@pytest.mark.mcp_contract`. CLI's `run` invokes `pytest -m mcp_contract`. Framework tests are unmarked (or marked `framework_dev`).

```python
# tests/test_mcp_tool_contract.py
pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.mcp_contract,  # NEW
]
```

```python
# pyproject.toml
markers = [
  "live_homelab: ...",
  "live_ollama: ...",
  "mcp_contract: tests that exercise an MCP server end-to-end (operator-facing)",
  "framework_dev: tests of the framework itself (developer-facing)",  # optional
]
addopts = "-m 'not live_homelab and not live_ollama'"  # unchanged
```

Cost: every test file needs a top-level marker. Risk: forgetting a marker on a new test silently puts it in the wrong category.

### Recommendation: Design A

Directory structure communicates intent without operators needing to know about pytest markers. It also makes the persona reframe (SEED-007) concrete: the operator literally never has reason to look inside `tests/framework/`. Migration is mechanical (`git mv` + path updates in `_build_pytest_args` + CI workflow updates).

## Cumulative Pattern Worth Naming

This is the **fifth** operator-vs-developer pain point surfaced during one manual UAT session on 2026-05-08:

1. `project_vibe_coded_persona.md` (SEED-007) — black-box rule reframed from test discipline to user-persona feature
2. `feedback_scaffold_completeness.md` — `config-init` produces incomplete scaffolds because devs assume operators know to fill in defaults
3. `project_genericize_example_config.md` (SEED-009) — `config.example.yaml` is homelab-saturated because devs wrote it from their setup
4. `project_pre_run_tool_summary.md` (SEED-008) — pytest's "N collected, M deselected" framing serves devs, not operators
5. **This seed** — `tests/` directory layout assumes a single dev/CI audience

The pattern is loud enough that **v1.2's milestone theme should be operator-first design**, with these seeds as the implementation path. Worth surfacing during `/gsd-new-milestone` questioning before any phase planning.

## How to Apply During v1.2 Planning

- Sequence after SEED-009 (doc/example cleanup) — both are foundational hygiene that compounds with the bigger semantic redesigns.
- Update CI to run both `tests/contract/` AND `tests/framework/` (CI exercises everything; operators get the narrow surface).
- The pre-run digest in SEED-008 should display only operator-facing test counts by default; framework counts only appear when `--include-framework` is set.

## Breadcrumbs

- `src/mcp_test_framework/cli.py:_build_pytest_args` (lines 92-115) — the single point that hardcodes `tests` as the pytest root; change to `tests/contract`
- `src/mcp_test_framework/cli.py:run` (lines 118-172) — Typer command that calls `_build_pytest_args`
- `tests/conftest.py` — needs to move to `tests/contract/conftest.py` (and possibly a stub at `tests/conftest.py` for `tests/framework/` if it shares fixtures)
- `tests/` directory structure (current state) — listed under Design A above, all leaf files move
- `pyproject.toml` `[tool.pytest.ini_options].testpaths = ["tests"]` — may need updating to `["tests/contract", "tests/framework"]` or removed entirely if the CLI dictates the path

## Related Memories

- `feedback_uat_must_be_user_driven.md` — same operator-vs-developer theme at the UAT-design level
- `project_vibe_coded_persona.md` (SEED-007) — positioning that this seed implements concretely
- `project_pre_run_tool_summary.md` (SEED-008) — compounds: smaller test surface = smaller, cleaner pre-run digest
