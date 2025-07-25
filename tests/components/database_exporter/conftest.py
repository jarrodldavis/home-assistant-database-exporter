"""Common fixtures for the Database Exporter tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from tests.typing import RecorderInstanceContextManager


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Set up recorder."""


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.database_exporter.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry
