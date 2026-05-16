"""Phase 21.1 RELOC-02: source-invariant pins for the rewritten mcp_session loader."""
from __future__ import annotations

import inspect
import re


def _session_source() -> str:
    from mcp_test_framework.test_code import session
    return inspect.getsource(session)


def _runtime_lines(src: str) -> str:
    """Return source with `#`-leading lines stripped, so grep gates ignore comments."""
    return "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))


def test_uses_spec_from_file_location() -> None:
    assert "spec_from_file_location" in _session_source()


def test_uses_submodule_search_locations() -> None:
    """Non-negotiable kwarg for relative imports inside generated __init__.py."""
    assert "submodule_search_locations" in _session_source()


def test_no_importlib_import_module_at_runtime() -> None:
    """Old loader replaced; only the file-location loader remains in runtime code."""
    runtime = _runtime_lines(_session_source())
    assert "importlib.import_module(" not in runtime, (
        "session.py runtime code must not call importlib.import_module; "
        "RELOC-02 mandates spec_from_file_location"
    )


def test_phase_04_1_no_anyio_cancel_scope() -> None:
    """Phase 04.1 invariant: no `with anyio.*` or CancelScope across the yield."""
    matches = re.findall(r"with anyio\.|CancelScope", _session_source())
    assert matches == [], f"found anyio cancel scopes: {matches}"


def test_reads_cfg_test_code_generated_root() -> None:
    # Phase 25 RENAME-05: Pydantic field renamed sdet -> test_code; the session
    # loader now reads cfg.test_code.generated_root (alias remains valid for
    # YAML keys via AliasChoices, but Python attribute access uses the new name).
    assert "cfg.test_code.generated_root" in _session_source()


def test_uses_operator_tone_exit_for_missing_dir() -> None:
    assert "_pytest_exit_operator_tone" in _session_source()
