"""Shared pytest fixtures for the AI Trading test suite."""

import pytest


@pytest.fixture
def default_config_path():
    """Path to the default YAML config."""
    return "configs/default.yaml"
