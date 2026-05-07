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
from mcp_test_framework.models import ToolConfig

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
    """D-01 / D-02 / TOOLCFG-06."""
    cfg = Config()
    assert cfg.version == 1
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


@pytest.mark.parametrize("bad_version", [0, 2, -1, 99])
def test_config_rejects_unsupported_version(bad_version) -> None:
    """D-02 / CD-01: only version=1 accepted; error message names version + value."""
    with pytest.raises(ValueError) as exc_info:
        Config(version=bad_version)
    msg = str(exc_info.value)
    assert "version" in msg
    assert str(bad_version) in msg


def test_reserved_fields_typed_but_runtime_no_op() -> None:
    """TOOLCFG-03 / D-06: setup + depends_on present, ignored at runtime."""
    tc = ToolConfig(setup={"x": 1}, depends_on=["a", "b"])
    assert tc.setup == {"x": 1}
    assert tc.depends_on == ["a", "b"]


def test_yaml_overlay_loads_tools_block(tmp_path: Path, monkeypatch) -> None:
    """D-20: YAML overlay path reaches `tools:` block correctly."""
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            """
            version: 1
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
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    cfg = Config()
    assert cfg.version == 1
    assert "foo_tool" in cfg.tools
    foo = cfg.tools["foo_tool"]
    assert foo.skip is True
    assert foo.skip_reason == "demonstration"
    assert foo.call_arguments == {"query": "ping"}
    assert foo.judges == ["clarity"]


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
    """
    from tests.test_mcp_tool_contract import test_empty_args_call_returns_non_error

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
