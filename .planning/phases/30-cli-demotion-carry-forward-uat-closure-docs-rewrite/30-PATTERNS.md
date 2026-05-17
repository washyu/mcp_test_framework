# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 11 (5 create, 5 modify, 1 conditional)
**Analogs found:** 9 / 11 (2 files have no in-repo analog — `LIBRARY-MODE.md`, `30-UAT.md` shape)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | test (framework self-test, subprocess parity) | spawn-subprocess + file-IO (JUnit XML) | `tests/framework/test_runner_live_smoke.py` | exact (subprocess + tmp_path + ET.parse + live marker) |
| `tests/framework/parity/__init__.py` | test (package marker) | n/a | empty / not required (pytest collects without `__init__.py` per existing `tests/framework/smoke/`) | n/a — likely skip |
| `tests/framework/conftest.py` (MODIFY: add `parity` marker) | test (conftest, marker registration) | pytest_configure hook | `tests/framework/conftest.py` (existing shape) + `pyproject.toml` markers list | role-match |
| `docs/LIBRARY-MODE.md` (CREATE) | docs (operator reference) | static markdown | `docs/TEST-CODE-AUTHORING.md` | role-match (peer operator doc) |
| `README.md` (MODIFY: heavy rewrite) | docs (top-of-funnel) | static markdown | `README.md` itself + `docs/TEST-CODE-AUTHORING.md` (heading + fence style) | self / role-match |
| `.planning/REQUIREMENTS.md` (MODIFY: CLOSE-01, CLOSE-03) | requirements (line-item rewrite) | n/a | Phase 27/28 CLOSE-NN line-edit precedent | role-match |
| `.planning/phases/30-.../30-UAT.md` (CREATE: capture protocol) | capture-protocol (user-driven) | static markdown + paste-evidence blocks | `.planning/phases/29-.../29-HUMAN-UAT.md` + `25-UAT.md` (yaml frontmatter + structured sections) | role-match |
| `pyproject.toml` (conditional MODIFY: only if marker added here) | config | toml | `pyproject.toml:67-72` existing `markers = [...]` block | exact (but framework-conftest registration preferred per CONTEXT.md) |
| `config.example.yaml`, `.env.example`, `docs/EXTENDING.md` | docs/config (scrub-verify only) | n/a | Research §"Doc scrub already resolved" — VERIFIED clean | no-op |

## Pattern Assignments

### `tests/framework/parity/test_cli_vs_pytest_route.py` (test, subprocess parity)

**Analog:** `tests/framework/test_runner_live_smoke.py` (closest existing live-stack subprocess test)

**Module docstring + imports pattern** (`test_runner_live_smoke.py:1-19`):
```python
"""Phase 14 Plan 05: live-homelab integration smoke for the new wrapper.

[...module purpose, what it asserts, and how it's gated by default...]

Skipped by default via the @pytest.mark.live_homelab marker
(pyproject.toml's `addopts = "-m 'not live_homelab and not live_ollama'"`).
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
```

**Pattern for parity test:** mirror — add `import sys` for `sys.executable` invocation.

**Marker-stack pattern — single live marker** (`test_runner_live_smoke.py:22`):
```python
pytestmark = pytest.mark.live_homelab
```

**Marker-stack pattern — multiple markers (composable)** (`tests/framework/smoke/test_smoke_homelab_mcp.py:34-37`):
```python
pytestmark = [
    pytest.mark.live_homelab,
    pytest.mark.asyncio(loop_scope="session"),
]
```

**Pattern for parity test:** combine both — the parity test is sync (no asyncio marker) but needs the new `parity` recursion-guard marker + both live markers:
```python
pytestmark = [
    pytest.mark.parity,         # recursion guard — outer subprocesses pass -m "not parity"
    pytest.mark.live_homelab,   # skip-gate (deselected by default via addopts)
    pytest.mark.live_ollama,
]
```

**Subprocess invocation shape** (`test_runner_live_smoke.py:25-29`):
```python
def _run_framework_subprocess(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "mcp-test-framework", "run", *args],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
```

