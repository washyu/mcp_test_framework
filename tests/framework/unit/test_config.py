"""Unit tests for the layered Config loader.

Verifies the locked precedence (CONTEXT.md "config precedence"):

    CLI/init kwargs > env vars > .env > YAML overlay > defaults

Each test clears every spec env var and ``MCPTF_CONFIG_FILE`` at start so the
tests do not leak through the shared OS environment. YAML tests use ``tmp_path``
for an isolated YAML file.

These are pure synchronous tests -- pytest-asyncio strict mode does NOT require
markers on sync tests (RESEARCH anti-pattern: do not add ``@pytest.mark.asyncio``).
"""

from __future__ import annotations

from pathlib import Path

import pydantic_core
import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.models import OllamaConfig, TestCodeConfig

# Phase 21.1 RELOC-01 (Rule 3 deviation, plan 21.1-01): Config.sdet became a
# REQUIRED field with no default. Every Config(...) call in this file must
# now provide it -- either via an init kwarg (`test_code=_TEST_CODE_STUB`) or via the
# `sdet:` block in the YAML body. The stub points at a per-test tmp path-
# adjacent literal; tests do not exercise the value, only the load.
_TEST_CODE_STUB = TestCodeConfig(generated_root=Path("tests/sdet/_generated"))
_TEST_CODE_YAML_BLOCK = 'test_code:\n  generated_root: "tests/sdet/_generated"\n'

# Every spec env var that must be cleared at the start of each test to avoid
# leakage from the developer's shell environment.
_SPEC_ENV_VARS: tuple[str, ...] = (
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "MCP_SERVER_COMMAND",
    "MCP_SERVER_ARGS",
    "MCP_SERVER_TIMEOUT_SECONDS",
    "TARGET_TOOL_NAME",
    "JUDGE_TIMEOUT_SECONDS",
    "MCPTF_CONFIG_FILE",
)


@pytest.fixture(autouse=True)
def _isolate_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Chdir each test to a fresh tmp dir so the project root's `.env` does NOT
    bleed into Config(). Tests that need a `.env` create one inside `tmp_path`.
    Required after the BareNameNestedEnvSource was extended to read `.env` for
    sub-model fields (Phase 02.1 follow-up — fix dotenv routing for nested fields)."""
    monkeypatch.chdir(tmp_path)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _SPEC_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _write_yaml(tmp_path: Path, body: str) -> Path:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(body, encoding="utf-8")
    return yaml_path


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env, no YAML -> every field is its declared default."""
    _clear_env(monkeypatch)

    cfg = Config(test_code=_TEST_CODE_STUB)

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"
    assert cfg.ollama.model == "qwen3.6:latest"
    assert cfg.ollama.timeout_seconds == 120
    assert cfg.mcp_server.command == "homelab-mcp"
    assert cfg.mcp_server.args == []
    assert cfg.mcp_server.timeout_seconds == 30
    # Phase 13 D-11: `target` field removed; single-tool focus now lives
    # in `--config focus-<tool>.yaml` (Phase 12 D-03).
    assert not hasattr(cfg, "target")
    assert cfg.judge_timeout_seconds == 120


def test_env_var_has_no_effect_on_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 13 D-05: env-overlay dropped; this test pins the negation.

    OLLAMA_BASE_URL in os.environ has ZERO effect on Config() — the model
    default wins. (Inverted from the v1.1 test_env_overrides_default.)
    """
    _clear_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:1")

    cfg = Config(test_code=_TEST_CODE_STUB)

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"


def test_yaml_overrides_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """YAML (via Config(yaml_file=...)) beats defaults when no env is set.

    Phase 13 D-05/D-06: env-overlay gone, MCPTF_CONFIG_FILE is no longer a
    Config() source. The resolver in cli.py:_load_config passes the path
    as an explicit kwarg.
    """
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "version: 2\n"
        "ollama:\n  base_url: http://yaml:1\n  model: qwen3.6:latest\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
    )

    cfg = Config(yaml_file=str(yaml_path))

    assert cfg.ollama.base_url == "http://yaml:1"


def test_dotenv_in_cwd_has_no_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Phase 13 D-07: .env is dead-letter for the framework's config layer.

    (Inverted from the v1.1 test_dotenv_routes_to_sub_model_fields.)
    """
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text(
        'MCP_SERVER_COMMAND=uvx\nMCP_SERVER_ARGS=["homelab-mcp"]\n', encoding="utf-8"
    )

    cfg = Config(test_code=_TEST_CODE_STUB)

    # Defaults win; .env contents are ignored.
    assert cfg.mcp_server.command == "homelab-mcp"
    assert cfg.mcp_server.args == []


