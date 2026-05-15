# Phase 23: Test suite debt cleanup — Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 7 modified, 1 created (conftest.py), 2 read-only references
**Analogs found:** 8 / 8 (all clusters have an in-repo analog)

---

## File Classification

| File (modified / created) | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/framework/unit/test_homelab_config.py` | test (unit, schema) | request-response (sync ctor) | itself (`:56-58`) — pattern already lives here | exact (source) |
| `tests/framework/test_tool_config.py` | test (unit + AsyncMock) | request-response | `tests/framework/unit/test_homelab_config.py:56-64` | exact role + data flow |
| `tests/framework/test_config_init_cli.py` | test (integration) | request-response | `tests/framework/unit/test_homelab_config.py:56-64` | exact role + data flow |
| `tests/framework/smoke/test_smoke_homelab_mcp.py` | test (smoke) | request-response | `tests/framework/unit/test_homelab_config.py:56-64` | exact role + data flow |
| `tests/framework/smoke/test_smoke_ollama_judge.py` | test (smoke) | request-response | `tests/framework/unit/test_homelab_config.py:56-64` | exact role + data flow |
| `tests/framework/unit/test_migration_doc.py` | test (doc regression) | file-I/O (read) | `tests/framework/unit/test_doc_scrub.py:16-21` (alt) and the file itself `:14-15` (bump-in-place) | exact (mechanical bump) |
| `tests/framework/unit/test_cli_errors.py` | test (CLI errors + AST scan) | file-I/O (read) | same as above — `:407` bump | exact (mechanical bump) |
| `tests/framework/conftest.py` **(CREATE)** | pytest conftest (fixture override) | request-response | `tests/sdet/conftest.py` (sibling conftest with focused hook) | role-match (different hook, same shape) |
| `README.md` | doc (operator-facing) | content rewrite | n/a — content fix; the contract lives in `tests/framework/unit/test_doc_scrub.py:31-49, 158-221` | rule-driven |
| `tests/framework/unit/test_doc_scrub.py` | test (read-only) | n/a | n/a — this defines the close-gate | n/a |
| `src/mcp_test_framework/fixtures.py` | source (read-only, D-02) | n/a | n/a — production fixture is intentionally not modified | n/a |

---

## Pattern Assignments

### `tests/framework/unit/test_homelab_config.py` (source of the `_SDET_STUB` pattern)

**Already contains the pattern.** This file is the propagation source for Cluster A. No new excerpt needed — the executor's job is to verify these lines are still present (they currently are) and to NOT regress them.

**The locked pattern** (`tests/framework/unit/test_homelab_config.py:51-65`):
```python
import textwrap

from mcp_test_framework.config import Config
from mcp_test_framework.models import SdetConfig

# Phase 21.1 RELOC-01: Config.sdet is REQUIRED. Tests in this file that
# construct Config(...) must supply an sdet stub (or set it in YAML).
_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")


def test_config_default_homelab():
    # Pure-default Config (no YAML, no env). Confirms the new field
    # default_factory wires through the root model.
    cfg = Config(sdet=_SDET_STUB)
    assert cfg.homelab.proxmox.dogfood_vmid_range == (9990, 9999)
```

**Inline-stub variant** for tests that don't want a module-level constant (`tests/framework/test_tool_config.py:204-212` — already adopted at the AsyncMock sites):
```python
from mcp_test_framework.models import SdetConfig
config = Config(
    sdet=SdetConfig(generated_root="tests/sdet/_generated"),
    tools={
        "a": ToolConfig(),
        "b": ToolConfig(skip=True, skip_reason="testing the filter"),
        "c": ToolConfig(),
    }
)
```

**Note for executor:** Cluster A red sites where `Config()` is called bare are:
- `tests/framework/test_tool_config.py:53` (`test_default_config_version_and_tools`)
- `tests/framework/test_tool_config.py:150` (somewhere in TestV111SkipFilter region — also reachable by `test_call_arguments_forwarded_to_call_tool_via_asyncmock` because the test function body calls into `tests.test_mcp_tool_contract.test_empty_args_call_returns_non_error`, which itself may build a Config — verify when running the failure)
- `tests/framework/test_config_init_cli.py:130` (`cfg = Config()  # MUST NOT raise`)
- `tests/framework/smoke/test_smoke_homelab_mcp.py:41, 63`
- `tests/framework/smoke/test_smoke_ollama_judge.py:78`
- `tests/framework/unit/test_runner_migration.py:132, 192` (the bare `Config()` MUST stay bare — these tests are specifically asserting the `MCPTF_CONFIG_FILE` fallback works on a bare `Config()`. They likely already work because the env var IS set during the test; verify before changing — they may not actually be in the red set.)

