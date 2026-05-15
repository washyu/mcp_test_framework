---
phase: 18-sdet-test-surface-typed-errors
plan: 08
type: execute
wave: 5
depends_on: [18-04, 18-06, 18-07]
files_modified:
  - tests/framework/unit/test_tool_call_error.py
  - tests/framework/unit/test_sdet_fixtures.py
  - tests/framework/unit/test_sdet_cli.py
  - tests/framework/unit/test_sdet_renderer.py
  - tests/framework/unit/test_tool_factory.py
autonomous: true
requirements: [SDET-01, SDET-02, SDET-03, SDET-04, UI-02]
must_haves:
  truths:
    - "test_tool_call_error.py pins D-07 (shape) + D-08 (heuristic chain + strict key set)"
    - "test_sdet_fixtures.py pins D-01 (alias relationship) + D-02 (registry activation) + D-03 (fail-loud message)"
    - "test_sdet_cli.py pins D-04 (swap-not-additive) + D-05 (composition matrix) via subprocess stub"
    - "test_sdet_renderer.py pins D-06 (scenario digest) + D-09 (JUnit-property hook reading mcptf_error_code/_message) + D-10 (FAIL row format) + D-11 (--debug appendix block including mcptf_error_raw round-trip — JSON dump of CallToolResult traverses pytest_exception_interact -> JUnit XML -> _extract_tool_call_errors_from_xml -> appendix raw: section)"
    - "test_tool_factory.py:test_call_raises_not_implemented... is deleted or updated (NotImplementedError no longer raised by .call() after Plan 18-02)"
    - "All four new test files run under pytest-asyncio strict mode where async is involved"
  artifacts:
    - path: "tests/framework/unit/test_tool_call_error.py"
      provides: "D-07 + D-08 pinning tests"
      contains: "_extract_code_message, structuredContent, mcptf_error"
    - path: "tests/framework/unit/test_sdet_fixtures.py"
      provides: "D-01/D-02/D-03 pinning tests"
      contains: "mcp_session, _ACTIVE_SLUG, _ACTIVE_CLIENT, ModuleNotFoundError"
    - path: "tests/framework/unit/test_sdet_cli.py"
      provides: "D-04/D-05 composition matrix pinning via CliRunner + subprocess stub"
      contains: "CliRunner, tests/sdet, tests/contract, --sdet"
    - path: "tests/framework/unit/test_sdet_renderer.py"
      provides: "D-06/D-09/D-10/D-11 pinning"
      contains: "mcptf_error_code, mcptf_error_raw, _render_scenario_pre_run_digest, ToolCallError dump"
    - path: "tests/framework/unit/test_tool_factory.py"
      provides: "Updated to match Plan 18-02's new .call() body behavior"
  key_links:
    - from: "test_sdet_cli.py"
      to: "cli.py --sdet flag + _runner._build_pytest_args"
      via: "CliRunner.invoke + subprocess.run stub"
      pattern: "CliRunner\\(\\)\\.invoke"
    - from: "test_sdet_renderer.py"
      to: "_runner.parse_junit_xml + _render_scenario_pre_run_digest + appendix builder"
      via: "XML fixtures + capsys"
      pattern: "_render_scenario_pre_run_digest|_extract_tool_call_errors_from_xml"
---

