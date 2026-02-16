"""Tests for create-vws-database CLI behavior."""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner

import vws_web_tools
from vws_web_tools import vws_web_tools_group


def test_create_vws_database_vumark_without_license_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creating a VuMark database does not require a license name."""
    dummy_driver = Mock()
    create_database = Mock()
    monkeypatch.setattr(
        target=vws_web_tools,
        name="create_chrome_driver",
        value=Mock(return_value=dummy_driver),
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="log_in",
        value=Mock(),
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="wait_for_logged_in",
        value=Mock(),
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="create_database",
        value=create_database,
    )

    result = CliRunner().invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-database",
            "--database-name",
            "vumark-db",
            "--database-type",
            "vumark",
            "--email-address",
            "user@example.com",
            "--password",
            "password",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    create_database.assert_called_once_with(
        driver=dummy_driver,
        database_name="vumark-db",
        license_name=None,
        database_type="vumark",
    )
