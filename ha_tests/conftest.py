"""Real Home Assistant fixtures; all EcoFlow calls stay mocked."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow discovery of this repository's integration by HA."""