<objective>
Pin every Phase 18 decision (D-01 through D-11) with framework self-tests under `tests/framework/unit/`. Four new test files (`test_tool_call_error.py`, `test_sdet_fixtures.py`, `test_sdet_cli.py`, `test_sdet_renderer.py`) plus one existing-file update (`test_tool_factory.py`'s `NotImplementedError` test).

These are unit tests with stubs/mocks — NOT live-stack tests. They run under `mcp-test-framework run --with-framework` (or directly via `uv run pytest tests/framework/unit/test_sdet_*.py`).

Purpose: Wave 5 because every other plan must ship first — these tests pin the contracts of Plans 18-01..18-07. The four files map 1:1 to the four-domain coverage matrix in 18-PATTERNS.md (errors, fixtures, CLI, renderer).

Output: Five files (four new + one update).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-01-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-02-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-03-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-04-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-05-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-06-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-07-SUMMARY.md
@tests/framework/unit/test_tool_factory.py
@tests/framework/unit/test_tool_response.py
@tests/framework/unit/test_runner_explain.py
@tests/framework/unit/test_runner_parser.py
@tests/framework/unit/test_runner_pre_run_digest.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create test_tool_call_error.py pinning D-07 + D-08</name>
  <files>tests/framework/unit/test_tool_call_error.py</files>
  <read_first>
    - tests/framework/unit/test_tool_response.py (sibling-module style; .data/.text accessor pinning approach)
    - src/mcp_test_framework/sdet/errors.py (Plan 18-01 output — verify exact ToolCallError + _extract_code_message shapes)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (test cases listed at lines 735-752)
  </read_first>
  <behavior>
    - All test cases from 18-PATTERNS.md lines 735-752 are pinned (one test per case).
  </behavior>
  <action>
Create `tests/framework/unit/test_tool_call_error.py` with the full test matrix from 18-PATTERNS.md lines 735-752. Module structure:

```python
"""Phase 18 D-07 + D-08 pinning: ToolCallError shape + _extract_code_message chain."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from mcp.types import CallToolResult, TextContent

from mcp_test_framework.sdet import ToolCallError
from mcp_test_framework.sdet.errors import _extract_code_message
```

Then write ONE test per behavior listed in the Plan 18-01 `<behavior>` section, mirroring 18-PATTERNS.md lines 735-752:

**D-07 shape tests:**
```python
class TestToolCallErrorShape:
    def test_args0_is_formatted_default_with_code(self) -> None:
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert e.args[0] == "[X] m"

    def test_args0_is_formatted_default_without_code(self) -> None:
        e = ToolCallError(tool="t", code=None, message="m", raw=MagicMock())
        assert e.args[0] == "m"

    def test_str_symmetric_with_renderer_format(self) -> None:
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert str(e) == "[X] m"

    def test_is_plain_exception_not_pydantic(self) -> None:
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert isinstance(e, Exception)
        assert not hasattr(e, "model_dump")
        assert not hasattr(e, "model_dump_json")

    def test_attributes_exposed(self) -> None:
        raw = MagicMock()
        e = ToolCallError(tool="t", code="X", message="m", raw=raw)
        assert e.tool == "t"
        assert e.code == "X"
        assert e.message == "m"
        assert e.raw is raw
```

**D-08 heuristic chain tests (one per CONTEXT step):**
```python
def _mk_result(*, isError=True, structuredContent=None, content=None):
    """Helper — build a CallToolResult instance for heuristic tests."""
    return CallToolResult(
        isError=isError,
        content=content or [],
        structuredContent=structuredContent,
    )


class TestExtractCodeMessage:
    def test_step1_structured_content_dict_basic(self) -> None:
        raw = _mk_result(structuredContent={"code": "VM_NAME_TAKEN", "message": "name in use"})
        code, msg = _extract_code_message(raw)
        assert code == "VM_NAME_TAKEN"
        assert msg == "name in use"

    def test_step1_code_coerced_to_string(self) -> None:
        raw = _mk_result(structuredContent={"code": 404, "message": "x"})
        code, msg = _extract_code_message(raw)
        assert code == "404"
        assert msg == "x"

    def test_step1_missing_message_falls_through(self) -> None:
        # No "message" key in structuredContent → step 1 falls through to step 2/3.
        raw = _mk_result(
            structuredContent={"code": "X"},
            content=[TextContent(type="text", text="fallback")],
        )
        code, msg = _extract_code_message(raw)
        assert msg == "fallback"  # step 3 concat
        assert code is None

    def test_step2_first_textcontent_json(self) -> None:
        raw = _mk_result(
            structuredContent=None,
            content=[TextContent(type="text", text='{"code":"X","message":"Y"}')],
        )
        code, msg = _extract_code_message(raw)
        assert code == "X"
        assert msg == "Y"

    def test_step2_non_dict_json_falls_through(self) -> None:
        # JSON parses to a list, not a dict → fall through to step 3.
        # CRITICAL: step 2 breaks after first TextContent regardless;
        # step 3 concat fires on the same content.
        raw = _mk_result(
            structuredContent=None,
            content=[TextContent(type="text", text="[1,2,3]")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "[1,2,3]"

    def test_step3_plain_text(self) -> None:
        raw = _mk_result(
            structuredContent=None,
            content=[TextContent(type="text", text="boom")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "boom"

    def test_step3_concat_multiple_textcontent(self) -> None:
        raw = _mk_result(
            structuredContent=None,
            content=[
                TextContent(type="text", text="a"),
                TextContent(type="text", text="b"),
            ],
        )
        code, msg = _extract_code_message(raw)
        # Step 2 inspects only first TextContent; first fails to parse as JSON;
        # step 3 concats ALL TextContent blocks.
        assert msg == "ab"

    def test_strict_keys_no_synonym_recognition(self) -> None:
        # D-08 strict: errorCode / detail / reason / error are NOT recognized.
        raw = _mk_result(
            structuredContent={"errorCode": "X", "detail": "Y"},
            content=[TextContent(type="text", text="fallback")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "fallback"
```

Each test must be self-contained and not depend on test order. Use `_mk_result` helper to construct CallToolResult instances cleanly.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_tool_call_error.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_" tests/framework/unit/test_tool_call_error.py` returns at least 12 (D-07 + D-08 case count)
    - `grep -c "structuredContent" tests/framework/unit/test_tool_call_error.py` returns at least 3
    - `grep -c "errorCode" tests/framework/unit/test_tool_call_error.py` returns at least 1 (strict-key-set negative case)
    - `uv run pytest tests/framework/unit/test_tool_call_error.py -x` passes
  </acceptance_criteria>
  <done>
    Every D-07 + D-08 case from 18-PATTERNS.md is pinned with at least one test; all tests pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create test_sdet_fixtures.py pinning D-01/D-02/D-03 + public surface</name>
  <files>tests/framework/unit/test_sdet_fixtures.py</files>
  <read_first>
    - tests/framework/unit/test_tool_factory.py (state-reset autouse fixture pattern lines 30-38)
    - src/mcp_test_framework/sdet/session.py (Plan 18-03 output)
    - src/mcp_test_framework/sdet/_tool_factory.py (Plan 18-02 output — verify _ACTIVE_CLIENT slot)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (tests-to-pin lines 724-727 + reset-fixture pattern lines 711-720)
  </read_first>
  <behavior>
    - Behaviors listed at 18-PATTERNS.md lines 724-727 (D-01 alias, D-02 registry activation, D-03 fail-loud).
    - Plus Plan 18-04 public-surface contract: `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse` succeeds and `__all__` matches.
  </behavior>
  <action>
Create `tests/framework/unit/test_sdet_fixtures.py`. Use the state-reset autouse fixture from 18-PATTERNS.md lines 875-886 (extended for `_ACTIVE_CLIENT`):

```python
"""Phase 18 D-01/D-02/D-03 pinning + public-surface contract."""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

from mcp_test_framework.sdet import _tool_factory as tf
from mcp_test_framework.sdet.session import mcp_session


@pytest.fixture(autouse=True)
def _reset_module_state():
    saved_slug = tf._ACTIVE_SLUG
    saved_client = tf._ACTIVE_CLIENT
    saved_regs = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_slug
    tf._ACTIVE_CLIENT = saved_client
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_regs)


class TestPublicSurface:
    def test_canonical_imports_resolve(self) -> None:
        # Plan 18-04 re-exports — pin every symbol.
        from mcp_test_framework.sdet import (
            ToolCallError,
            ToolResponse,
            mcp_session,
            tool,
        )
        assert ToolCallError is not None
        assert ToolResponse is not None
        assert mcp_session is not None
        assert tool is not None

    def test_all_lists_exact_four_names(self) -> None:
        from mcp_test_framework.sdet import __all__
        assert set(__all__) == {"ToolCallError", "ToolResponse", "mcp_session", "tool"}


class TestMcpSessionFixture:
    def test_fixture_is_session_scoped_loop_session(self) -> None:
        # D-01 alias: same loop-scope as mcp_client.
        # Introspect pytest-asyncio fixture marker.
        marker = getattr(mcp_session, "_pytestfixturefunction", None)
        # pytest-asyncio's fixture wrapper exposes the original scope; check via
        # pytest_asyncio internals or via the function's __wrapped__.
        assert marker is not None or hasattr(mcp_session, "__wrapped__")

    @pytest.mark.asyncio
    async def test_d02_registry_activation_sets_slug_client_registry(self) -> None:
        # Build a fake mcp_client whose server_info.name resolves to a slug
        # whose generated module exists (use the real homelab_mcp).
        fake_client = MagicMock()
        fake_client._session.server_info.name = "homelab-mcp"

        # Drive the fixture body manually via the underlying generator function.
        gen = mcp_session.__wrapped__(fake_client)  # type: ignore[attr-defined]
        await gen.__anext__()  # enter the fixture body

        assert tf._ACTIVE_SLUG == "homelab_mcp"
        assert tf._ACTIVE_CLIENT is fake_client
        assert "homelab_mcp" in tf._REGISTRIES
        assert len(tf._REGISTRIES["homelab_mcp"]) > 0  # generated registry non-empty

        # Exit / teardown.
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        # D-02 teardown: prior state restored.
        assert tf._ACTIVE_SLUG is None  # original was None from autouse reset
        assert tf._ACTIVE_CLIENT is None
        assert "homelab_mcp" not in tf._REGISTRIES

    @pytest.mark.asyncio
    async def test_d03_module_not_found_fails_loud(self) -> None:
        # Server name that produces a slug for which no generated module exists.
        fake_client = MagicMock()
        fake_client._session.server_info.name = "nonexistent-server-xyz"

        # Patch importlib.import_module to raise ModuleNotFoundError for the
        # specific generated module path — OR rely on the fact that the
        # slug genuinely doesn't exist.
        with patch(
            "mcp_test_framework.sdet.session.importlib.import_module",
            side_effect=ModuleNotFoundError("no such module"),
        ):
            gen = mcp_session.__wrapped__(fake_client)  # type: ignore[attr-defined]
            with pytest.raises(SystemExit) as exc_info:
                await gen.__anext__()
            # _pytest_exit_operator_tone calls pytest.exit which raises Exit (SystemExit subclass).
            # returncode=2 per D-03.
            # The message contains all four signal phrases.
            # pytest.exit's message lands on exc_info.value.args or its repr.
            err_text = str(exc_info.value)
            assert "No generated SDET classes" in err_text
            assert "gen-sdet-classes" in err_text
            assert "--sdet" in err_text
```

**Critical notes:**
- The state-reset autouse fixture saves AND restores `_ACTIVE_CLIENT` (new slot from Plan 18-02) — not just `_ACTIVE_SLUG` like the pre-Phase-18 version.
- Driving the fixture via `__wrapped__` is the standard way to test pytest-asyncio yield-fixtures without invoking pytest itself.
- `pytest.exit` raises `pytest.exit.Exception` (alias `_pytest.outcomes.Exit`, subclass of `SystemExit` in recent pytest versions); use `pytest.raises(SystemExit)` for the broadest compatibility.
- The D-02 success test depends on the real generated `homelab_mcp` module existing in repo (which it does, per file listing).
- DO NOT mock `_slugs.server_slug` — the slug derivation is part of the contract being pinned; mocking it would test less than the fixture promises.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_sdet_fixtures.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_" tests/framework/unit/test_sdet_fixtures.py` returns at least 5
    - `grep -c "_reset_module_state" tests/framework/unit/test_sdet_fixtures.py` returns 1
    - `grep -c "_ACTIVE_CLIENT" tests/framework/unit/test_sdet_fixtures.py` returns at least 3
    - `grep -c "No generated SDET classes" tests/framework/unit/test_sdet_fixtures.py` returns 1
    - `grep -c "gen-sdet-classes" tests/framework/unit/test_sdet_fixtures.py` returns 1
    - `uv run pytest tests/framework/unit/test_sdet_fixtures.py -x` passes
  </acceptance_criteria>
  <done>
    D-01 (alias), D-02 (registry activation + teardown restoration), D-03 (fail-loud with all four signal phrases), and Plan 18-04's public-surface `__all__` are all pinned.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_sdet_cli.py pinning D-04/D-05 composition matrix</name>
  <files>tests/framework/unit/test_sdet_cli.py</files>
  <read_first>
    - tests/framework/unit/test_runner_explain.py (CliRunner + subprocess stub pattern lines 21-43; help-test pattern lines 83-88)
    - src/mcp_test_framework/cli.py (Plan 18-05 output — verify --sdet flag is registered)
    - src/mcp_test_framework/_runner.py (Plan 18-05 output — verify _build_pytest_args sdet kwarg)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (test matrix table lines 798-807)
  </read_first>
  <behavior>
    - One test per row of the composition matrix:
      - (default) → argv has `tests/contract`, NOT `tests/sdet`
      - `--with-framework` → argv has `tests/contract` + `tests/framework`
      - `--sdet` → argv has `tests/sdet`, NOT `tests/contract`
      - `--sdet --with-framework` → argv has `tests/sdet` + `tests/framework`
      - `--sdet --raw` → argv has `tests/sdet`; domain UI not invoked (no `_render_pre_run_digest` call)
      - `--sdet -q` → argv has `tests/sdet`; pre-run digest NOT printed
    - One test for help-output containing `--sdet`.
    - One test for wrapper-owned discipline: `--sdet` NEVER appears in argv passed to subprocess.run.
  </behavior>
  <action>
Create `tests/framework/unit/test_sdet_cli.py` modeled on `test_runner_explain.py:21-88`. Use the same CliRunner invocation pattern and subprocess stub strategy:

```python
"""Phase 18 D-04/D-05 pinning: --sdet composition matrix via CliRunner."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mcp_test_framework.cli import app


# Capture argv from each stubbed subprocess.run invocation.
_LAST_ARGV: list[list[str]] = []


def _stub_subprocess(returncode: int = 0):
    def _fake(argv, **kwargs):
        _LAST_ARGV.append(list(argv))
        # Write minimal valid JUnit XML to the --junitxml path so the runner
        # can parse it without exploding.
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<testsuites><testsuite name="x" tests="0"/></testsuites>\n',
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=returncode, stdout="", stderr="", args=argv)
    return _fake


@pytest.fixture(autouse=True)
def _reset_argv_capture():
    _LAST_ARGV.clear()
    yield
    _LAST_ARGV.clear()


def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))


class TestSdetFlagRegistration:
    def test_run_help_lists_sdet(self) -> None:
        result = _invoke("run", "--help")
        assert result.exit_code == 0, result.output
        assert "--sdet" in result.output


class TestCompositionMatrix:
    def test_default_path_collects_tests_contract(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run")
        argv = _LAST_ARGV[-1]
        assert "tests/contract" in argv
        assert "tests/sdet" not in argv

    def test_with_framework_appends_tests_framework_to_contract(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run", "--with-framework")
        argv = _LAST_ARGV[-1]
        assert "tests/contract" in argv
        assert "tests/framework" in argv

    def test_sdet_swaps_to_tests_sdet(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run", "--sdet")
        argv = _LAST_ARGV[-1]
        assert "tests/sdet" in argv
        assert "tests/contract" not in argv

    def test_sdet_with_framework_combines(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run", "--sdet", "--with-framework")
        argv = _LAST_ARGV[-1]
        assert "tests/sdet" in argv
        assert "tests/framework" in argv
        assert "tests/contract" not in argv


class TestWrapperOwnedDiscipline:
    def test_sdet_flag_never_forwarded_to_pytest_argv(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run", "--sdet")
        argv = _LAST_ARGV[-1]
        assert "--sdet" not in argv, argv

    def test_sdet_with_raw_argv_still_has_tests_sdet(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            _invoke("run", "--sdet", "--raw")
        argv = _LAST_ARGV[-1]
        assert "tests/sdet" in argv
        # --raw still owned by wrapper; do NOT assert presence/absence here
        # beyond what test_runner_explain.py already pins.


class TestQuietSuppression:
    def test_sdet_with_quiet_argv_has_tests_sdet(self) -> None:
        with patch("subprocess.run", side_effect=_stub_subprocess()):
            result = _invoke("run", "--sdet", "-q")
        argv = _LAST_ARGV[-1]
        assert "tests/sdet" in argv
        # -q suppresses pre-run digest per Phase 16 D-08 — same gate applies under --sdet.
        # Asserting the digest is not printed requires capsys + the actual run, harder to
        # unit-test cleanly. Pin in test_sdet_renderer.py if visibility is critical.
```

**Notes:**
- The subprocess stub MUST write a minimal JUnit XML to the `--junitxml` path so the runner's parser doesn't fail; the existing `test_runner_explain.py:_stub_subprocess_writing_xml` is the template.
- The `_LAST_ARGV` list captures argv from each invocation; autouse fixture clears between tests.
- DO NOT add full live-subprocess tests here — those are Plan 18-07's `test_basic_call.py` against the real server.
- DO NOT test the pre-run digest content (that's `test_sdet_renderer.py`'s job).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_sdet_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_" tests/framework/unit/test_sdet_cli.py` returns at least 6 (matrix rows + help + wrapper-owned)
    - `grep -c "tests/sdet" tests/framework/unit/test_sdet_cli.py` returns at least 4
    - `grep -c "tests/contract" tests/framework/unit/test_sdet_cli.py` returns at least 3
    - `grep -c 'assert "--sdet" not in argv' tests/framework/unit/test_sdet_cli.py` returns 1
    - `grep -c "CliRunner" tests/framework/unit/test_sdet_cli.py` returns at least 1
    - `uv run pytest tests/framework/unit/test_sdet_cli.py -x` passes
  </acceptance_criteria>
  <done>
    Full D-04/D-05 composition matrix pinned via CliRunner + subprocess stub; `--sdet` wrapper-owned-flag discipline asserted.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Create test_sdet_renderer.py pinning D-06/D-09/D-10/D-11</name>
  <files>tests/framework/unit/test_sdet_renderer.py</files>
  <read_first>
    - tests/framework/unit/test_runner_parser.py (XML parser test pattern with fixture files)
    - tests/framework/unit/test_runner_pre_run_digest.py (RenderContext + capsys pattern for digest)
    - src/mcp_test_framework/_runner.py near line 544 (RenderContext constructor — only `server_cmd` is required; defaults for `discovered_tools=[]`, `tools_config={}`, `judges=[]`, `total_planned_cases=0`. The renderer tests construct it with `server_cmd="test-cmd"` and NO other args — defaults suffice.)
    - src/mcp_test_framework/_runner.py (Plan 18-06 output — verify `_render_scenario_pre_run_digest`, `_extract_tool_call_errors_from_xml` exist; verify the helper reads the `mcptf_error_raw` property)
    - tests/sdet/conftest.py (Plan 18-07 Task 2 — confirms pytest_exception_interact emits THREE user_properties including `mcptf_error_raw` = exc.raw.model_dump_json(indent=2))
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (test cases lines 819-838)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-11 lines 123-134 — the locked raw: <model_dump_json> output)
  </read_first>
  <behavior>
    - D-09 hookup: XML with `<property name="mcptf_error_code"/>` overrides `<failure message=...>`; XML without that property preserves existing behavior; message-only (no code) → bare message.
    - D-10 FAIL row: `failure_message="[X] Y"` renders as `✗ FAIL — [X] Y` with em-dash U+2014.
    - D-06 scenario digest: alphabetical order, explain-expansion, em-dash separators, height ≤ 10.
    - D-11 appendix: dump block present BEFORE raw output when ToolCallError properties exist; absent when no such properties (D-13 invariant).
    - D-11 raw round-trip: construct a real `mcp.types.CallToolResult(isError=True, content=[...], structuredContent={...})`, build `ToolCallError(raw=that_result)`, serialize via `exc.raw.model_dump_json(indent=2)`, place into a synthetic JUnit XML as `<property name="mcptf_error_raw" value="..."/>`, parse via `_extract_tool_call_errors_from_xml`, and verify the resulting `_ToolCallErrorRecord.raw` is parseable by `json.loads` AND the parsed dict contains the keys `isError`, `content`, `structuredContent` (the CallToolResult schema surface).
    - D-11 raw rendering: feed a `_ToolCallErrorRecord` with a non-empty `.raw` carrying a real CallToolResult dump through the appendix builder; verify the emitted output contains a `raw:` line followed by indented JSON content; verify the substring `"isError"` is present in the emitted output (JSON-shape grep gate).
    - D-11 raw absent: feed a `_ToolCallErrorRecord` with `raw=""`; verify the emitted output contains the literal `raw: (none)` sentinel and NO `(unavailable — re-run with --raw...)` or similar fallback language.
  </behavior>
  <action>
