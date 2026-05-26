"""Collection-time per-bucket skip filter -- BUCKET-02 / SC#1.

Invariant: skipped buckets are ABSENT from `pytest --collect-only`
output AND DO NOT produce runtime SKIPPED rows. Mirrors the v1.1.1
whole-tool skip invariant (project memory MEM:project_v1_1_skip_bug).

Harness: subprocess-based `pytest --collect-only` AND full-run
`pytest` against a tmp_path pyproject.toml + config.yaml + stub
conftest.py. Mandatory per the W2/W3 revision notes -- the
`--collect-only` check alone misses the [NOTSET] placeholder
that pytest 9.0.3 emits when indirect-parametrize receives an
empty list (see Test 5 `rationale`). The full-run check is what
pins the chosen two-hook mechanism (filter in
pytest_generate_tests + [NOTSET] cleanup in
pytest_collection_modifyitems) against the broken
empty-parametrize-only mechanism.

A synthetic-Metafunc unit test (Test 4) sits alongside for fast
feedback.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework._plugin import pytest_generate_tests
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS
from mcp_test_framework.models import ToolConfig


def _write_harness(
    tmp_path: Path,
    tool_a_skip_buckets: list[str],
    tool_b_skip_buckets: list[str],
) -> None:
    """Write pyproject.toml + config.yaml + stub conftest.py into tmp_path."""
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent(f"""\
        [tool.pytest.ini_options]
        mcp_config_file = "./config.yaml"
        asyncio_mode = "strict"
    """))
    (tmp_path / "config.yaml").write_text(textwrap.dedent(f"""\
        version: 2
        mcp_server:
          command: homelab-mcp
          args: []
        tools:
          tool_a:
            skip: false
            skip_buckets: {tool_a_skip_buckets!r}
          tool_b:
            skip: false
            skip_buckets: {tool_b_skip_buckets!r}
        test_code:
          generated_root: ./_gen
    """))
    # Stub conftest.py monkeypatches _discover_tools_live so no real MCP
    # subprocess is spawned during the subprocess pytest invocation.
    (tmp_path / "conftest.py").write_text(textwrap.dedent("""\
        import mcp_test_framework._plugin as _plugin

        async def _fake_discover(cfg):
            return ["tool_a", "tool_b"]

        _plugin._discover_tools_live = _fake_discover
    """))


def _run_collect_only(tmp_path: Path, verbose: bool = False) -> subprocess.CompletedProcess:
    args = [sys.executable, "-m", "pytest", "--collect-only", "-v" if verbose else "-q"]
    return subprocess.run(args, cwd=tmp_path, capture_output=True, text=True)


def _run_full(tmp_path: Path) -> subprocess.CompletedProcess:
    """Full run -- no --collect-only. The actual tests will fail at fixture
    resolution because the stub harness has no real MCP server, but the
    critical assertion is about SKIPPED-row PRESENCE in stdout, which is
    determined at collection time before any test body runs.
    """
    args = [
        sys.executable, "-m", "pytest",
        "-v", "-p", "no:cacheprovider", "--no-header", "-rN",
    ]
    return subprocess.run(args, cwd=tmp_path, capture_output=True, text=True)


def test_skip_output_bucket_drops_only_output_tests_for_that_tool(
    tmp_path: Path,
) -> None:
    """Test 1: tool_b skip_buckets=["output"] removes only output tests for tool_b.

    Subprocess-based --collect-only harness. MANDATORY per plan spec.
    """
    _write_harness(tmp_path, tool_a_skip_buckets=[], tool_b_skip_buckets=["output"])
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    stdout = result.stdout

    # Output-bucket tests for tool_b must be ABSENT from collected node ids.
    assert "test_empty_args_call_returns_non_error[tool_b]" not in stdout, (
        f"Output-bucket test for tool_b should not be collected.\nstdout:\n{stdout}"
    )
    assert "test_result_has_content_or_structured[tool_b]" not in stdout, (
        f"Output-bucket test for tool_b should not be collected.\nstdout:\n{stdout}"
    )
    assert "test_text_content_parses_as_json[tool_b]" not in stdout, (
        f"Output-bucket test for tool_b should not be collected.\nstdout:\n{stdout}"
    )

    # Schema and judge tests for tool_b ARE still present.
    assert "test_schema_passes_structural_checks[tool_b]" in stdout, (
        f"Schema test for tool_b should still be collected.\nstdout:\n{stdout}"
    )
    assert "test_description_clarity[tool_b]" in stdout, (
        f"Judge test for tool_b should still be collected.\nstdout:\n{stdout}"
    )

    # tool_a's output tests are unaffected.
    assert "test_empty_args_call_returns_non_error[tool_a]" in stdout, (
        f"Output test for tool_a should be collected.\nstdout:\n{stdout}"
    )

    # Collection must succeed (exit code 0 = tests found; NOT 2 = error).
    assert result.returncode == 0, (
        f"pytest --collect-only should exit 0 (tests found).\nreturncode={result.returncode}\nstdout:\n{stdout}\nstderr:\n{result.stderr}"
    )


def test_skip_all_buckets_for_one_tool_drops_all_its_tests(
    tmp_path: Path,
) -> None:
    """Test 2: tool_b skip_buckets=["schema","judge","output"] drops ALL its tests.

    Subprocess-based --collect-only harness. MANDATORY per plan spec.
    """
    _write_harness(
        tmp_path,
        tool_a_skip_buckets=[],
        tool_b_skip_buckets=["schema", "judge", "output"],
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    stdout = result.stdout

    # No node id should contain [tool_b].
    assert "[tool_b]" not in stdout, (
        f"No tool_b node ids should be collected when all buckets are skipped.\nstdout:\n{stdout}"
    )

    # No [NOTSET] placeholder should appear (modifyitems cleanup must have stripped it).
    assert "[NOTSET]" not in stdout, (
        f"[NOTSET] placeholder should be stripped by pytest_collection_modifyitems.\nstdout:\n{stdout}"
    )

    # tool_a tests still present (all buckets).
    assert "[tool_a]" in stdout, (
        f"tool_a tests should still be collected.\nstdout:\n{stdout}"
    )

    # Collection must not error (exit 0 = has tests, exit 5 = no tests; both OK, NOT 2).
    assert result.returncode in (0, 5), (
        f"pytest --collect-only should exit 0 (tests found) not 2 (error).\nreturncode={result.returncode}\nstdout:\n{stdout}\nstderr:\n{result.stderr}"
    )


def test_no_collected_test_is_runtime_skipped_due_to_skip_buckets(
    tmp_path: Path,
) -> None:
    """Test 3: skipped-bucket cells produce zero SKIPPED rows in full-run output.

    Subprocess-based --collect-only AND full-run. MANDATORY per plan spec.
    Distinguishes the two-hook mechanism from the broken empty-parametrize-only
    mechanism which leaves [NOTSET] SKIPPED rows.
    """
    _write_harness(tmp_path, tool_a_skip_buckets=[], tool_b_skip_buckets=["output"])

    # (a) collect-only: no [NOTSET] in node-id listing.
    collect_result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-v"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    collect_stdout = collect_result.stdout

    # Output-bucket tests for tool_b must not appear (assertion on parametrize-id pairs).
    for output_test in (
        "test_empty_args_call_returns_non_error",
        "test_result_has_content_or_structured",
        "test_text_content_parses_as_json",
    ):
        assert f"{output_test}[tool_b]" not in collect_stdout, (
            f"{output_test}[tool_b] should be absent from --collect-only.\nstdout:\n{collect_stdout}"
        )

    assert "[NOTSET]" not in collect_stdout, (
        f"[NOTSET] should not appear in --collect-only output.\nstdout:\n{collect_stdout}"
    )

    # (b) full-run: no SKIPPED rows for filtered cells.
    full_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--no-header", "-rN"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    full_stdout = full_result.stdout

    # The two-hook mechanism produces zero SKIPPED rows; broken empty-parametrize-only
    # mechanism produces N SKIPPED rows. This assertion is the discriminator.
    assert " SKIPPED" not in full_stdout, (
        f"No SKIPPED rows should appear in full-run output when buckets are filtered at collection time.\nstdout:\n{full_stdout}"
    )


def test_synthetic_metafunc_per_bucket_filter_drops_expected_tools() -> None:
    """Test 4: unit-level synthetic-Metafunc pin for the per-bucket filter.

    Uses a tiny mock to call pytest_generate_tests directly and asserts the
    recorded parametrize() call excludes the correct tools.
    """
    from mcp_test_framework.config import Config
    from mcp_test_framework.models import TestCodeConfig

    _TEST_CODE_STUB = TestCodeConfig(generated_root="tests/sdet/_generated")

    def _make_metafunc(
        func_name: str,
        tools_map: dict[str, ToolConfig],
        parametrize_tools: list[str],
    ):
        """Build a fake Metafunc-like namespace suitable for pytest_generate_tests."""
        # Config with the supplied tools map.
        cfg = Config(
            test_code=_TEST_CODE_STUB,
            tools=tools_map,
        )

        # Synth collector with sentinel + parametrize stash.
        synth_collector = SimpleNamespace(
            _is_mcp_contracts_synthetic=True,
            _mcp_parametrize_tools=parametrize_tools,
            parent=None,
        )

        # Recording parametrize method.
        recorded_calls: list[tuple] = []

        def record_parametrize(argname, argvalues, **kwargs):
            recorded_calls.append((argname, list(argvalues), kwargs))

        # Fake function with the correct __name__.
        fake_func = SimpleNamespace(__name__=func_name)

        # Fake metafunc with all attrs pytest_generate_tests walks.
        fake_metafunc = SimpleNamespace(
            function=fake_func,
            fixturenames=["mcp_target_tool"],
            definition=SimpleNamespace(parent=synth_collector),
        )
        fake_config = SimpleNamespace(_mcp_contracts_config=cfg)
        fake_metafunc.config = fake_config
        fake_metafunc.parametrize = record_parametrize

        return fake_metafunc, recorded_calls

    # --- Sub-case A: output-bucket test with tool_b skipping output ---
    meta_a, calls_a = _make_metafunc(
        func_name="test_empty_args_call_returns_non_error",
        tools_map={
            "tool_a": ToolConfig(),
            "tool_b": ToolConfig(skip_buckets=["output"]),
        },
        parametrize_tools=["tool_a", "tool_b"],
    )
    pytest_generate_tests(meta_a)

    assert len(calls_a) == 1, f"parametrize should be called exactly once; got {calls_a}"
    argname_a, names_a, _ = calls_a[0]
    assert argname_a == "mcp_target_tool"
    assert names_a == ["tool_a"], (
        f"tool_b should be filtered out for output-bucket test; got names={names_a}"
    )

    # --- Sub-case B: schema-bucket test with tool_b skipping output (not schema) ---
    meta_b, calls_b = _make_metafunc(
        func_name="test_schema_passes_structural_checks",
        tools_map={
            "tool_a": ToolConfig(),
            "tool_b": ToolConfig(skip_buckets=["output"]),
        },
        parametrize_tools=["tool_a", "tool_b"],
    )
    pytest_generate_tests(meta_b)

    assert len(calls_b) == 1, f"parametrize should be called exactly once; got {calls_b}"
    argname_b, names_b, _ = calls_b[0]
    assert argname_b == "mcp_target_tool"
    assert names_b == ["tool_a", "tool_b"], (
        f"Neither tool should be filtered for schema test when only output is skipped; got names={names_b}"
    )

    # --- Sub-case C: judge-bucket test, both tools opt out of different buckets ---
    meta_c, calls_c = _make_metafunc(
        func_name="test_description_clarity",
        tools_map={
            "tool_a": ToolConfig(skip_buckets=["judge"]),
            "tool_b": ToolConfig(skip_buckets=["schema", "judge", "output"]),
        },
        parametrize_tools=["tool_a", "tool_b"],
    )
    pytest_generate_tests(meta_c)

    assert len(calls_c) == 1, f"parametrize should be called exactly once; got {calls_c}"
    argname_c, names_c, _ = calls_c[0]
    assert argname_c == "mcp_target_tool"
    assert names_c == [], (
        f"Both tools skip judge bucket; names should be empty; got names={names_c}"
    )


def test_every_tool_opts_out_of_every_bucket_emits_zero_items(
    tmp_path: Path,
) -> None:
    """Test 5: every tool opts out of every bucket -> zero items, zero SKIPPED rows.

    Subprocess-based collect-only AND full-run. MANDATORY per W2 pin.
    Invariant: "every tool opts out of every bucket -> zero items post-modifyitems,
    zero runtime SKIPPED rows, zero collection errors."
    """
    _write_harness(
        tmp_path,
        tool_a_skip_buckets=["schema", "judge", "output"],
        tool_b_skip_buckets=["schema", "judge", "output"],
    )

    # (a) collect-only: exit 0 or 5, no [tool_a]/[tool_b]/[NOTSET], no ERROR.
    collect_result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    collect_stdout = collect_result.stdout

    assert collect_result.returncode in (0, 5), (
        f"Exit code should be 0 (collected) or 5 (no tests), not 2 (error).\nreturncode={collect_result.returncode}\nstdout:\n{collect_stdout}\nstderr:\n{collect_result.stderr}"
    )
    assert "[tool_a]" not in collect_stdout, (
        f"No tool_a items should appear when all buckets are skipped.\nstdout:\n{collect_stdout}"
    )
    assert "[tool_b]" not in collect_stdout, (
        f"No tool_b items should appear when all buckets are skipped.\nstdout:\n{collect_stdout}"
    )
    assert "[NOTSET]" not in collect_stdout, (
        f"[NOTSET] placeholder should be stripped by modifyitems cleanup.\nstdout:\n{collect_stdout}"
    )

    # (b) full-run: zero SKIPPED rows, exit 0 or 5 (NOT 2).
    full_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--no-header", "-rN"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    full_stdout = full_result.stdout

    # The two-hook mechanism (W2 fix) produces zero SKIPPED rows.
    # The broken empty-parametrize-only mechanism produces N SKIPPED rows (one per test func).
    # This assertion is the discriminator between the two mechanisms.
    assert " SKIPPED" not in full_stdout, (
        f"Zero SKIPPED rows should appear when all buckets are skipped for every tool.\nstdout:\n{full_stdout}"
    )

    assert full_result.returncode in (0, 5), (
        f"Exit code should be 0 or 5 (not 2 = collection error).\nreturncode={full_result.returncode}\nstdout:\n{full_stdout}\nstderr:\n{full_result.stderr}"
    )
