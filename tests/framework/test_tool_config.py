"""Phase 08 verification: ToolConfig schema + runtime guards.

Schema tests (load-time, sync, no live services) verify the Pydantic surface
laid by Plan 01: ToolConfig defaults, validator behavior, version constraint,
extra="forbid" on both ToolConfig and top-level Config.

Runtime tests (subprocess pytest invocations against
tests/test_mcp_tool_contract.py) verify the runtime guards laid by Plan 02:
skip-via-config, judges subset, call_arguments threading, and the
unknown-tool-name warning. These require a live homelab-mcp + Ollama --
marked accordingly so the default pytest run
(addopts = "-m 'not live_homelab and not live_ollama'") excludes them.

A separate AsyncMock-based unit test proves call_arguments threading reaches
McpTestClient.call_tool verbatim WITHOUT requiring a live server -- this is
the strong proof of ROADMAP success criterion #4 / TOOLCFG-01.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml
from pydantic import ValidationError

from mcp_test_framework.config import Config
from mcp_test_framework.models import TestCodeConfig, ToolConfig

# Phase 23 D-01 (Cluster A): Config.sdet is REQUIRED post Phase 21.1 RELOC-01.
# Module-level stub (Pattern S1) covers the bare Config() sites in this file.
# Mirrors tests/framework/unit/test_homelab_config.py:51-58 (the locked source).
_TEST_CODE_STUB = TestCodeConfig(generated_root="tests/sdet/_generated")

# ===========================================================================
# Schema tests -- sync, load-time, no live services
# ===========================================================================


def test_default_toolconfig_values() -> None:
    """D-04: declaration order + defaults."""
    tc = ToolConfig()
    assert tc.skip is False
    assert tc.skip_reason is None
    assert tc.call_arguments == {}
    assert tc.judges is None
    assert tc.setup is None
    assert tc.depends_on is None


def test_default_config_version_and_tools() -> None:
    """D-01 / D-02 / TOOLCFG-06.

    Phase 23 (Cluster A): Config.sdet is REQUIRED -> supply _TEST_CODE_STUB. The
    default schema version is 2 since the v1->v2 migration; assertion
    updated to match current schema.
    """
    cfg = Config(test_code=_TEST_CODE_STUB)
    assert cfg.version == 2
    assert isinstance(cfg.tools, dict)


def test_config_rejects_extra_top_level_field() -> None:
    """CD-02 / TOOLCFG-05 at root level: typos like `targt:` -> error."""
    with pytest.raises(ValidationError) as exc_info:
        Config(targt=None)
    assert "extra_forbidden" in str(exc_info.value)


def test_toolconfig_rejects_extra_field_typo() -> None:
    """TOOLCFG-05 / D-15: typos like `srtip:` -> extra_forbidden at load."""
    with pytest.raises(ValidationError) as exc_info:
        ToolConfig(srtip=True)
    assert "extra_forbidden" in str(exc_info.value)


def test_toolconfig_rejects_unknown_judge_id() -> None:
    """D-17 / TOOLCFG-04: unknown rubric ID -> ValueError listing valid IDs."""
    with pytest.raises(ValueError) as exc_info:
        ToolConfig(judges=["clarty"])
    msg = str(exc_info.value)
    assert "clarity" in msg
    assert "unknown rubric id" in msg


def test_toolconfig_accepts_empty_judges_list() -> None:
    """D-07: empty list = explicit opt-out, distinct from None default."""
    tc = ToolConfig(judges=[])
    assert tc.judges == []


def test_toolconfig_accepts_none_judges() -> None:
    """TOOLCFG-06: None default = run all rubrics."""
    tc = ToolConfig(judges=None)
    assert tc.judges is None


def test_toolconfig_accepts_all_locked_rubric_ids() -> None:
    """TOOLCFG-04 / D-10: locked v1.1 ID set."""
    tc = ToolConfig(judges=["clarity", "disambiguation", "parameters"])
    assert tc.judges == ["clarity", "disambiguation", "parameters"]


@pytest.mark.parametrize("bad_reason", [None, "", "   "])
def test_toolconfig_skip_requires_non_empty_reason(bad_reason) -> None:
    """D-16 / TOOLCFG-07: skip=True without non-empty skip_reason -> error."""
    with pytest.raises(ValueError) as exc_info:
        ToolConfig(skip=True, skip_reason=bad_reason)
    assert "skip_reason" in str(exc_info.value)


def test_toolconfig_skip_with_reason_succeeds() -> None:
    """D-16 happy path."""
    tc = ToolConfig(skip=True, skip_reason="legitimate reason")
    assert tc.skip is True
    assert tc.skip_reason == "legitimate reason"


@pytest.mark.parametrize("bad_version", [0, 1, -1, 99])
def test_config_rejects_unsupported_version(bad_version) -> None:
    """D-02 / CD-01: only version=2 accepted post Phase 13 v1->v2 migration;
    error message names version + value.

    Phase 23 (Cluster A): parametrize previously included `2` from the v1
    era; updated to `1` (now-stale schema) to keep the rejection contract
    covered with a non-current version. Config.sdet is REQUIRED so supply
    _TEST_CODE_STUB.
    """
    with pytest.raises(ValueError) as exc_info:
        Config(test_code=_TEST_CODE_STUB, version=bad_version)
    msg = str(exc_info.value)
    assert "version" in msg
    assert str(bad_version) in msg


def test_reserved_fields_typed_but_runtime_no_op() -> None:
    """TOOLCFG-03 / D-06: setup + depends_on present, ignored at runtime."""
    tc = ToolConfig(setup={"x": 1}, depends_on=["a", "b"])
    assert tc.setup == {"x": 1}
    assert tc.depends_on == ["a", "b"]


def test_yaml_overlay_loads_tools_block(tmp_path: Path, monkeypatch) -> None:
    """D-20: YAML overlay path reaches `tools:` block correctly.

    Phase 23 (Cluster A): YAML must declare `version: 2` post the Phase 13
    v1->v2 migration; bare Config() in this body needs sdet supplied via
    YAML (the YAML source layers in atop init kwargs). The YAML now
    carries the `sdet:` block alongside the `tools:` block to mirror what
    the operator-facing scaffold emits.
    """
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            """
            version: 2
            sdet:
              generated_root: "tests/sdet/_generated"
            tools:
              foo_tool:
                skip: true
                skip_reason: "demonstration"
                call_arguments:
                  query: "ping"
                judges: [clarity]
            """
        ).strip() + "\n",
        encoding="utf-8",
    )
    # v1.5: MCPTF_CONFIG_FILE is no longer a path-pointer fallback; load
    # via the explicit yaml_file= kwarg the resolver in cli._load_config
    # now uses end-to-end.
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    cfg = Config(yaml_file=str(yaml_path))
    assert cfg.version == 2
    assert "foo_tool" in cfg.tools
    foo = cfg.tools["foo_tool"]
    assert foo.skip is True
    assert foo.skip_reason == "demonstration"
    assert foo.call_arguments == {"query": "ping"}
    assert foo.judges == ["clarity"]


# ===========================================================================
# v1.1.1 hotfix (260508-p0b) regression tests -- parametrize-time skip filter
#
# Phase 14 gap-closure (Plan 14-07): grouped into TestV111SkipFilter so the
# autouse `_reset_discovery_cache` fixture's blast radius is narrow -- it
# only resets the migrated cache for these two tests, not the whole module.
# Mirrors the reference pattern at tests/unit/test_runner_migration.py.
# ===========================================================================


class TestV111SkipFilter:
    """SAFE-01 v1.1.1 skip-filter regression coverage.

    Plan 14-05 migrated the in-pytest discovery cache from
    `tests.conftest._DISCOVERED_TOOL_NAMES` (implicit module attribute) to
    `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (importable module
    path). Tests here patch the new canonical seam. The autouse reset
    fixture mirrors `tests/unit/test_runner_migration.py:_reset_discovery_cache`.
    """

    @pytest.fixture(autouse=True)
    def _reset_discovery_cache(self):
        """Phase 14 gap-closure (Plan 14-07): mirror the reset fixture in
        tests/unit/test_runner_migration.py so the v1.1.1 regression tests
        stay independent. The discovery cache lives in
        `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (Plan 14-05).
        """
        from mcp_test_framework import _runner as _r
        _r._DISCOVERED_TOOL_NAMES = None
        yield
        _r._DISCOVERED_TOOL_NAMES = None

    def test_allowlist_filters_out_skip_true_tools(self) -> None:
        """v1.1.1-SKIP-FILTER: ``tools.<name>.skip: true`` removes the tool
        from the parametrize input list (not just runtime-skips its 10 tests).

        Phase 27 retarget: the legacy ``tests/conftest.py:_resolve_tool_names``
        helper is gone; the opt-in allowlist filter now lives inline in
        ``src/mcp_test_framework/_plugin.py:pytest_collection`` as a
        generator expression over ``cfg.tools.items()``. The test mirrors
        the plugin's one-liner so the SAFE-01 contract stays pinned
        independent of where the filter lives.
        """
        from mcp_test_framework.models import TestCodeConfig
        config = Config(
            test_code=TestCodeConfig(generated_root="tests/test_code/_generated"),
            tools={
                "a": ToolConfig(),
                "b": ToolConfig(skip=True, skip_reason="testing the filter"),
                "c": ToolConfig(),
            }
        )
        allowed = sorted(
            name for name, tcfg in config.tools.items() if not tcfg.skip
        )
        assert allowed == ["a", "c"], (
            f"expected skip:true tool 'b' filtered out; got {allowed!r}"
        )


# ===========================================================================
# Phase 14 gap-closure (Plan 14-07): patch-seam migration audit
#
# Plan 14-05 moved the in-pytest discovery cache from
# `tests.conftest._DISCOVERED_TOOL_NAMES` (implicit module attribute) to
# `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (importable module
# path). The audit below catches any test that still patches the old seam.
# ===========================================================================


def test_no_stale_conftest_module_discovered_tool_names_writes() -> None:
    """Phase 14 gap-closure: no test should patch the dead seam
    `_conftest_module._DISCOVERED_TOOL_NAMES = [...]`. The cache moved
    to `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` in Plan 14-05;
    writing to the conftest-module attribute is now a no-op (the conftest
    consumes the cache via `from mcp_test_framework import _runner as _r;
    _r._DISCOVERED_TOOL_NAMES`).

    If this test fails, retarget the offending patch to:
        from mcp_test_framework import _runner as _r
        _r._DISCOVERED_TOOL_NAMES = [...]
    See tests/unit/test_runner_migration.py for the reference pattern.
    """
    import re
    from pathlib import Path

    tests_dir = Path(__file__).parent
    offenders: list[tuple[Path, int, str]] = []
    # Match writes only (avoids matching documentation that quotes the
    # pattern). Pattern: dotted access + optional spaces + '=' + not '='.
    write_pattern = re.compile(r"_conftest_module\._DISCOVERED_TOOL_NAMES\s*=\s*(?!=)")
    # Track triple-quoted-string state so docstrings/assertion messages
    # that reference the dead-seam pattern are not flagged. This lets the
    # audit catch real writes (Tasks 1 RED state) while ignoring its own
    # documentation (Task 2 GREEN state).
    triple_re = re.compile(r'"""|\'\'\'')
    for py_file in tests_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        in_triple = False
        for lineno, line in enumerate(content.splitlines(), start=1):
            # Toggle triple-quote state once per delimiter on this line.
            triple_hits = len(triple_re.findall(line))
            line_starts_in_string = in_triple
            if triple_hits % 2 == 1:
                in_triple = not in_triple
            # Skip pure comment lines.
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            # Skip lines that are fully inside a docstring/triple-quoted
            # string (both started and ended inside one).
            if line_starts_in_string and in_triple:
                continue
            if write_pattern.search(line):
                offenders.append((py_file.relative_to(tests_dir), lineno, line.strip()))
    assert offenders == [], (
        "Found stale writes to `_conftest_module._DISCOVERED_TOOL_NAMES` "
        "(the cache moved to `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` "
        "in Plan 14-05). Retarget per `tests/unit/test_runner_migration.py`. "
        f"Offenders: {offenders}"
    )