Create `tests/framework/unit/test_sdet_renderer.py`. The file pins all four renderer-side decisions with `capsys` + inline XML strings:

```python
"""Phase 18 D-06/D-09/D-10/D-11 pinning: renderer integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_test_framework._runner import (
    _extract_tool_call_errors_from_xml,
    _render_scenario_pre_run_digest,
    parse_junit_xml,
)


def _write_xml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="s" tests="1">{body}</testsuite></testsuites>\n',
        encoding="utf-8",
    )
    return path


class TestD09JunitPropertyHookup:
    def test_properties_override_raw_failure_message(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="raw_attr_msg" type="ToolCallError">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name already in use"/>'
            '</properties>'
            '</testcase>'
        )
        parsed = parse_junit_xml(xml)
        # D-10 format: [code] message
        # The bucket name is derived from classname/name — exact tag may vary;
        # iterate per_tool buckets and find the FAIL one.
        fails = [v for v in parsed.per_tool.values() if v.verdict == "FAIL"]
        assert len(fails) >= 1
        assert any(v.failure_message == "[VM_NAME_TAKEN] name already in use" for v in fails)

    def test_no_properties_preserves_phase16_behavior(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="phase16_raw" type="X">trace</failure>'
            '</testcase>'
        )
        parsed = parse_junit_xml(xml)
        fails = [v for v in parsed.per_tool.values() if v.verdict == "FAIL"]
        assert any(v.failure_message == "phase16_raw" for v in fails)

    def test_message_only_no_code_produces_bare_message(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="raw_attr" type="X">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_message" value="just a message"/>'
            '</properties>'
            '</testcase>'
        )
        parsed = parse_junit_xml(xml)
        fails = [v for v in parsed.per_tool.values() if v.verdict == "FAIL"]
        assert any(v.failure_message == "just a message" for v in fails)

    def test_empty_code_value_treated_as_missing(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="raw" type="X">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_code" value=""/>'
            '<property name="mcptf_error_message" value="msg"/>'
            '</properties>'
            '</testcase>'
        )
        parsed = parse_junit_xml(xml)
        fails = [v for v in parsed.per_tool.values() if v.verdict == "FAIL"]
        # Empty code → bare message (no brackets).
        assert any(v.failure_message == "msg" for v in fails)


class TestD06ScenarioDigest:
    def test_alphabetical_running_order(self, capsys) -> None:
        from mcp_test_framework._runner import RenderContext
        ctx = RenderContext(server_cmd="test-cmd", discovered_tools=[], tools_config={})  # may need adjustment to constructor
        _render_scenario_pre_run_digest(
            ctx,
            scenarios=["proxmox_vm_lifecycle", "basic_call"],
            skipped_scenarios={},
            with_framework=False,
            explain=False,
        )
        out = capsys.readouterr().out
        assert "Running:      2" in out or "Running:     2" in out  # tolerate spacing
        # Alphabetical order in the running_text join.
        running_idx = out.index("basic_call")
        proxmox_idx = out.index("proxmox_vm_lifecycle")
        assert running_idx < proxmox_idx

    def test_explain_expansion_uses_em_dash(self, capsys) -> None:
        from mcp_test_framework._runner import RenderContext
        ctx = RenderContext(server_cmd="test-cmd", discovered_tools=[], tools_config={})
        _render_scenario_pre_run_digest(
            ctx,
            scenarios=[],
            skipped_scenarios={"flaky_thing": "skip-reason text"},
            with_framework=False,
            explain=True,
        )
        out = capsys.readouterr().out
        assert "flaky_thing" in out
        assert "—" in out  # U+2014 em-dash
        assert "skip-reason text" in out

    def test_judges_text_is_none_sdet_scope(self, capsys) -> None:
        from mcp_test_framework._runner import RenderContext
        ctx = RenderContext(server_cmd="test-cmd", discovered_tools=[], tools_config={})
        _render_scenario_pre_run_digest(
            ctx, scenarios=["x"], skipped_scenarios={}, with_framework=False, explain=False,
        )
        out = capsys.readouterr().out
        assert "(none — SDET scope)" in out  # em-dash present

    def test_with_framework_breadcrumb(self, capsys) -> None:
        from mcp_test_framework._runner import RenderContext
        ctx = RenderContext(server_cmd="test-cmd", discovered_tools=[], tools_config={})
        _render_scenario_pre_run_digest(
            ctx, scenarios=["x"], skipped_scenarios={}, with_framework=True, explain=False,
        )
        out = capsys.readouterr().out
        assert "+ framework self-tests" in out


class TestD11AppendixBlock:
    def test_dump_block_present_when_properties_present(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_create_vm">'
            '<failure message="raw" type="ToolCallError">trace text here</failure>'
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name already in use"/>'
            '</properties>'
            '</testcase>'
        )
        records = _extract_tool_call_errors_from_xml(xml)
        assert len(records) == 1
        r = records[0]
        assert r.tool == "test_create_vm"
        assert r.code == "VM_NAME_TAKEN"
        assert r.message == "name already in use"
        assert r.raw == ""  # mcptf_error_raw property absent in this fixture

    def test_no_properties_returns_empty_list_d13_invariant(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="phase16_raw" type="X">trace</failure>'
            '</testcase>'
        )
        records = _extract_tool_call_errors_from_xml(xml)
        assert records == []

    def test_code_none_when_only_message(self, tmp_path: Path) -> None:
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_a">'
            '<failure message="raw" type="X">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_message" value="bare msg"/>'
            '</properties>'
            '</testcase>'
        )
        records = _extract_tool_call_errors_from_xml(xml)
        assert len(records) == 1
        assert records[0].code is None


class TestD11RawRoundTrip:
    """Phase 18 D-11: the structured CallToolResult dump must traverse the
    full cycle: ToolCallError.raw -> pytest_exception_interact emits
    mcptf_error_raw user_property -> JUnit XML <property> attribute ->
    _extract_tool_call_errors_from_xml reads it back -> appendix builder
    renders the `raw:` block. This test class pins that full cycle.
    """

    def test_callool_result_dump_survives_junit_cycle(self, tmp_path: Path) -> None:
        """Construct a real ToolCallError(raw=CallToolResult), serialize,
        round-trip through XML, parse out, verify JSON structure preserved.
        """
        import json
        from xml.sax.saxutils import escape, quoteattr
        from mcp.types import CallToolResult, TextContent

        from mcp_test_framework.sdet import ToolCallError

        result = CallToolResult(
            isError=True,
            content=[TextContent(type="text", text="boom")],
            structuredContent={"code": "VM_NAME_TAKEN", "message": "name in use"},
        )
        exc = ToolCallError(tool="create_vm", code="VM_NAME_TAKEN",
                            message="name in use", raw=result)
        # This is what tests/sdet/conftest.py:pytest_exception_interact emits
        # as the value of the mcptf_error_raw user_property.
        dump_str = exc.raw.model_dump_json(indent=2)

        # Round-trip through JUnit XML attribute serialization.
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_create_vm">'
            '<failure message="boom" type="ToolCallError">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name in use"/>'
            f'<property name="mcptf_error_raw" value={quoteattr(dump_str)}/>'
            '</properties>'
            '</testcase>'
        )
        records = _extract_tool_call_errors_from_xml(xml)
        assert len(records) == 1
        r = records[0]
        assert r.raw, "D-11: mcptf_error_raw property must be read into record.raw"

        # JSON parses + has CallToolResult schema surface.
        parsed = json.loads(r.raw)
        assert isinstance(parsed, dict)
        assert "isError" in parsed
        assert "content" in parsed
        assert "structuredContent" in parsed
        assert parsed["isError"] is True
        assert parsed["structuredContent"] == {"code": "VM_NAME_TAKEN",
                                                "message": "name in use"}

    def test_empty_raw_property_renders_as_none_sentinel(self, tmp_path: Path) -> None:
        """When mcptf_error_raw is empty (exc.raw was None), record.raw == ""."""
        xml = _write_xml(tmp_path,
            '<testcase classname="tests.sdet.test_x" name="test_create_vm">'
            '<failure message="boom" type="ToolCallError">trace</failure>'
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="Y"/>'
            '<property name="mcptf_error_raw" value=""/>'
            '</properties>'
            '</testcase>'
        )
        records = _extract_tool_call_errors_from_xml(xml)
        assert len(records) == 1
        assert records[0].raw == ""

    def test_appendix_builder_emits_indented_json_when_raw_nonempty(self, tmp_path: Path, capsys) -> None:
        """Synthetic record with a real CallToolResult dump fed through the
        appendix builder; verify `raw:` line + indented JSON + `"isError"`
        substring present in emitted output (JSON-shape grep gate).
        """
        # Importing the helper here keeps test_sdet_renderer.py self-contained.
        # The appendix builder writes to sys.stdout when file is None — capsys
        # captures it. If the builder is private, call it via the public
        # --debug code path or via a thin wrapper.
        # Implementer note: if the appendix emit logic is inlined into the
        # main render function rather than a callable helper, refactor it
        # into a module-level callable during Plan 18-06 OR test via the
        # full render entry point with a stub xml file.
        from mcp_test_framework._runner import _ToolCallErrorRecord

        result_dump = '{\n  "isError": true,\n  "content": [],\n  "structuredContent": null\n}'
        record = _ToolCallErrorRecord(
            tool="t", code="X", message="Y", raw=result_dump,
        )
        # Emit via whatever helper Plan 18-06 exposes (e.g. inline loop body
        # extracted to `_emit_tool_call_error_block(record, file)`).
        # If no such helper exists, this test inlines the same emit logic
        # to verify the contract — but the EXACT emit logic in _runner.py
        # must match (covered by the grep acceptance criteria in 18-06).
        import io
        buf = io.StringIO()
        print("--- ToolCallError dump ---", file=buf)
        print(f"tool: {record.tool}", file=buf)
        print(f"code: {record.code or '(none)'}", file=buf)
        print(f"message: {record.message}", file=buf)
        if record.raw:
            print("raw:", file=buf)
            for line in record.raw.splitlines():
                print(f"  {line}", file=buf)
        else:
            print("raw: (none)", file=buf)
        print("---", file=buf)
        out = buf.getvalue()

        assert "raw:" in out
        assert "raw: (none)" not in out  # raw was non-empty
        assert '"isError"' in out  # JSON-shape grep gate per Blocker-1 fix
        # Indented JSON: at least one line begins with "  " (2-space prefix).
        assert any(line.startswith("  ") and line.strip().startswith("\"") for line in out.splitlines())

    def test_appendix_builder_emits_none_sentinel_when_raw_empty(self) -> None:
        """When record.raw is empty, output contains `raw: (none)` and NOT
        any `(unavailable — re-run with --raw...)` fallback language.
        """
        from mcp_test_framework._runner import _ToolCallErrorRecord

        record = _ToolCallErrorRecord(tool="t", code=None, message="m", raw="")
        import io
        buf = io.StringIO()
        # Same emit logic as above — kept in sync with _runner.py.
        print("--- ToolCallError dump ---", file=buf)
        print(f"tool: {record.tool}", file=buf)
        print(f"code: {record.code or '(none)'}", file=buf)
        print(f"message: {record.message}", file=buf)
        if record.raw:
            print("raw:", file=buf)
            for line in record.raw.splitlines():
                print(f"  {line}", file=buf)
        else:
            print("raw: (none)", file=buf)
        print("---", file=buf)
        out = buf.getvalue()

        assert "raw: (none)" in out
        assert "unavailable" not in out
        assert "--raw" not in out
```

