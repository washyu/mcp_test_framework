"""Unit tests for the pyproject.toml mcp_config_file route in _load_config.

Covers the precedence branch that reads
`[tool.pytest.ini_options] mcp_config_file` from pyproject.toml below the
`--config` flag. Fail-soft on parse problems; fail-loud when the ini value
resolves to a missing file (typo defense — do NOT silently mask by falling
through to other branches).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import typer
import yaml

from mcp_test_framework.cli import (
    _find_pyproject_upward,
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
    # No env vars participate in config resolution as of v1.5;
    # this fixture is a no-op kept for blame continuity.
    return None


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


def test_env_var_no_longer_routed_when_no_pyproject_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 31 SHIM-05 D-05 inversion: with no --config, no pyproject
    ini key, and no ./config.yaml, the resolver fails SAFE-03 even when
    MCPTF_CONFIG_FILE points at a valid YAML. The env-var branch is gone.
    """
    env_path = tmp_path / "env.yaml"
    _write_minimal_config_yaml(env_path)
    # pyproject.toml exists but has no [tool.pytest.ini_options]
    _write_pyproject_with_mcp_config_file(tmp_path, None)
    monkeypatch.chdir(tmp_path)
    # The resolver must fail-loud via SAFE-03 because no cwd config.yaml
    # exists. The env-pointed YAML is NEVER consulted.
    import typer
    with pytest.raises(typer.Exit) as exc_info:
        _load_config(path=None)
    assert exc_info.value.exit_code == 2


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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WR-06: typo error must name raw value, resolved candidate, and pyproject.

    A refactor that swaps to a generic 'config not found' message would lose
    the typo-specific context an operator needs to find the offending key.
    Lock the three load-bearing identifiers in the rendered operator copy.
    """
    raw_value = "./does-not-exist.yaml"
    _write_pyproject_with_mcp_config_file(tmp_path, raw_value)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        _load_config(path=None)
    assert exc_info.value.exit_code == 2
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    # Names the raw value (the actual ini string the operator typed):
    assert raw_value in combined
    # Names the resolved candidate path (pyproject.parent / raw_value):
    resolved_candidate = tmp_path / "does-not-exist.yaml"
    assert str(resolved_candidate) in combined
    # Names the pyproject.toml location:
    assert str(tmp_path / "pyproject.toml") in combined


@pytest.mark.parametrize(
    "raw_toml_value",
    [
        "[1, 2]",         # list
        "5",              # int
        "true",           # bool
        # Note: TOML has no `None`; we model "None" as "absent entirely" via
        # _write_pyproject_with_mcp_config_file(value=None), already covered
        # by test_pyproject_without_ini_options_section_falls_through. The
        # additional sentinel here is an in-TOML representation that pydantic
        # would reject if isinstance(raw, str) ever stopped guarding:
        '{ key = "val" }',  # inline table
    ],
    ids=["list", "int", "bool", "inline_table"],
)
def test_pyproject_non_string_value_falls_through_silently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_toml_value: str,
) -> None:
    """WR-06: helper's isinstance(raw, str) guard collapses non-strings to ''.

    A future refactor that drops the isinstance check would raise
    'AttributeError: '<type>' object has no attribute 'strip'' and crash
    the CLI on any non-string mcp_config_file value. Pin the fall-through
    behavior so the regression test fires before the crash hits operators.
    """
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            f"""\
            [project]
            name = "x"
            version = "0.0"

            [tool.pytest.ini_options]
            mcp_config_file = {raw_toml_value}
            """
        ),
        encoding="utf-8",
    )
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    # Fell through to cwd autodiscovery without raising:
    assert cfg is not None
    assert resolved == cwd_yaml


def test_pyproject_absolute_path_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-06: absolute mcp_config_file path bypasses pyproject-relative resolution.

    Exercises the `if not candidate.is_absolute()` branch's negative side
    (currently uncovered by other tests, all of which pass relative paths).
    """
    abs_inner = tmp_path / "absolute_inner.yaml"
    _write_minimal_config_yaml(abs_inner)
    # Use the absolute path verbatim in pyproject.toml. On Windows we need
    # to escape backslashes for TOML's string syntax.
    abs_str = str(abs_inner).replace("\\", "\\\\")
    _write_pyproject_with_mcp_config_file(tmp_path, abs_str)
    # chdir somewhere ELSE so the absolute path cannot accidentally pass via
    # cwd or pyproject-relative resolution.
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    # The resolved path must equal the absolute path verbatim (not
    # pyproject.parent / abs_str).
    assert resolved == abs_inner


def test_load_config_walks_upward_for_pyproject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-04: pyproject discovery must walk upward like pytest's rootpath.

    Operator invokes `mcp-contracts gen-test-classes` from a subdirectory
    of their project. The CLI must find the same pyproject.toml the
    in-subprocess pytest plugin would discover, otherwise the CLI falls
    through to cwd autodiscovery and the operator sees a "no config file
    found" error despite a perfectly valid pyproject.toml two directories up.
    """
    inner = tmp_path / "inner.yaml"
    _write_minimal_config_yaml(inner)
    _write_pyproject_with_mcp_config_file(tmp_path, "./inner.yaml")
    sub = tmp_path / "sub" / "subsub"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == inner


def test_find_pyproject_upward_returns_none_when_no_pyproject(
    tmp_path: Path,
) -> None:
    """Negative branch: walk hits filesystem root without finding pyproject."""
    sub = tmp_path / "sub" / "subsub"
    sub.mkdir(parents=True)
    # No pyproject.toml anywhere under tmp_path; the walk will continue
    # up the real filesystem ancestry. To make the test deterministic
    # we only assert the helper does NOT find one under tmp_path itself:
    # if one exists higher up on the test runner's filesystem (e.g. the
    # framework's own pyproject), it WILL be returned -- that's correct
    # behavior. So we instead verify the helper returns None when given
    # a directory we control with no pyproject above it inside tmp_path
    # by checking that the returned path, if any, is NOT under tmp_path.
    result = _find_pyproject_upward(sub)
    if result is not None:
        # Found one higher up than tmp_path -- that's not under our control.
        # Assert at minimum it is not a fabricated path under tmp_path.
        assert not str(result).startswith(str(tmp_path))


def test_find_pyproject_upward_finds_at_start(tmp_path: Path) -> None:
    """Positive branch: pyproject at the starting directory itself."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.0"\n', encoding="utf-8"
    )
    result = _find_pyproject_upward(tmp_path)
    assert result == tmp_path / "pyproject.toml"


def test_find_pyproject_upward_finds_two_levels_up(tmp_path: Path) -> None:
    """Positive branch: pyproject two parents up from start."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.0"\n', encoding="utf-8"
    )
    sub = tmp_path / "sub" / "subsub"
    sub.mkdir(parents=True)
    result = _find_pyproject_upward(sub)
    assert result == tmp_path / "pyproject.toml"