**Pattern to apply (Cluster A)**: change `Config()` → `Config(sdet=_SDET_STUB)` (module-level stub) OR `Config(sdet=SdetConfig(generated_root="tests/sdet/_generated"))` (inline). Prefer module-level when ≥2 sites in a file.

---

### `tests/framework/unit/test_migration_doc.py` (Cluster B: mechanical bump)

**Pattern:** in-place `parents[2]` → `parents[3]`.

**Current (broken) code** (`tests/framework/unit/test_migration_doc.py:14-18`):
```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


MIGRATION_DOC = _repo_root() / "docs" / "MIGRATION-v1-to-v2.md"
```

**Verified resolution at current depth** (Bash output, 2026-05-14):
- File path: `tests/framework/unit/test_migration_doc.py`
- `parents[2]` resolves to `…/tests/` (broken — that's why `tests/docs/MIGRATION-…` is being probed)
- `parents[3]` resolves to repo root `…/mvp_test_framework/` (correct)

**Fix excerpt** (executor copies verbatim):
```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
```

**Alternative pattern explicitly NOT adopted (per D-04)** — the walk-to-`pyproject.toml` style at `tests/framework/unit/test_doc_scrub.py:16-21`:
```python
def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")
```
Leave heterogeneous styles. Consolidation is captured as deferred.

---

### `tests/framework/unit/test_cli_errors.py` (Cluster B: mechanical bump)

**Current (broken) code** (`tests/framework/unit/test_cli_errors.py:401-409`):
```python
def test_cli_errors_static_call_sites_no_banned_tokens() -> None:
    """AST scan: every _emit_operator_error call's literal args are operator-tone."""
    import ast
    # Walk up from this test file to the repo root (same pattern as
    # test_doc_scrub._repo_root) so the test passes regardless of the
    # cwd pytest is invoked from.
    repo_root = Path(__file__).resolve().parents[2]
    src = (repo_root / "src" / "mcp_test_framework" / "cli.py").read_text(
        encoding="utf-8"
    )
```

**Fix:** change `parents[2]` → `parents[3]` at line 407. Comment text already (mis)describes the pattern as "walk up"; D-04 keeps the heterogeneous style and merely fixes the depth count.

---

### `tests/framework/conftest.py` (CREATE — D-02 test-side override seam)

**Status:** `tests/framework/conftest.py` does NOT exist (Glob result empty). The planner must CREATE it.

**Analog 1 (preferred, closest by directory shape):** `tests/sdet/conftest.py` — a focused conftest scoped to a sibling subdir of `tests/`, registering a single hook. Same shape and depth.

`tests/sdet/conftest.py` (full body — verbatim, for shape reference):
```python
"""Phase 18 SDET-only conftest: ToolCallError -> JUnit user_properties hook.

[... docstring elided ...]
"""
from __future__ import annotations

from mcp_test_framework.sdet import ToolCallError


def pytest_exception_interact(node, call, report):
    """D-09 + D-11: hoist ToolCallError fields onto report.user_properties.
    [... elided ...]
    """
    exc = call.excinfo.value if call.excinfo else None
    if isinstance(exc, ToolCallError):
        report.user_properties.append(("mcptf_error_code", exc.code or ""))
        report.user_properties.append(("mcptf_error_message", exc.message))
        report.user_properties.append((
            "mcptf_error_raw",
            exc.raw.model_dump_json(indent=2) if exc.raw is not None else "",
        ))
```

**Shape to copy:**
- `from __future__ import annotations`
- Short docstring naming the phase + the contract being held
- Single hook / fixture definition; nothing else

**Analog 2 (the production fixture being shadowed):** `src/mcp_test_framework/fixtures.py:89-101`:
```python
@pytest.fixture(scope="session")
def config() -> Config:
    """Load YAML config once per session.
    [... docstring elided ...]
    """
    return Config()
```
This is the fixture that fails under bare `Config()` after RELOC-01. The override in `tests/framework/conftest.py` has the same name, same scope, and supplies the sdet stub.

**Recommended new file** (executor pattern — substantively complete; the planner may tune the docstring):
```python
"""Phase 23 D-02: test-side override of the session-scoped `config` fixture.

After Phase 21.1 RELOC-01 made Config.sdet REQUIRED, the production fixture
at src/mcp_test_framework/fixtures.py raises pydantic.ValidationError when
constructed bare. tests/framework/ tests don't need a real sdet config -- they
exercise the framework itself, not SDET codegen. This conftest shadows the
fixture with one that supplies the `_SDET_STUB` pattern already established
at tests/framework/unit/test_homelab_config.py.

Production `src/` is intentionally NOT modified -- see Phase 23 CONTEXT.md D-02.
"""
from __future__ import annotations

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.models import SdetConfig

_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")


@pytest.fixture(scope="session")
def config() -> Config:
    return Config(sdet=_SDET_STUB)
```

**Override-precedence note for executor:** pytest's conftest resolution gives the more-deeply-nested conftest priority. `tests/framework/conftest.py` shadows `src/mcp_test_framework/fixtures.py:config` for any test collected under `tests/framework/`. The production fixture continues to apply for `tests/contract/` and `tests/sdet/`.

---

### `README.md` (Cluster C: D-05 + D-06 rewrites)

**Read-only contract definers (must NOT be edited):**

1. **Banned-token regex** — `tests/framework/unit/test_doc_scrub.py:31-39, 49`:
   ```python
   BASE_BANNED = [
       r"\bPhase \d",
       r"\bPlan \d-\d",
       r"\bTOOLCFG-\d",
       r"\bISOL-\d",
       r"\bOUTPUT-\d",
       r"\bD-\d{2}",
       r"\b\d{6}-[a-z0-9]{3}",
   ]
   # … README rule:
   patterns = BASE_BANNED + [r"src/[\w/.]+\.py:\d+"]
   ```

2. **Operator-invocation pairing rule** — `tests/framework/unit/test_doc_scrub.py:158-221`. The fail message names the exact line numbers when run. Executor must run the test to enumerate.
   Exemptions documented in the test body: `--config`, `--help`, `--command`.
   Output-line heuristic prefixes (excluded as pytest output, not invocations): `platform `, `rootdir:`, `configfile:`, `plugins:`, `asyncio:`, `collected `, `tests\\`, `tests/`, `=====`.

**README.md line 104 context** (`README.md:98-114`, verbatim — preserve surrounding prose during rewrite):
```
##### `--explain` example

`--explain` drops the `(use --explain to list)` hint and renders the list
inline between the digest and the pytest subprocess:

```
$ mcp-test-framework run --explain
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56
```

**D-05 fix shape**: line 104 changes from `$ mcp-test-framework run --explain` to `$ mcp-test-framework run --config config.yaml --explain`. The downstream sample output (header, lists, counts) is unaffected.

**D-06 fix shape (banned tokens)**: enumerate via running the test, then apply Phase 12 D-10 semantic-rewrite (NOT regex-strip). Phase 12 precedent: replace `Phase N` / `D-NN` / `Plan N-N` / `src/foo.py:LL` references with operator-meaningful prose. Example transformation (from Phase 12 CLEAN-01 commits):
- BEFORE: `Per Phase 12 D-08, every invocation pairs with --config`
- AFTER:  `Every operator-facing invocation in this README pairs with --config so the framework launches against a known config; see ERROR-STYLE.md for the launch-error surface.`

Preserve prose meaning. Cite surviving doc anchors (`docs/ERROR-STYLE.md`, `docs/EXTENDING.md`, `docs/MIGRATION-v1-to-v2.md`, `examples/homelab-mcp.yaml`) — these are not banned.

---

## Shared Patterns

### Pattern S1: `_SDET_STUB` module constant
**Source:** `tests/framework/unit/test_homelab_config.py:51-58`
**Apply to:** every Cluster A red site that calls `Config()` with no args, when the file has ≥2 such call sites.
```python
from mcp_test_framework.models import SdetConfig

_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")
# ... then: Config(sdet=_SDET_STUB)
```

### Pattern S2: Inline `SdetConfig(...)` kwarg
**Source:** `tests/framework/test_tool_config.py:204-212` (already adopted in TestV111SkipFilter)
**Apply to:** single-site Cluster A reds, or when the call already passes other kwargs.
```python
Config(sdet=SdetConfig(generated_root="tests/sdet/_generated"))
```

### Pattern S3: `parents[N]` repo-root (heterogeneous; do NOT consolidate per D-04)
**Source — depth 3 (under `tests/framework/unit/`):** must use `parents[3]`.
**Source — depth 2 (under `tests/framework/`):** uses `parents[2]` (already correct — leave alone). Examples: `tests/framework/test_banned_imports.py:30`, `tests/framework/test_runner_subprocess.py:359`, `tests/framework/test_runner_live_smoke.py:33-57`, `tests/framework/smoke/test_mcp_client_teardown_regression.py:46` (smoke/ is depth 3, but this file uses `parents[2]` — verify whether it's broken too; not in current red set so leave).

### Pattern S4: walk-to-`pyproject.toml` (alternative, NOT propagated)
**Source:** `tests/framework/unit/test_doc_scrub.py:16-21`. Robust to depth changes. Captured as future-refactor candidate; D-04 says do not propagate now.

### Pattern S5: Doc semantic-rewrite (NOT regex-strip)
**Source:** Phase 12 D-10 precedent (no current code excerpt — historical commit shape).
**Apply to:** every banned-token hit identified by `test_readme_exists_and_no_banned_tokens`.
- Identify the banned token.
- Rewrite the sentence to preserve operator-meaningful intent.
- Cite surviving doc anchors instead of planning IDs.

### Pattern S6: `--config config.yaml` pairing rule
**Source:** `tests/framework/unit/test_doc_scrub.py:158-221` (`test_doc_invocations_consistently_pair_with_config`).
**Apply to:** every fenced-code-block line in README.md / docs/EXTENDING.md that matches `mcp-test-framework (run|list-tools|config-init)\b` and does NOT contain `--config`, `--help`, or `--command`.

---

## No Analog Found

None. Every Cluster A/B/C fix has an in-repo pattern source. The only new file (`tests/framework/conftest.py`) is modeled on `tests/sdet/conftest.py` for shape and on the `_SDET_STUB` pattern for body.

---

## Pre-Flight Notes for the Planner

1. **Enumerate Cluster A reds before writing tasks.** Run `uv run pytest tests/framework/ --tb=no -q` (under `pyproject.toml` addopts which deselect `live_homelab and live_ollama`). The 12 fails + 1 error inventory needs concrete file:test pairs before the executor can apply S1/S2 mechanically. Specifically:
   - `tests/framework/test_tool_config.py::test_call_arguments_forwarded_to_call_tool_via_asyncmock` is the suspected 12th red (per CONTEXT specifics §1). Confirm.
   - `tests/framework/unit/test_runner_migration.py:132, 192` use intentional bare `Config()` (testing the env-var fallback). These may already pass because the env var is set in the test setup — verify before changing.

2. **Enumerate Cluster C banned tokens before drafting rewrites.** Run the test once to get the regex hit list:
   ```bash
   uv run pytest tests/framework/unit/test_doc_scrub.py::test_readme_exists_and_no_banned_tokens -v
   ```
   The assertion message lists the matching regexes, but not the offending text — the planner runs `Grep` for each surviving pattern in `README.md` to get exact lines. D-10 says rewrite, not strip; per-hit decisions belong in the plan.

3. **Run the doc-invocation test for line numbers.** Its assertion message names every offending line; copy that list into the plan rather than guessing from `Grep`.

4. **Close-gate verification (D-07/D-08):** the planner's final plan asserts:
   ```bash
   uv run pytest tests/framework/ --tb=no -q
   # expect: 0 failed, 0 errored. xfailed=2 and skipped=1 stay.
   ```

---

## Metadata

**Analog search scope:** `tests/framework/**`, `tests/conftest.py`, `tests/sdet/conftest.py`, `src/mcp_test_framework/fixtures.py:85-117`, `README.md:88-125`.
**Files scanned (Read calls):** 8 (CONTEXT.md, test_homelab_config.py, test_doc_scrub.py, test_migration_doc.py, test_cli_errors.py:395-422, fixtures.py:85-125, tests/conftest.py, tests/sdet/conftest.py, test_isolation.py, test_tool_config.py, README.md:90-125).
**Grep scans:** `Config\(\)` and `parents\[2\]` under `tests/framework/`.
**Pattern extraction date:** 2026-05-14.