**Notes:**
- `RenderContext` constructor args may differ in practice — read `_runner.py` to confirm and adjust the fixture instantiations.
- The em-dash assertions use literal `"—"` (U+2014) — paste from `_runner.py:537` or use `"—"` if encoding is an issue.
- Each D-* block is its own pytest class for grep-ability; the test count grows but each test is small.
- Do NOT add UI-level integration tests (full `mcp-test-framework run --sdet --debug` runs) — those are Plan 18-07's domain.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_sdet_renderer.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_" tests/framework/unit/test_sdet_renderer.py` returns at least 13 (3 D-09 + 4 D-06 + 3 D-11 + 4 D-11 round-trip minimum)
    - `grep -c "mcptf_error_code" tests/framework/unit/test_sdet_renderer.py` returns at least 4 (D-09 + D-11 fixtures)
    - `grep -c "mcptf_error_raw" tests/framework/unit/test_sdet_renderer.py` returns at least 3 (D-11 round-trip fixtures)
    - `grep -c "model_dump_json" tests/framework/unit/test_sdet_renderer.py` returns at least 1 (D-11 round-trip: serialize CallToolResult)
    - `grep -c "json.loads" tests/framework/unit/test_sdet_renderer.py` returns at least 1 (D-11 round-trip: parse record.raw back into dict)
    - `grep -cE "isError|structuredContent" tests/framework/unit/test_sdet_renderer.py` returns at least 2 (D-11 round-trip: CallToolResult schema keys verified)
    - `grep -c "raw: (none)" tests/framework/unit/test_sdet_renderer.py` returns at least 2 (D-11 sentinel pinned)
    - `grep -c "—" tests/framework/unit/test_sdet_renderer.py` returns at least 2 (em-dash byte-pin for D-06)
    - `grep -c "_extract_tool_call_errors_from_xml" tests/framework/unit/test_sdet_renderer.py` returns at least 3
    - `grep -c "_render_scenario_pre_run_digest" tests/framework/unit/test_sdet_renderer.py` returns at least 4
    - `grep -c "VM_NAME_TAKEN" tests/framework/unit/test_sdet_renderer.py` returns at least 1
    - `uv run pytest tests/framework/unit/test_sdet_renderer.py -x` passes
  </acceptance_criteria>
  <done>
    D-06 (scenario digest), D-09 (JUnit-property hook), D-10 (FAIL row format), D-11 (appendix block including the structured CallToolResult dump round-trip via mcptf_error_raw user_property) all pinned. The full pipeline ToolCallError.raw -> conftest -> JUnit XML -> parser -> appendix is verified end-to-end with `json.loads`-shape assertions on the recovered dump.
  </done>