def test_yaml_beats_env_var(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Phase 13 D-05: env-overlay gone; YAML wins over env var.

    (Inverted from the v1.1 test_env_overrides_yaml.)
    """
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "version: 2\n"
        "ollama:\n  base_url: http://yaml:1\n  model: qwen3.6:latest\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
    )
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:1")

    cfg = Config(yaml_file=str(yaml_path))

    assert cfg.ollama.base_url == "http://yaml:1"


def test_init_overrides_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """init kwargs (CLI flag surface) beat YAML."""
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "version: 2\n"
        "ollama:\n  base_url: http://yaml:1\n  model: qwen3.6:latest\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
    )

    cfg = Config(yaml_file=str(yaml_path), ollama=OllamaConfig(base_url="http://init:1"))

    assert cfg.ollama.base_url == "http://init:1"


def test_safe_05_env_var_does_not_override_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 D-05/D-07: env-overlay is gone; YAML wins."""
    _clear_env(monkeypatch)
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://from-yaml:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
        encoding="utf-8",
    )
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://from-env:11434")
    monkeypatch.setenv("MCP_SERVER_COMMAND", "/usr/bin/should-be-ignored")
    cfg = Config(yaml_file=str(yaml_path))
    assert cfg.ollama.base_url == "http://from-yaml:11434"
    assert cfg.mcp_server.command == "/bin/true"


def test_safe_05_dotenv_file_in_cwd_has_no_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 D-07: .env is dead-letter for the framework."""
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text(
        "OLLAMA_BASE_URL=http://from-dotenv:11434\n",
        encoding="utf-8",
    )
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://from-yaml:11434\n  model: qwen3.6:latest\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    cfg = Config(yaml_file=str(yaml_path))
    assert cfg.ollama.base_url == "http://from-yaml:11434"


def test_safe_06_version_1_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 13 D-08: v1 schemas raise so the SAFE-06 ERROR-STYLE mapper
    can render the locked migration message."""
    _clear_env(monkeypatch)
    yaml_path = tmp_path / "v1.yaml"
    yaml_path.write_text(
        "version: 1\n"
        "ollama:\n  base_url: http://x:11434\n  model: m\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
        encoding="utf-8",
    )
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Config(yaml_file=str(yaml_path))
    # Validator message phrasing must enable the mapper at
    # cli.py:_emit_operator_error_for_validation to match.
    assert "not supported by this build" in str(exc_info.value)
    assert "expected 2" in str(exc_info.value)


def test_safe_06_version_2_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    yaml_path = tmp_path / "v2.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://x:11434\n  model: m\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
        encoding="utf-8",
    )
    cfg = Config(yaml_file=str(yaml_path))
    assert cfg.version == 2


def test_top_level_config_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating a top-level Config field raises ValidationError."""
    _clear_env(monkeypatch)
    cfg = Config(test_code=_TEST_CODE_STUB)

    with pytest.raises((pydantic_core.ValidationError, ValueError, TypeError)):
        cfg.judge_timeout_seconds = 999  # type: ignore[misc]


def test_sub_model_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating a sub-model field raises -- verifies Assumption A5 in 01-RESEARCH.md."""
    _clear_env(monkeypatch)
    cfg = Config(test_code=_TEST_CODE_STUB)

    with pytest.raises((pydantic_core.ValidationError, ValueError, TypeError)):
        cfg.ollama.model = "X"  # type: ignore[misc]


def test_no_yaml_path_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config() with no kwargs returns model defaults."""
    _clear_env(monkeypatch)

    cfg = Config(test_code=_TEST_CODE_STUB)

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"


def test_invalid_yaml_path_skips_yaml_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config(yaml_file=<non-existent>) does not raise — YamlSource skips
    a non-existent file (Path.is_file guard inside settings_customise_sources)."""
    _clear_env(monkeypatch)

    cfg = Config(yaml_file="/does/not/exist.yaml", test_code=_TEST_CODE_STUB)

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"


def test_mcp_server_timeout_seconds_env_has_no_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 13 D-05: env-overlay dropped; MCP_SERVER_TIMEOUT_SECONDS in
    os.environ has ZERO effect on Config(). (Inverted from v1.1's
    env-overlay regression guard.)"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_SERVER_TIMEOUT_SECONDS", "5")

    cfg = Config(test_code=_TEST_CODE_STUB)

    # Model default wins; env var is ignored.
    assert cfg.mcp_server.timeout_seconds == 30