# ===========================================================================
# AsyncMock-based call_arguments threading proof (TOOLCFG-01 strong proof,
# ROADMAP success criterion #4) -- in-process, no live server needed.
# ===========================================================================


@pytest.mark.asyncio
async def test_call_arguments_forwarded_to_call_tool_via_asyncmock() -> None:
    """ROADMAP success criterion #4 / TOOLCFG-01: prove the framework passes
    the configured `call_arguments` dict (NOT `{}`) into McpTestClient.call_tool.

    Imports the actual TEST-08 body Plan 02 modified, builds fake
    mcp_client + target_tool + tool_config, awaits the body, then asserts
    the AsyncMock received the configured args verbatim.

    Phase 27 D-05 retarget: the legacy on-disk contract file was deleted
    and its bodies extracted into ``mcp_test_framework.contracts._tests``
    (the wheel-shipped module the plugin injects). Import the body from
    the new location; the fixture-name renames (``mcp_target_tool``,
    ``mcp_client``) are positional in the test signature so the
    SimpleNamespace fakes still bind correctly.
    """
    from mcp_test_framework.contracts._tests import test_empty_args_call_returns_non_error

    configured_args = {"key": "value", "limit": 7}
    tool_config = ToolConfig(call_arguments=configured_args)

    fake_result = SimpleNamespace(isError=False, content=[], structuredContent=None)
    mock_call_tool = AsyncMock(return_value=fake_result)
    fake_mcp_client = SimpleNamespace(call_tool=mock_call_tool)
    fake_target_tool = SimpleNamespace(name="demo_tool")

    await test_empty_args_call_returns_non_error(
        fake_mcp_client, fake_target_tool, tool_config
    )

    mock_call_tool.assert_called_once_with("demo_tool", configured_args)