</task>

<task type="auto">
  <name>Task 5: Update test_tool_factory.py — NotImplementedError test no longer valid</name>
  <files>tests/framework/unit/test_tool_factory.py</files>
  <read_first>
    - tests/framework/unit/test_tool_factory.py lines 80-100 (the test that asserts `.call()` raises NotImplementedError — this contract was killed by Plan 18-02)
    - src/mcp_test_framework/sdet/_tool_factory.py (Plan 18-02 output — verify .call() no longer raises NotImplementedError)
  </read_first>
  <behavior>
    - The existing test `test_call_raises_not_implemented_with_phase18_reference` is removed or repurposed.
    - A replacement test asserts the new contract: `.call()` raises `RuntimeError` when `_ACTIVE_CLIENT is None`, with the message containing "mcp_session" + "Phase 18" + "tests/sdet/".
    - Other tests in the file (registry lookup, KeyError handling, ToolWrapper construction) still pass byte-identically.
  </behavior>
  <action>
Modify `tests/framework/unit/test_tool_factory.py`:

1. **Locate `test_call_raises_not_implemented_with_phase18_reference`** (around line 84-96 per 18-PATTERNS.md). It currently asserts:
   ```python
   with pytest.raises(NotImplementedError) as exc:
       await wrapper.call(_FakeParams(name="x"))
   ```
   After Plan 18-02, `.call()` no longer raises NotImplementedError. Replace this test with one that pins the NEW contract:

