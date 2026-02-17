"""Tests which create real databases on Vuforia."""

import datetime
import uuid
from collections.abc import Iterator

import pytest
import yaml
from click.testing import CliRunner
from selenium.webdriver.remote.webdriver import WebDriver

import vws_web_tools
from tests.credentials import VWSCredentials
from vws_web_tools import vws_web_tools_group


@pytest.fixture(name="chrome_driver")
def fixture_chrome_driver() -> Iterator[WebDriver]:
    """Yield a headless Chrome WebDriver, quitting on tear down."""
    driver = vws_web_tools.create_chrome_driver()
    yield driver
    driver.quit()


def test_create_databases_library(
    chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
) -> None:
    """Test creating licenses and databases via the library."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-ci-{today_date}-{random_str}"
    database_name = f"database-ci-{today_date}-{random_str}"

    vws_web_tools.log_in(
        driver=chrome_driver,
        email_address=email_address,
        password=password,
    )

    vws_web_tools.wait_for_logged_in(driver=chrome_driver)

    vws_web_tools.create_license(
        driver=chrome_driver,
        license_name=license_name,
    )
    vws_web_tools.create_cloud_database(
        driver=chrome_driver,
        database_name=database_name,
        license_name=license_name,
    )

    details = vws_web_tools.get_database_details(
        driver=chrome_driver,
        database_name=database_name,
    )

    assert details["database_name"] == database_name
    assert details["server_access_key"]
    assert details["server_secret_key"]
    assert details["client_access_key"]
    assert details["client_secret_key"]


def test_create_vumark_database_library(
    chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
) -> None:
    """Test creating a VuMark database via the library."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-vumark-ci-{today_date}-{random_str}"

    vws_web_tools.log_in(
        driver=chrome_driver,
        email_address=email_address,
        password=password,
    )
    vws_web_tools.wait_for_logged_in(driver=chrome_driver)

    vws_web_tools.create_vumark_database(
        driver=chrome_driver,
        database_name=database_name,
    )

    details = vws_web_tools.get_vumark_database_details(
        driver=chrome_driver,
        database_name=database_name,
    )

    assert details["database_name"] == database_name
    assert details["server_access_key"]
    assert details["server_secret_key"]


def test_create_vumark_database_cli(
    vws_credentials: VWSCredentials,
) -> None:
    """Test creating a VuMark database via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-vumark-ci-{today_date}-{random_str}"

    runner = CliRunner()

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-vumark-database",
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
            "show-vumark-database-details",
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

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-vumark-database-details",
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


def test_upload_vumark_template(
    chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
    request: pytest.FixtureRequest,
) -> None:
    """Test uploading a VuMark SVG template via the library."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-vumark-ci-{today_date}-{random_str}"

    vws_web_tools.log_in(
        driver=chrome_driver,
        email_address=email_address,
        password=password,
    )
    vws_web_tools.wait_for_logged_in(driver=chrome_driver)

    vws_web_tools.create_vumark_database(
        driver=chrome_driver,
        database_name=database_name,
    )

    test_file_path = request.path
    assert test_file_path is not None
    svg_path = test_file_path.parent / "fixtures" / "vumark_template.svg"
    template_name = f"template-{random_str}"
    vws_web_tools.upload_vumark_template(
        driver=chrome_driver,
        database_name=database_name,
        svg_file_path=svg_path,
        template_name=template_name,
        width=1.0,
    )

    assert template_name in chrome_driver.page_source


def test_get_vumark_target_id(
    chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
    request: pytest.FixtureRequest,
) -> None:
    """Test getting a VuMark target ID via the library."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-vumark-ci-{today_date}-{random_str}"

    vws_web_tools.log_in(
        driver=chrome_driver,
        email_address=email_address,
        password=password,
    )
    vws_web_tools.wait_for_logged_in(driver=chrome_driver)

    vws_web_tools.create_vumark_database(
        driver=chrome_driver,
        database_name=database_name,
    )

    test_file_path = request.path
    assert test_file_path is not None
    svg_path = test_file_path.parent / "fixtures" / "vumark_template.svg"
    template_name = f"template-{random_str}"
    vws_web_tools.upload_vumark_template(
        driver=chrome_driver,
        database_name=database_name,
        svg_file_path=svg_path,
        template_name=template_name,
        width=1.0,
    )

    limitation_text = "rendered as a link"
    target_id: str | None = None
    caught_error: TypeError | None = None
    try:
        target_id = vws_web_tools.get_vumark_target_id(
            driver=chrome_driver,
            database_name=database_name,
            target_name=template_name,
        )
    except TypeError as exception:
        caught_error = exception

    if target_id is not None:
        expected_target_id_length = 32
        assert len(target_id) == expected_target_id_length
        assert target_id.isalnum()
    else:
        assert caught_error is not None
        assert limitation_text in str(caught_error)


def test_create_databases_cli(
    vws_credentials: VWSCredentials,
) -> None:
    """Test creating licenses and databases via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
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
            "create-vws-cloud-database",
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
