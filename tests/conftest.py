"""Shared fixtures for fcontext tests."""
import pytest
from pathlib import Path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with .fcontext/ initialized."""
    from fcontext.init import init_workspace
    init_workspace(tmp_path, force=True)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """A bare temp directory (no .fcontext/)."""
    return tmp_path
