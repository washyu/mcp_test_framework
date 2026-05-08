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
from mcp_test_framework.models import OllamaConfig

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

    cfg = Config()

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"
    assert cfg.ollama.model == "qwen3.6:latest"
    assert cfg.ollama.timeout_seconds == 120
    assert cfg.mcp_server.command == "homelab-mcp"
    assert cfg.mcp_server.args == []
    assert cfg.mcp_server.timeout_seconds == 30
    # Phase 07 D-01: tool_name default is None (discover-all mode); explicit
    # TARGET_TOOL_NAME restricts the run to a single tool (single-item parametrize).
    assert cfg.target.tool_name is None
    assert cfg.judge_timeout_seconds == 120


def test_env_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var beats default. Bare name routes via validation_alias."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:1")

    cfg = Config()

    assert cfg.ollama.base_url == "http://env:1"


def test_yaml_overrides_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """YAML overlay (via MCPTF_CONFIG_FILE) beats defaults when env is unset."""
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "ollama:\n  base_url: http://yaml:1\n",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))

    cfg = Config()

    assert cfg.ollama.base_url == "http://yaml:1"


def test_dotenv_routes_to_sub_model_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`.env` bare-name lines reach sub-model fields (regression: Phase 02.1
    follow-up — `.env`'s `MCP_SERVER_COMMAND=uvx` was previously a no-op)."""
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text(
        'MCP_SERVER_COMMAND=uvx\nMCP_SERVER_ARGS=["homelab-mcp"]\n', encoding="utf-8"
    )

    cfg = Config()

    assert cfg.mcp_server.command == "uvx"
    assert cfg.mcp_server.args == ["homelab-mcp"]


def test_env_overrides_dotenv_for_sub_model_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`os.environ` beats `.env` for sub-model fields (locked precedence)."""
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text("MCP_SERVER_COMMAND=from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("MCP_SERVER_COMMAND", "from-env")

    cfg = Config()

    assert cfg.mcp_server.command == "from-env"


def test_env_overrides_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The locked precedence inversion: env beats YAML."""
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "ollama:\n  base_url: http://yaml:1\n",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:1")

    cfg = Config()

    assert cfg.ollama.base_url == "http://env:1"


def test_init_overrides_env_and_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """init kwargs (CLI flag surface) beat env and YAML."""
    _clear_env(monkeypatch)
    yaml_path = _write_yaml(
        tmp_path,
        "ollama:\n  base_url: http://yaml:1\n",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:1")

    cfg = Config(ollama=OllamaConfig(base_url="http://init:1"))

    assert cfg.ollama.base_url == "http://init:1"


def test_top_level_config_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating a top-level Config field raises ValidationError."""
    _clear_env(monkeypatch)
    cfg = Config()

    with pytest.raises((pydantic_core.ValidationError, ValueError, TypeError)):
        cfg.judge_timeout_seconds = 999  # type: ignore[misc]


def test_sub_model_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating a sub-model field raises -- verifies Assumption A5 in 01-RESEARCH.md."""
    _clear_env(monkeypatch)
    cfg = Config()

    with pytest.raises((pydantic_core.ValidationError, ValueError, TypeError)):
        cfg.ollama.model = "X"  # type: ignore[misc]


def test_no_yaml_path_skips_yaml_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    """No MCPTF_CONFIG_FILE -> defaults remain in effect."""
    _clear_env(monkeypatch)

    cfg = Config()

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"


def test_invalid_yaml_path_skips_yaml_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    """MCPTF_CONFIG_FILE pointing at a non-existent file does not raise (Path.is_file guard)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", "/does/not/exist.yaml")

    cfg = Config()

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"


def test_mcp_server_timeout_seconds_env_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP_SERVER_TIMEOUT_SECONDS env var routes through _BareNameNestedEnvSource.

    Phase 1 LEARNINGS lesson "EnvSettingsSource does not walk sub-model
    validation_alias" means a missing precedence test would let the field
    silently default-fallback with no exception trace. This is the
    regression guard required by D-07.
    """
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_SERVER_TIMEOUT_SECONDS", "5")

    cfg = Config()

    assert cfg.mcp_server.timeout_seconds == 5
