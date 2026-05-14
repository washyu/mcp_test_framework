# Cross-file SDET scenario ordering with `pytest-order`

The framework ships no custom cross-file ordering mechanism. Single-file
scenarios (the canonical idiom — see `tests/sdet/test_proxmox_vm_lifecycle.py`)
rely on pytest's file-order collection: tests run top-to-bottom within
one module without any markers.

If your scenario spans multiple files (e.g., a provision step in one
file and a drive step in another), add `pytest-order` to YOUR project's
dev dependencies (NOT this framework's) and annotate tests with
`@pytest.mark.order(N)`.

## Worked example

```python
# tests/sdet/test_provision.py
import pytest
import pytest_asyncio

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def provisioned_vm(mcp_session):
    # ... create VM, yield handle, teardown ...
    yield {"vmid": 9990}

@pytest.mark.order(1)
@pytest.mark.asyncio(loop_scope="session")
async def test_provision(provisioned_vm):
    assert provisioned_vm["vmid"] is not None
```

```python
# tests/sdet/test_drive.py
import pytest

@pytest.mark.order(2)
@pytest.mark.asyncio(loop_scope="session")
async def test_drive(provisioned_vm):
    # provisioned_vm is the same session-scoped instance from test_provision.
    # @pytest.mark.order(2) guarantees this runs AFTER test_provision even
    # though it lives in a different file.
    assert provisioned_vm["vmid"] is not None
```

## Why this is not framework-internal

- The framework's only dogfood scenario is single-file
  (`tests/sdet/test_proxmox_vm_lifecycle.py`), so the framework itself
  never imports `pytest-order`.
- Per Phase 19 D-11, `pytest-order` is NOT added to `pyproject.toml`.
- Promoting this recipe to a project dep is an opt-in operator decision.

## Phase 21 absorption

This file is the canonical source for the cross-file ordering pattern.
`docs/SDET-AUTHORING.md` (Phase 21 DOC-SDET-01) folds this content into
the public authoring guide; until then, this file is the authoritative
reference.