**Pattern for parity test Route A:** swap to `mcp-contracts` (post-rename) and use `sys.executable -m` for in-tree-source fidelity. `cli.py:1787` has `if __name__ == "__main__": app()` verified, so `python -m mcp_test_framework.cli` invokes the Typer app correctly. Route A:
```python
proc_a = subprocess.run(
    [sys.executable, "-m", "mcp_test_framework.cli", "run",
     "--config", "config.test.yaml",
     f"--junit-xml={xml_a}",
     "--", "-m", "not parity"],
    cwd=repo_root, capture_output=True, text=True, check=False,
)
```

**Pattern for parity test Route B (raw pytest, no precedent in repo — composed from research §Pattern 1):**
```python
proc_b = subprocess.run(
    [sys.executable, "-m", "pytest",
     "-o", "mcp_config_file=./config.test.yaml",
     f"--junitxml={xml_b}",
     "-m", "not parity",
     "tests/"],
    cwd=repo_root, capture_output=True, text=True, check=False,
)
```

**`repo_root` resolution pattern** (`test_runner_live_smoke.py:33`):
```python
repo_root = Path(__file__).resolve().parents[2]
```

**Pattern for parity test:** `parents[3]` because the parity test sits one level deeper (`tests/framework/parity/test_*.py` vs `tests/framework/test_*.py`). Research §"Anti-Patterns to Avoid" calls this out explicitly.

**JUnit XML walker pattern** (`test_runner_live_smoke.py:51-53` — minimal precedent for `ET.parse`):
```python
tree = ET.parse(target)
root = tree.getroot()
assert root.tag in {"testsuites", "testsuite"}
```

**Pattern for parity test:** extend to a full `{nodeid: outcome}` walker. Research §Pattern 1 supplies the exact 26-line shape; key elements:
```python
def _parse_outcomes(xml_path: Path) -> dict[str, str]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    out: dict[str, str] = {}
    for tc in suite.iter("testcase"):
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        nodeid = f"{classname}::{name}" if classname else name
        # any-fail-wins per child element: failure > error > skipped > passed
        if tc.find("failure") is not None:
            out[nodeid] = "failed"
        elif tc.find("error") is not None:
            out[nodeid] = "error"
        elif tc.find("skipped") is not None:
            out[nodeid] = "skipped"
        else:
            out[nodeid] = "passed"
    return out
```

**XML-existence assertion pattern** (`test_runner_live_smoke.py:50`):
```python
assert target.exists(), f"--junit-xml=PATH did not populate {target}: {proc.stdout}"
```

**Pattern for parity test:** mirror per-route, surface BOTH stdout AND stderr per Pitfall §4 (Windows subprocess returncode debugging):
```python
assert xml_a.exists(), f"Route A produced no XML.\nstdout:\n{proc_a.stdout}\nstderr:\n{proc_a.stderr}"
```

**D-02a defensive non-vacuous assertion (CONTEXT.md locked resolution, no in-repo precedent):**
```python
# Right after parsing — before the equality assert
assert outcomes_a, (
    "Parity test ran against an empty outcomes dict — likely because "
    "./config.test.yaml ships with `tools: {}` (Phase 27 D-13/D-16). "
    "Populate `tools:` in config.test.yaml or run against a populated config. "
    f"Route A stdout (tail):\n{proc_a.stdout[-2000:]}"
)
```

**Dict-equality assertion + readable diff (composed in research §Pattern 1; no in-repo precedent for set-diff failure messages):**
```python
assert outcomes_a == outcomes_b, (
    f"CLI vs pytest-route outcome divergence.\n"
    f"Only in Route A: {set(outcomes_a) - set(outcomes_b)}\n"
    f"Only in Route B: {set(outcomes_b) - set(outcomes_a)}\n"
    f"Differing outcomes: "
    f"{ {k: (outcomes_a.get(k), outcomes_b.get(k)) for k in outcomes_a if outcomes_a.get(k) != outcomes_b.get(k)} }"
)
```

---

### `tests/framework/conftest.py` (MODIFY: register `parity` marker)

**Analog:** existing `tests/framework/conftest.py` (additive) + `pyproject.toml:67-72` `markers = [...]` block.

**Existing conftest shape (`tests/framework/conftest.py:1-25`):**
```python
"""Phase 23 D-02: test-side override of the session-scoped `config` fixture.
[...]
Production `src/` is intentionally NOT modified -- see Phase 23 CONTEXT.md D-02.
"""
from __future__ import annotations

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.models import TestCodeConfig

_TEST_CODE_STUB = TestCodeConfig(generated_root="tests/sdet/_generated")


@pytest.fixture(scope="session")
def config() -> Config:
    return Config(test_code=_TEST_CODE_STUB)
```

