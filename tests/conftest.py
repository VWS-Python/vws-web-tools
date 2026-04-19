"""Configuration, plugins and fixtures for `pytest`."""

import os

import pytest

from tests.credentials import VWSCredentials


@pytest.fixture(name="vws_credentials", scope="session")
def fixture_vws_credentials() -> VWSCredentials:
    """Get VWS credentials from environment variables."""
    return VWSCredentials(
        email_address=os.environ["VWS_EMAIL_ADDRESS"],
        password=os.environ["VWS_PASSWORD"],
    )