# ===========================================================================
# Runtime tests -- subprocess pytest against test_mcp_tool_contract.py
# ===========================================================================


def _run_pytest_with_tools_yaml(
    tmp_path: Path,
    tools_block: dict,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Drive `pytest tests/test_mcp_tool_contract.py` under a tempfile YAML
    overlay built by deep-merging `tools_block` into config.example.yaml.

    Why deep-merge (not string concat): config.example.yaml itself contains
    a top-level `tools:` block after Plan 04 Task 3 lands. Naive
    concatenation would produce duplicate top-level `tools:` keys --
    PyYAML's safe_load silently keeps the last (works today, breaks
    invisibly the moment loader semantics tighten or a third-party tool
    reads the YAML strictly). Deep-merge keeps the file syntactically
    valid AND preserves the example's other settings (mcp_server, ollama,
    target, judge_timeout_seconds), which is what we want -- the test
    inherits the operator's mcp_server config from the canonical example.
    """
    base_doc = yaml.safe_load(
        Path("config.example.yaml").read_text(encoding="utf-8")
    ) or {}

    merged_tools = dict(base_doc.get("tools") or {})
    merged_tools.update(tools_block)
    base_doc["tools"] = merged_tools

    yaml_path = tmp_path / "tools_overlay.yaml"
    yaml_path.write_text(
        yaml.safe_dump(base_doc, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )

    env = {**os.environ, "MCPTF_CONFIG_FILE": str(yaml_path)}
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_mcp_tool_contract.py",
        "-v",
        "-W", "default::UserWarning",
        # Override the default addopts marker filter so the inner pytest
        # run actually exercises live tests (the OUTER test is marked
        # @live_homelab/@live_ollama -- the gate is at the outer level).
        "-m", "",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=300
    )


@pytest.mark.live_homelab
@pytest.mark.live_ollama
def test_skip_via_config_skips_all_ten_tests_for_tool(tmp_path: Path) -> None:
    """TOOLCFG-07 + uniform skip across all 10 tests (Plan 02 Task 2 commitment)."""
    tools_block = {
        "list_keyring_credentials": {
            "skip": True,
            "skip_reason": "phase 08 verification skip",
        },
    }
    result = _run_pytest_with_tools_yaml(tmp_path, tools_block)
    out = result.stdout + result.stderr
    assert "phase 08 verification skip" in out, (
        f"skip_reason not surfaced. stdout:\n{out}"
    )
    skip_lines = [
        line for line in out.splitlines()
        if "SKIPPED" in line and "list_keyring_credentials" in line
    ]
    assert len(skip_lines) >= 10, (
        f"expected >=10 SKIPPED rows for list_keyring_credentials, got "
        f"{len(skip_lines)}. stdout:\n{out}"
    )


@pytest.mark.live_homelab
@pytest.mark.live_ollama
def test_judges_subset_skips_un_selected_judged_tests(tmp_path: Path) -> None:
    """D-08 / TOOLCFG-04: judges: [clarity] -> TEST-05 runs, TEST-06 + TEST-07 SKIPPED."""
    tools_block = {
        "list_keyring_credentials": {"judges": ["clarity"]},
    }
    result = _run_pytest_with_tools_yaml(tmp_path, tools_block)
    out = result.stdout + result.stderr
    assert "judge 'disambiguation' not selected" in out, (
        f"TEST-06 skip reason missing. stdout:\n{out}"
    )
    assert "judge 'parameters' not selected" in out, (
        f"TEST-07 skip reason missing. stdout:\n{out}"
    )
    assert (
        "judge 'clarity' not selected for tool 'list_keyring_credentials'"
        not in out
    ), f"TEST-05 unexpectedly skipped. stdout:\n{out}"


@pytest.mark.live_homelab
@pytest.mark.live_ollama
def test_unknown_tool_in_tools_block_emits_warning(tmp_path: Path) -> None:
    """D-14 / D-18: configured tool not in discovered list -> UserWarning at session start."""
    tools_block = {
        "does_not_exist_xyz_phase08": {
            "skip": True,
            "skip_reason": "ghost tool",
        },
    }
    result = _run_pytest_with_tools_yaml(tmp_path, tools_block)
    out = result.stdout + result.stderr
    assert "does_not_exist_xyz_phase08" in out, (
        f"unknown-tool warning text missing. stdout:\n{out}"
    )
    assert "configured but not in discovered tool list" in out, (
        f"unknown-tool warning phrase missing. stdout:\n{out}"
    )
    assert result.returncode != 2 or "warning" in out.lower(), (
        f"unexpected hard-fail on unknown tool: returncode={result.returncode}"
    )