def test_no_cwd_config_yaml_auto_discovery_and_no_fail_loud(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """LOCKS BOTH halves of SEED-006 (CONTEXT.md decision).

    Two halves are locked together because the v1.2 redesign (SEED-006)
    couples them:
      (1) NO cwd auto-discovery: with no MCPTF_CONFIG_FILE env var set
          and a config.yaml present in cwd, Config() does NOT pick it up.
      (2) NO fail-loud on missing config: Config() does NOT raise when
          no config.yaml is discoverable; it returns model defaults.

    If a future contributor flips EITHER half, this test fails with a
    message naming WHICH half flipped, so the contributor knows which
    SEED-006 component they triggered.

    The v1.2 redesign that ENABLES cwd auto-discovery AND/OR fail-loud
    is tracked under SEED-006 in .planning/seeds/. When that redesign
    lands, this test should be inverted (or deleted) DELIBERATELY in
    the same commit that amends the CONTEXT.md decision and updates
    config.py:settings_customise_sources. Until then, this test
    prevents drift.

    Tagged `decision-lock` in plan 12-09 frontmatter — this task
    enforces a CONTEXT.md decision rather than a numbered requirement
    (per checker NIT #2 disposition).
    """
    _clear_env(monkeypatch)
    # _isolate_cwd autouse fixture has already chdir'd to a fresh tmp dir.
    # Write a config.yaml at cwd that, IF auto-discovered, would override
    # mcp_server.command to a sentinel value.
    cwd_config = Path.cwd() / "config.yaml"
    cwd_config.write_text(
        "mcp_server:\n"
        "  command: sentinel-cwd-auto-discovery-canary\n",
        encoding="utf-8",
    )

    # Half 2 first: prove Config() does not raise. If the v1.2
    # fail-loud half lands first, this raises and the assertion error
    # explicitly names which half flipped.
    try:
        cfg = Config(test_code=_TEST_CODE_STUB)
    except Exception as exc:  # noqa: BLE001 -- intentional broad catch
        raise AssertionError(
            "SEED-006 half (2) has flipped: Config() now raises when no "
            "MCPTF_CONFIG_FILE is set and no auto-discovery picks up "
            f"cwd/config.yaml. Underlying error: {type(exc).__name__}: {exc}.\n"
            "If you intended to enable fail-loud-on-missing-config, "
            "delete this test in the same commit that amends CONTEXT.md "
            "and config.py:settings_customise_sources. Otherwise, you have a bug."
        ) from exc

    # Half 1: prove no cwd auto-discovery (the canary did NOT bleed in).
    assert cfg.mcp_server.command != "sentinel-cwd-auto-discovery-canary", (
        "SEED-006 half (1) has flipped: cwd auto-discovery is now ENABLED "
        "(the canary value from cwd/config.yaml leaked into Config()).\n"
        "If you intended to enable cwd auto-discovery, delete this test "
        "in the same commit that amends CONTEXT.md and "
        "config.py:settings_customise_sources. Otherwise, you have a bug."
    )

    # Stronger: prove the model default ('homelab-mcp') is what landed.
    assert cfg.mcp_server.command == "homelab-mcp", (
        f"unexpected cfg.mcp_server.command={cfg.mcp_server.command!r}; "
        "test expected the McpServerConfig model default since cwd "
        "auto-discovery is locked off. If McpServerConfig.command default "
        "has been changed (the DEFERRED bullet from UAT gap 2 / "
        "project_genericize_example_config), update this expectation in "
        "the same commit."
    )


def test_phase_13_d_11_target_block_in_yaml_rejected(tmp_path: Path) -> None:
    """Phase 13 D-11: v2 has no `target:` field. A leftover v1 `target:`
    block triggers extra=forbid at load time (defense-in-depth alongside
    the SAFE-06 version refusal)."""
    yaml_path = tmp_path / "leftover.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "target:\n  tool_name: list_registered_servers\n"
        "ollama:\n  base_url: http://x:11434\n  model: m\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n"
        + _TEST_CODE_YAML_BLOCK,
        encoding="utf-8",
    )
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Config(yaml_file=str(yaml_path))
    assert any(
        e.get("loc", ()) == ("target",) and e.get("type") == "extra_forbidden"
        for e in exc_info.value.errors()
    )
