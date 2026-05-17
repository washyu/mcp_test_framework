"""Unit tests for the pyproject.toml mcp_config_file route in _load_config.

Covers the new precedence branch that reads
`[tool.pytest.ini_options] mcp_config_file` from pyproject.toml between the
`--config` flag and the `MCPTF_CONFIG_FILE` env-var branches. Fail-soft on
parse problems; fail-loud when the ini value resolves to a missing file
(typo defense — do NOT silently mask by falling through to other branches).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import typer
import yaml

from mcp_test_framework.cli import (
    _load_config,
    _read_mcp_config_file_from_pyproject,
)


def _write_minimal_config_yaml(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "mcp_server": {"command": "echo", "args": []},
                "test_code": {
                    "generated_root": str(path.parent / "_generated"),
                },
                "tools": {},
            }
        ),
        encoding="utf-8",
    )


def _write_pyproject_with_mcp_config_file(
    tmp_path: Path, mcp_config_file_value: str | None
) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    if mcp_config_file_value is None:
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "0.0"\n',
            encoding="utf-8",
        )
    else:
        pyproject.write_text(
            textwrap.dedent(
                f"""\
                [project]
                name = "x"
                version = "0.0"

                [tool.pytest.ini_options]
                mcp_config_file = "{mcp_config_file_value}"
                """
            ),
            encoding="utf-8",
        )
    return pyproject


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)


def test_gen_test_classes_uses_pyproject_ini_when_no_config_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inner = tmp_path / "inner.yaml"
    _write_minimal_config_yaml(inner)
    _write_pyproject_with_mcp_config_file(tmp_path, "./inner.yaml")
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == inner


def test_config_flag_overrides_pyproject_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject_inner = tmp_path / "from-pyproject.yaml"
    _write_minimal_config_yaml(pyproject_inner)
    flag_explicit = tmp_path / "from-flag.yaml"
    _write_minimal_config_yaml(flag_explicit)
    _write_pyproject_with_mcp_config_file(tmp_path, "./from-pyproject.yaml")
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=flag_explicit)
    assert cfg is not None
    assert resolved == flag_explicit


def test_env_var_still_works_when_no_pyproject_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / "env.yaml"
    _write_minimal_config_yaml(env_path)
    # pyproject.toml exists but has no [tool.pytest.ini_options]
    _write_pyproject_with_mcp_config_file(tmp_path, None)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(env_path))
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == env_path


def test_missing_pyproject_falls_through_to_cwd_autodiscovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    # No pyproject.toml at all
    assert not (tmp_path / "pyproject.toml").exists()
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_malformed_pyproject_falls_through_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[broken\nthis is not valid toml", encoding="utf-8"
    )
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_pyproject_without_ini_options_section_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, None)
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_pyproject_empty_string_value_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, "")
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_relative_path_resolves_against_pyproject_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    inner = sub / "inner.yaml"
    _write_minimal_config_yaml(inner)
    _write_pyproject_with_mcp_config_file(tmp_path, "./subdir/inner.yaml")
    # Run from a DIFFERENT directory to prove resolution is pyproject-relative
    # and NOT cwd-relative. Direct helper call exercises pure pyproject-relative
    # resolution semantics (no cwd fall-through interference).
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    resolved_path, pyproject_path = _read_mcp_config_file_from_pyproject(tmp_path)
    assert resolved_path == inner
    assert pyproject_path == tmp_path / "pyproject.toml"


def test_pyproject_typo_value_raises_fail_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, "./does-not-exist.yaml")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        _load_config(path=None)
    assert exc_info.value.exit_code == 2
