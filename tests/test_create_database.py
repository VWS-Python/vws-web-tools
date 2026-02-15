"""Tests which create real databases on Vuforia."""

import datetime
import os
import uuid

import yaml
from click.testing import CliRunner

from vws_web_tools import vws_web_tools_group


def test_create_databases() -> None:
    """Test creating licenses and databases via the CLI."""
    email_address = os.environ["VWS_EMAIL_ADDRESS"]
    password = os.environ["VWS_PASSWORD"]
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-ci-{today_date}-{random_str}"
    database_name = f"database-ci-{today_date}-{random_str}"

    runner = CliRunner()

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-license",
            "--license-name",
            license_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-database",
            "--license-name",
            license_name,
            "--database-name",
            database_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-database-details",
            "--database-name",
            database_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    details = yaml.safe_load(stream=result.output)
    assert details["database_name"] == database_name
    assert details["server_access_key"]
    assert details["server_secret_key"]
    assert details["client_access_key"]
    assert details["client_secret_key"]

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-database-details",
            "--database-name",
            database_name,
            "--email-address",
            email_address,
            "--password",
            password,
            "--env-var-format",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    env_vars: dict[str, str] = dict(
        line.split(sep="=", maxsplit=1)
        for line in result.output.strip().split(sep="\n")
    )
    assert env_vars["VUFORIA_TARGET_MANAGER_DATABASE_NAME"] == database_name
    assert env_vars["VUFORIA_SERVER_ACCESS_KEY"]
    assert env_vars["VUFORIA_SERVER_SECRET_KEY"]
    assert env_vars["VUFORIA_CLIENT_ACCESS_KEY"]
    assert env_vars["VUFORIA_CLIENT_SECRET_KEY"]