**Existing `pyproject.toml` markers block (`pyproject.toml:68-72`):**
```toml
markers = [
  "live_homelab: requires homelab-mcp runnable via uvx (or on PATH)",
  "live_ollama: requires reachable Ollama at OLLAMA_BASE_URL with the configured model",
]
addopts = "-m 'not live_homelab and not live_ollama'"
```

**Pattern for marker registration in conftest (research §Pattern 2, no in-repo precedent for `pytest_configure` hook):**

The CONTEXT.md `<decisions>` default is to register the marker in `tests/framework/conftest.py` rather than `pyproject.toml` so the marker is framework-internal (not surfaced on operator `pytest --markers`). Pattern to append:
```python
def pytest_configure(config: pytest.Config) -> None:  # noqa: D401
    config.addinivalue_line(
        "markers",
        "parity: framework-internal recursion guard for the CLI/library "
        "parity test (tests/framework/parity/). Inner subprocesses exclude "
        "this marker with `-m 'not parity'` to prevent infinite recursion.",
    )
```

**Note on the function name collision:** The existing conftest already defines a `config` fixture (line 22-24). The new `pytest_configure` hook takes a `config: pytest.Config` argument with the same name as the fixture but at hook scope — no actual collision, but planner should rename the hook parameter to e.g. `pytestconfig` if any reader confusion is anticipated.

---

### `docs/LIBRARY-MODE.md` (CREATE: operator-facing primary reference)

**Analog:** `docs/TEST-CODE-AUTHORING.md` (peer operator-facing doc with similar heading depth and walkthrough shape).

**Heading + intro pattern (`docs/TEST-CODE-AUTHORING.md:1-12`):**
```markdown
# Authoring test-code scenarios for your MCP server

This doc walks a test-code author through authoring a scenario test file under
`tests/test_code/test_<name>.py` against a connected MCP server. The flow covers
[...one-paragraph scope statement, ~6-8 lines...]

## Prerequisites

- A configured MCP server (a working `config.yaml`; see `docs/EXTENDING.md`
  for the bootstrap flow).
- `mcp-test-framework` installed in the project's `uv` environment
  (`uv sync` once, then `uv run mcp-test-framework --help`).
```

**Pattern for LIBRARY-MODE.md:** mirror exactly:
- H1 in title case naming the doc subject
- One paragraph (~6-8 lines) framing scope + persona
- `## Prerequisites` bullet list
- Subsequent H2 sections one per topic (quickstart, what-it-is/is-not, mechanism, surfaces, migration, error tone, links)

**Code-fence pattern in `docs/TEST-CODE-AUTHORING.md:34-37`:**
```bash
uv run mcp-test-framework gen-test-classes
```

**Pattern for LIBRARY-MODE.md:** triple-backtick fenced blocks with language tag (`bash`, `toml`, `python`). Per CLAUDE.md "No emojis"; no symbols/decorative chars.

**Link-style pattern (`docs/TEST-CODE-AUTHORING.md:15`):**
```markdown
(see `docs/EXTENDING.md` for the bootstrap flow)
```

Inline-backtick + relative path. `LIBRARY-MODE.md` links back to `TEST-CODE-AUTHORING.md` for the test-code-author surface; does not duplicate that doc's content. Full outline is in `30-RESEARCH.md` §"`docs/LIBRARY-MODE.md` outline" lines 612-753.

---

### `README.md` (MODIFY: heavy rewrite)

**Analog:** itself (current top-of-file) + `docs/TEST-CODE-AUTHORING.md` (style consistency).

**Current top-of-README pattern (`README.md:1-15`):**
```markdown
# mcp_test_framework

A pytest-based Python framework for testing MCP (Model Context Protocol) servers.

The MVP targets the `homelab-mcp` server over stdio and validates one tool
(`list_keyring_credentials` by default) end-to-end through schema validation, an
Ollama-backed description-quality judge, and output conformance checks.

## Testing an MCP server you didn't write
[...current secondary subsection — keep, move down...]
```

