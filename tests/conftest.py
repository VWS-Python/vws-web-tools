"""Configuration, plugins and fixtures for `pytest`."""

import os

import pytest
from beartype import beartype

from tests.credentials import VWSCredentials


@pytest.fixture(name="vws_credentials")
def fixture_vws_credentials() -> VWSCredentials:
    """Get VWS credentials from environment variables."""
    return VWSCredentials(
        email_address=os.environ["VWS_EMAIL_ADDRESS"],
        password=os.environ["VWS_PASSWORD"],
    )


@beartype
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply the beartype decorator to all collected test functions."""
    for item in items:
        assert isinstance(item, pytest.Function)
        item.obj = beartype(obj=item.obj)
