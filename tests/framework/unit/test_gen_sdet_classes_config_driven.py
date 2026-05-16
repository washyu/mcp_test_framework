"""Phase 21.1 RELOC-02: gen-test-classes is config-driven via cfg.sdet.generated_root.

Phase 25 RENAME-02 (plan 25-02) renamed the Typer command from
gen-sdet-classes to gen-test-classes and the Python function from
gen_sdet_classes to gen_test_classes. The legacy CLI name still works
as a deprecation shim. Tests below pin the canonical new function symbol
via inspect; the legacy `_invoke("gen-sdet-classes", ...)` paths still
work for now but emit a DeprecationWarning -- those continue to exercise
the shim, which is intentional coverage for the v1.4 deprecation window.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _invoke(*args: str, env: dict | None = None):
    return CliRunner().invoke(app, list(args), env=env or {})


def _write_config_without_sdet(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump({
        "version": 2,
        "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
    }), encoding="utf-8")
    return p


def test_help_does_not_mention_legacy_hardcoded_path() -> None:
    result = _invoke("gen-sdet-classes", "--help")
    assert result.exit_code == 0, result.output
    assert "src/mcp_test_framework/sdet/generated" not in result.output, (
        "docstring still references the legacy hardcoded path; update per RELOC-02"
    )


def test_missing_sdet_generated_root_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    cfg = _write_config_without_sdet(tmp_path)
    result = _invoke("gen-sdet-classes", "--config", str(cfg))
    assert result.exit_code == 2, result.output
    # Existing SAFE-03 missing-required-field message is the contract.
    assert "missing a required field" in result.output
    assert "sdet" in result.output


def test_source_no_longer_hardcodes_path() -> None:
    """grep gate: cli.py:gen_test_classes must not contain the legacy hardcoded path string."""
    import inspect
    from mcp_test_framework.cli import gen_test_classes
    src = inspect.getsource(gen_test_classes)
    # Filter out lines starting with `#` (comments may legitimately mention
    # the legacy path in a migration note); the contract is the runtime
    # code path no longer constructs the legacy string.
    runtime_lines = [ln for ln in src.splitlines() if not ln.strip().startswith("#")]
    runtime = "\n".join(runtime_lines)
    assert 'Path(__file__).parent / "sdet" / "generated"' not in runtime
    assert "src/mcp_test_framework/sdet/generated/{slug}" not in runtime


def test_out_root_read_from_config() -> None:
    """Static check: the function body reads cfg.sdet.generated_root."""
    import inspect
    from mcp_test_framework.cli import gen_test_classes
    src = inspect.getsource(gen_test_classes)
    assert "cfg.sdet.generated_root" in src