**Pattern for rewrite:** lead with library-mode quickstart per research §"README rewrite — operator-onboarding-first structure" (lines 755-781). Recommended ordering:
1. H1 title + one-line value prop
2. Quickstart (3-5 lines: `uv add mcp-contracts`, one ini line, `uv run pytest`)
3. Library-mode reference (~50 lines, link inward to `docs/LIBRARY-MODE.md`)
4. Existing canonical green-run sample (current L222 — keep, move down)
5. Existing test-code scenarios subsection (current L266+ — keep)
6. Configuration (current L155+, light edits to reference `mcp_config_file` ini route)
7. Appendix: CLI usage (current L45-150, demoted, retained verbatim)
8. Setup (current L19-43, demoted or moved into Appendix)
9. Links

**Existing CLI doc shape to preserve verbatim (`README.md:45-50`):**
```markdown
## Commands

### Run the test suite

```bash
uv run mcp-contracts run --config config.yaml
```

This is the demoted Appendix content; do NOT rewrite it.

---

### `.planning/REQUIREMENTS.md` (MODIFY: CLOSE-01 + CLOSE-03 line rewrites)

**Analog:** Phase 27/28 line-item amendments to REQUIREMENTS.md (planner can grep recent commits for "REQUIREMENTS" to find precedent).

**Pattern:** in-place text replacement of two line-items. CONTEXT.md `<downstream_impact>` lines 161-164 supply the exact replacement copy verbatim. CLOSE-02 and CLOSE-04 are unchanged. Traceability table row for Phase 30 stays at current state; flips to `Complete` post-phase-close.

---

### `.planning/phases/30-.../30-UAT.md` (CREATE: capture-protocol document)

**Analog:** `.planning/phases/29-live-domain-ui-reporter-plugin/29-HUMAN-UAT.md` (closest existing capture-protocol shape with frontmatter + structured sections).

**YAML frontmatter pattern (`29-HUMAN-UAT.md:1-7`):**
```yaml
---
status: partial
phase: 29-live-domain-ui-reporter-plugin
source: [29-VERIFICATION.md]
started: 2026-05-17T00:00:00Z
updated: 2026-05-17T00:00:00Z
---
```

**Pattern for `30-UAT.md`:** mirror with `phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite`, `status: pending`, `source: [30-CONTEXT.md, 30-VERIFICATION.md]`.

**Section-per-UAT pattern (`29-HUMAN-UAT.md:15-18`):**
```markdown
### 1. Live-TTY `mcp-contracts run` smoke (CR-01 fix verification)
expected: Run `mcp-contracts run --config <fixture pointing at a real or stub MCP server with at least one tool>` from a real terminal. Header appears before pytest collection finishes; [...]
result: [pending]
why_human: Stream-stdout vs. capture-stdout behavior under a real TTY (not the captured-output mode all framework tests use) is the exact seam [...]
```

This pattern uses `expected: / result: / why_human:` as flat key-value-style fields. Research §"Live-UAT capture protocol shape" (lines 472-502) proposes a richer structure with explicit Pre-reqs, Commands, Pass criteria checklist, and Evidence paste blocks.

**Pattern for `30-UAT.md`:** prefer the richer research-supplied template per UAT (4 UATs: README test-code-scenarios re-capture, Phase 17 ~70-tool codegen, v1.2 Phase 13 v2-config walkthrough, v1.2 Phase 14 live-smoke under both modes). Each UAT section:
```markdown
### UAT-N: <title>
**Background:** <one-line context>
**Carried from:** <Phase/Plan/SC reference>
**Pre-reqs:**
  - <env var, shell, credential, network reachability>

**Commands:**
```bash
<exact command to run, one per line>
```

**Expected observable outcome:** <what the operator should see>
**Pass criteria:**
- [ ] <observable assertion>

**Evidence (paste here after running):**
```
<stdout, screenshot reference, or filepath snapshot>
```