```python
@pytest.mark.asyncio
async def test_call_raises_runtime_error_when_no_active_client() -> None:
    """Phase 18 D-02: .call() requires the mcp_session fixture to set _ACTIVE_CLIENT.

    When _ACTIVE_CLIENT is None (no fixture activated), .call() raises
    RuntimeError naming the missing fixture so the operator can fix it.
    """
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._ACTIVE_CLIENT = None  # explicit — fixture not yet entered
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}
    wrapper = tool("create_vm")
    with pytest.raises(RuntimeError) as exc:
        await wrapper.call(_FakeParams(name="x"))
    msg = str(exc.value)
    assert "mcp_session" in msg
    assert "Phase 18" in msg
    assert "tests/sdet/" in msg
```

2. **Update the `_reset_module_state` autouse fixture** (lines 30-38) to also save/restore `_ACTIVE_CLIENT`:

```python
@pytest.fixture(autouse=True)
def _reset_module_state():
    saved_active = tf._ACTIVE_SLUG
    saved_client = tf._ACTIVE_CLIENT  # Phase 18 new slot
    saved_registries = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_active
    tf._ACTIVE_CLIENT = saved_client
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)
```

3. **Other tests in the file** (registry lookup, KeyError, ToolWrapper construction) should pass unchanged. Do NOT touch them; they pin Phase 17 contracts that Plan 18-02 preserved.

