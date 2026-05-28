"""Phase 34-09 gap closure / ISOL-05 / 34-VERIFICATION.md CR-01+WR-05.

Three regression pins for the corrected bare-Config() call sites:

1. ``Config()`` raises ``pydantic.ValidationError`` -- pins WHY the explicit
   construction is required (test_code is a REQUIRED field with no default
   since Phase 21.1; the old audit rows claiming "inherits strict default"
   were false).

2. ``Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))``
   constructs successfully and ``.host_isolation == "strict"`` -- pins the
   corrected fallback shape used at all four call sites.

3. The proxmox scenario module text has NO ``cfg = Config()`` and has
   ``TestCodeConfig(generated_root=`` exactly twice -- pins that the corrected
   sites cannot silently regress to bare Config().
   (File read as text; the module is NOT imported -- it carries live_homelab
   markers and would attempt to load generated classes at import time.)
"""
from __future__ import annotations


def test_bare_config_raises_validation_error() -> None:
    """Config() raises ValidationError because test_code is REQUIRED (Phase 21.1).

    This is the invariant that made the audit's 'inherits strict default'
    classification false -- ValidationError fires before any default is evaluated.
    """
    import pytest
    from pydantic import ValidationError

    from mcp_test_framework.config import Config

    with pytest.raises(ValidationError) as exc_info:
        Config()

    # The error must mention the test_code field.
    assert "test_code" in str(exc_info.value), (
        "ValidationError should mention the missing 'test_code' field; "
        f"got: {exc_info.value}"
    )


def test_explicit_construction_succeeds_with_strict_default() -> None:
    """Explicit Config(test_code=...) constructs without error; host_isolation defaults to 'strict'.

    Pins the corrected fallback shape used at all four bare-Config() sites:
    fixtures.py, session.py, and the two proxmox scenario sites.
    """
    from mcp_test_framework.config import Config
    from mcp_test_framework.models import TestCodeConfig

    cfg = Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))
    # host_isolation keeps its 'strict' default once test_code is supplied.
    assert cfg.host_isolation == "strict", (
        f"Expected host_isolation='strict' (the default), got {cfg.host_isolation!r}"
    )


def test_proxmox_scenario_module_has_no_bare_config() -> None:
    """The proxmox scenario file has no bare cfg = Config() and has TestCodeConfig twice.

    Pins that the corrected sites (module-level _load_generated_homelab_mcp and
    fixture-body proxmox_vm_lifecycle_readme) cannot silently regress to bare Config().

    The file is read as TEXT, not imported -- the module carries live_homelab markers
    and would attempt to load generated classes at import time.
    """
    from pathlib import Path

    # Resolve path relative to this test file's location (tests/framework/unit/).
    # Proxmox scenario lives at tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py.
    this_file = Path(__file__).resolve()
    repo_root = this_file.parent.parent.parent.parent  # up from unit/ -> framework/ -> tests/ -> repo root
    scenario_path = repo_root / "tests" / "test_code" / "test_proxmox_vm_lifecycle_readme_sample.py"

    src = scenario_path.read_text(encoding="utf-8")

    # No bare bare bare Config() call: cfg = Config() must be absent.
    assert "cfg = Config()" not in src, (
        "Proxmox scenario still contains bare 'cfg = Config()' -- "
        "regression: bare Config() raises ValidationError (test_code REQUIRED)"
    )

    # Both corrected sites must use explicit TestCodeConfig construction.
    explicit_count = src.count("TestCodeConfig(generated_root=")
    assert explicit_count == 2, (
        f"Expected TestCodeConfig(generated_root= exactly 2 times in proxmox scenario, "
        f"got {explicit_count}"
    )