**Status:** [ ] pending / [x] pass / [ ] fail / [ ] blocked
```

The exact body content for each of UAT-1..4 is fully specified in `30-RESEARCH.md` lines 504-611. Planner copies verbatim.

**Summary block pattern (`29-HUMAN-UAT.md:31-37`):**
```yaml
## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0
```

Append this block at the bottom; pre-fill with `total: 4` and `pending: 4`.

---

## Shared Patterns

### Subprocess invocation on Windows
**Source:** `tests/framework/test_runner_live_smoke.py:25-29` and `tests/framework/test_runner_live_smoke.py:46-49`
**Apply to:** parity test (Route A + Route B both)
```python
subprocess.run(
    [sys.executable, "-m", "<package.module>", *args],   # list-form argv — no shell=True
    cwd=repo_root,                                        # pathlib.Path works on 3.14
    capture_output=True, text=True,                       # we read stdout/stderr in assertion messages
    check=False,                                          # we want to inspect returncode, not raise
)
```
Use `f"--junitxml={xml_path}"` as a single argv element (no manual quoting) — verified in `_runner.py:151`. Pattern §Pitfall 4 in research.

### Live-stack opt-in gating
**Source:** `tests/framework/test_runner_live_smoke.py:22` (single marker) and `tests/framework/smoke/test_smoke_homelab_mcp.py:34-37` (multiple markers) + `pyproject.toml:72` (`addopts = "-m 'not live_homelab and not live_ollama'"`)
**Apply to:** parity test
```python
pytestmark = [pytest.mark.live_homelab, pytest.mark.live_ollama, ...]
```
Default addopts deselects either marker; operator opts in with `-m live_homelab` (note: `-m` SELECTS, doesn't add — see Pitfall §1 in research; operator must use full expression like `-m "parity and live_homelab and live_ollama"`).

### `__future__` import + `from pathlib import Path`
**Source:** `tests/framework/test_runner_live_smoke.py:13-17`
**Apply to:** parity test (uniform with established framework-self-test style)
```python
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
```

### Markdown doc style
**Source:** `docs/TEST-CODE-AUTHORING.md`
**Apply to:** `docs/LIBRARY-MODE.md`, `README.md` rewrite
- H1 title in plain title case (`# Library Mode — pytest-native MCP contract testing`)
- Em-dash for prose continuation; em-dash also acceptable in headings
- Triple-backtick fenced code with language tag (`bash`, `toml`, `python`)
- Inline-backtick + relative path for doc cross-links
- No emojis (CLAUDE.md guideline)
- Tables for resolution / surface enumerations

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/LIBRARY-MODE.md` (body content) | docs (operator reference) | static | No prior library-mode reference doc exists; outline is fresh per research §"`docs/LIBRARY-MODE.md` outline" lines 612-753 |
| `tests/framework/parity/test_cli_vs_pytest_route.py` — set-diff failure message | test (assertion-message composition) | n/a | No in-repo precedent for dict-divergence diff messages; composed in research §Pattern 1 |
| `tests/framework/parity/test_cli_vs_pytest_route.py` — D-02a defensive `assert outcomes_a` | test | n/a | New requirement from D-02a resolution; no precedent |
| `pyproject.toml` (conditional MODIFY) | config | toml | Existing `markers = [...]` block is the analog (`pyproject.toml:68-72`), but CONTEXT.md `<decisions>` default is framework-conftest registration; planner picks |
| `tests/framework/parity/__init__.py` | test (package marker) | n/a | Existing `tests/framework/smoke/` does NOT carry `__init__.py` — likely not needed; planner verifies pytest discovery |

## Metadata

**Analog search scope:**
- `tests/framework/` (all subdirs) — recursive `pytestmark` + subprocess pattern grep
- `src/mcp_test_framework/` (top-level only — ruled out `_runner.parse_junit_xml` reuse per research §Anti-Patterns)
- `docs/` (peer operator docs — `TEST-CODE-AUTHORING.md`, `EXTENDING.md`, `ERROR-STYLE.md`)
- `.planning/phases/*/[0-9]*-UAT.md` and `*-HUMAN-UAT.md` — UAT shape candidates
- `pyproject.toml` (ini options, markers, addopts)
- `README.md` (current top-of-file)

**Files scanned:** ~25 read or grep-sampled

**Pattern extraction date:** 2026-05-17

**Key resolved-or-deferred items:**
- Open Q §1 (config.test.yaml empty tools) — RESOLVED in CONTEXT.md D-02a (defensive assert + doc); pattern shown above
- Open Q §2 (cli.py `__main__` shape) — RESOLVED here: `cli.py:1787` has `if __name__ == "__main__": app()`; `[sys.executable, "-m", "mcp_test_framework.cli", "run", ...]` is the correct shape; NO `src/mcp_test_framework/__main__.py` exists (verified)
- Open Q §3 (REQ amendment plan-bundling) — research recommends bundling with the docs-rewrite plan; planner picks