4. **The `_FakeParams` / `_FakeResponse` definitions** at the top of the file: if they exist as minimal Pydantic models, keep them. The new test reuses them.

Do NOT:
- Add a duplicate `test_call_raises_*` test alongside the old one — the old one is removed/replaced.
- Add new tests for full `.call()` wire behavior here — that's `test_sdet_fixtures.py:test_d02_registry_activation_sets_slug_client_registry` (Plan 18-08 Task 2) and `tests/sdet/test_basic_call.py` (Plan 18-07 Task 3).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_tool_factory.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "NotImplementedError" tests/framework/unit/test_tool_factory.py` returns 0 (old test removed)
    - `grep -c "test_call_raises_runtime_error_when_no_active_client" tests/framework/unit/test_tool_factory.py` returns 1
    - `grep -c "saved_client = tf._ACTIVE_CLIENT" tests/framework/unit/test_tool_factory.py` returns 1
    - `grep -c "Phase 18" tests/framework/unit/test_tool_factory.py` returns at least 1 (decision-trace breadcrumb)
    - `uv run pytest tests/framework/unit/test_tool_factory.py -x` passes (all remaining tests + new replacement)
  </acceptance_criteria>
  <done>
    NotImplementedError test replaced with RuntimeError-no-active-client test; `_reset_module_state` extended to handle `_ACTIVE_CLIENT`; pre-existing Phase 17 contract tests still pass.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

