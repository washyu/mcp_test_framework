"""Wave-0 regression guard for Phase 12 CLEAN-02 + D-13.

config.example.yaml is hand-curated as a 3-pattern template. This test
ensures the file remains a 3-entry placeholder document -- not a homelab-
specific config (which lives at examples/homelab-mcp.yaml).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")


CFG_EXAMPLE = _repo_root() / "config.example.yaml"


def _load() -> dict:
    return yaml.safe_load(CFG_EXAMPLE.read_text(encoding="utf-8"))


def test_config_example_yaml_exists() -> None:
    assert CFG_EXAMPLE.is_file(), f"missing {CFG_EXAMPLE}"


def test_config_example_yaml_parses() -> None:
    data = _load()
    assert isinstance(data, dict)
    for key in ("ollama", "mcp_server", "judge_timeout_seconds", "version", "tools"):
        assert key in data, f"top-level {key!r} missing"


def test_config_example_has_placeholder_tools() -> None:
    """D-13 + Phase 999.2 D-01: placeholder entries demonstrate Patterns A/B/C/D."""
    data = _load()
    tools = data["tools"]
    expected = {
        "<safe_read_tool_a>",
        "<safe_read_tool_b>",
        "<destructive_tool_c>",
        "<required_field_tool>",
    }
    assert set(tools.keys()) == expected, (
        f"unexpected tool entries: got {set(tools.keys())}, want {expected}"
    )


def test_config_example_no_target_block() -> None:
    """D-03: target.tool_name is leaving in Phase 13; do not advertise it."""
    data = _load()
    assert "target" not in data, "target: block must be absent from config.example.yaml (D-03)"


def test_config_example_links_config_init_and_examples() -> None:
    """D-14: README/template/config-init form a triangle. The template links to
    both config-init (the runnable scaffold) and examples/homelab-mcp.yaml
    (the worked reference)."""
    text = CFG_EXAMPLE.read_text(encoding="utf-8")
    assert "config-init" in text
    assert "examples/homelab-mcp.yaml" in text


def test_config_example_no_banned_tokens() -> None:
    text = CFG_EXAMPLE.read_text(encoding="utf-8")
    banned = [
        r"\bPhase \d",
        r"\bPlan \d-\d",
        r"\bTOOLCFG-\d",
        r"\bISOL-\d",
        r"\bOUTPUT-\d",
        r"\bCD-\d",
        r"\bD-\d{2}",
        r"\b\d{6}-[a-z0-9]{3}",
    ]
    found = [p for p in banned if re.search(p, text)]
    assert not found, f"banned tokens in config.example.yaml: {found}"


def test_config_example_has_pattern_comments() -> None:
    """The header comment block names the patterns; the per-tool
    comments label which pattern each entry implements."""
    text = CFG_EXAMPLE.read_text(encoding="utf-8")
    assert "Pattern A" in text
    assert "Pattern B" in text
    assert "Pattern C" in text
    assert "Pattern D" in text


def test_config_example_pattern_a_has_judges() -> None:
    """Pattern A = minimal opt-in via judges-only."""
    data = _load()
    a = data["tools"]["<safe_read_tool_a>"]
    assert "judges" in a, "Pattern A entry must demonstrate judges-only opt-in"


def test_config_example_pattern_b_has_call_arguments() -> None:
    """Pattern B = opt-in with pre-filled call_arguments."""
    data = _load()
    b = data["tools"]["<safe_read_tool_b>"]
    assert "call_arguments" in b, "Pattern B entry must demonstrate call_arguments"


def test_config_example_pattern_c_has_skip_with_reason() -> None:
    """Pattern C = opt-out with curated reason."""
    data = _load()
    c = data["tools"]["<destructive_tool_c>"]
    assert c.get("skip") is True
    assert c.get("skip_reason"), "Pattern C must have non-empty skip_reason"


def test_config_example_pattern_d_has_examples_and_skip_buckets() -> None:
    """Pattern D = required-field tool with examples: + skip_buckets: pairing."""
    data = _load()
    d = data["tools"]["<required_field_tool>"]
    assert "examples" in d, (
        "Pattern D entry must demonstrate the examples: field "
        "(codegen-driven smoke scenario -- Phase 999.2)"
    )
    assert isinstance(d["examples"], list) and len(d["examples"]) > 0, (
        "Pattern D examples: must be a non-empty list of argument dicts"
    )
    assert "skip_buckets" in d, (
        "Pattern D entry must demonstrate the skip_buckets: pairing "
        "(recommended companion to examples: for required-field tools)"
    )
