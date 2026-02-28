"""Shared pytest fixtures for the AI Trading test suite."""

from pathlib import Path

import pytest

# Absolute path to the project root (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def default_config_path():
    """Absolute path to the default YAML config."""
    return PROJECT_ROOT / "configs" / "default.yaml"