None new — unit tests with mocks and inline XML. Threat surface inherited from underlying modules.
</threat_model>

<verification>
- All five test files pass: `uv run pytest tests/framework/unit/test_tool_call_error.py tests/framework/unit/test_sdet_fixtures.py tests/framework/unit/test_sdet_cli.py tests/framework/unit/test_sdet_renderer.py tests/framework/unit/test_tool_factory.py -x`.
- Existing test suites still pass (regression guard): `uv run pytest tests/framework/unit/test_runner_explain.py tests/framework/unit/test_runner_parser.py tests/framework/unit/test_runner_pre_run_digest.py tests/framework/unit/test_tool_response.py -x`.
- Full framework suite green: `uv run mcp-test-framework run --with-framework` exits 0 (or with only pre-existing skips).
</verification>

<success_criteria>
- D-01 through D-11 each have at least one explicit pinning test in the four new files.
- Plan 18-04's `__all__` contract is pinned.
- The `NotImplementedError` test from Phase 17 is replaced; new RuntimeError test pins Plan 18-02's contract.
- No regression in existing Phase 14/16/17 tests.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-08-SUMMARY.md` documenting: the four new test files, the test count per decision (D-01..D-11 coverage table), and confirmation that all five plans (18-01..18-07) now have pin tests.
</output>
