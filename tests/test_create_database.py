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


@pytest.fixture(name="logged_in_chrome_driver", scope="module")
def fixture_logged_in_chrome_driver(
    vws_credentials: VWSCredentials,
) -> Iterator[WebDriver]:
    """Yield a headless Chrome WebDriver that is logged in."""
    driver = vws_web_tools.create_chrome_driver()
    vws_web_tools.log_in(
        driver=driver,
        email_address=vws_credentials.email_address,
        password=vws_credentials.password,
    )
    yield driver
    driver.quit()


def _create_cli_license(vws_credentials: VWSCredentials) -> str:
    """Create a license via the CLI and return its name."""
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-ci-{today_date}-{random_str}"
    runner = CliRunner()
    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-license",
            "--license-name",
            license_name,
            "--email-address",
            vws_credentials.email_address,
            "--password",
            vws_credentials.password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    return license_name


@pytest.fixture(name="license_name", scope="module")
def fixture_license_name(
    vws_credentials: VWSCredentials,
) -> str:
    """Create a license via the CLI and return its name."""
    return _create_cli_license(vws_credentials=vws_credentials)


@pytest.fixture(name="cli_license_name", scope="module")
def fixture_cli_license_name(
    vws_credentials: VWSCredentials,
) -> str:
    """Create a license via the CLI and return its name."""
    return _create_cli_license(vws_credentials=vws_credentials)


def test_create_databases_library(
    *,
    logged_in_chrome_driver: WebDriver,
    license_name: str,
) -> None:
    """Test creating databases via the library."""
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-ci-{today_date}-{random_str}"

    license_details = vws_web_tools.get_license_details(
        driver=logged_in_chrome_driver,
        license_name=license_name,
    )
    assert license_details["license_name"] == license_name
    assert license_details["license_key"]

    vws_web_tools.create_cloud_database(
        driver=logged_in_chrome_driver,
        database_name=database_name,
        license_name=license_name,
    )

    details = vws_web_tools.get_database_details(
        driver=logged_in_chrome_driver,
        database_name=database_name,
    )

    assert details["database_name"] == database_name
    assert details["server_access_key"]
    assert details["server_secret_key"]
    assert details["client_access_key"]
    assert details["client_secret_key"]


def test_delete_license_library(
    *,
    chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
) -> None:
    """Test deleting a license via the library."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-del-ci-{today_date}-{random_str}"

    vws_web_tools.log_in(
        driver=chrome_driver,
        email_address=email_address,
        password=password,
    )

    vws_web_tools.create_license(
        driver=chrome_driver,
        license_name=license_name,
    )

    license_details = vws_web_tools.get_license_details(
        driver=chrome_driver,
        license_name=license_name,
    )
    assert license_details["license_name"] == license_name
    assert license_details["license_key"]

    vws_web_tools.delete_license(
        driver=chrome_driver,
        license_name=license_name,
    )


def test_delete_license_cli(
    *,
    vws_credentials: VWSCredentials,
) -> None:
    """Test deleting a license via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-del-ci-{today_date}-{random_str}"

    runner = CliRunner()

    create_result = runner.invoke(
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
    assert create_result.exit_code == 0
    assert create_result.output == ""

    show_license_result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-license-details",
            "--license-name",
            license_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert show_license_result.exit_code == 0
    license_details = yaml.safe_load(stream=show_license_result.output)
    assert license_details["license_name"] == license_name
    assert license_details["license_key"]

    delete_result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "delete-vws-license",
            "--license-name",
            license_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert delete_result.exit_code == 0
    assert delete_result.output == ""


def test_create_vumark_database_library(
    *,
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
    *,
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
    *,
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


def test_upload_vumark_template_cli(
    *,
    vws_credentials: VWSCredentials,
    request: pytest.FixtureRequest,
) -> None:
    """Test uploading a VuMark SVG template via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-vumark-ci-{today_date}-{random_str}"
    template_name = f"template-{random_str}"

    test_file_path = request.path
    assert test_file_path is not None
    svg_path = test_file_path.parent / "fixtures" / "vumark_template.svg"
    runner = CliRunner()

    create_database_result = runner.invoke(
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
    assert create_database_result.exit_code == 0

    upload_template_result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "upload-vumark-template",
            "--database-name",
            database_name,
            "--svg-file-path",
            str(object=svg_path),
            "--template-name",
            template_name,
            "--width",
            "1.0",
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert upload_template_result.exit_code == 0

    wait_for_instance_id_result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "wait-for-vumark-instance-id",
            "--database-name",
            database_name,
            "--target-name",
            template_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert wait_for_instance_id_result.exit_code == 0
    wait_instance_id = wait_for_instance_id_result.output.strip()
    expected_target_id_length = 32
    assert len(wait_instance_id) == expected_target_id_length
    assert wait_instance_id.isalnum()

    get_instance_id_result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "get-vumark-instance-id",
            "--database-name",
            database_name,
            "--target-name",
            template_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert get_instance_id_result.exit_code == 0
    get_instance_id = get_instance_id_result.output.strip()
    assert get_instance_id == wait_instance_id


def test_get_vumark_target_id(
    *,
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

    vws_web_tools.wait_for_vumark_target_link(
        driver=chrome_driver,
        database_name=database_name,
        target_name=template_name,
    )

    target_id = vws_web_tools.get_vumark_target_id(
        driver=chrome_driver,
        database_name=database_name,
        target_name=template_name,
    )
    expected_target_id_length = 32
    assert len(target_id) == expected_target_id_length
    assert target_id.isalnum()


def test_get_license_details_library(
    *,
    logged_in_chrome_driver: WebDriver,
    license_name: str,
) -> None:
    """Test getting license details via the library."""
    details = vws_web_tools.get_license_details(
        driver=logged_in_chrome_driver,
        license_name=license_name,
    )

    assert details["license_name"] == license_name
    assert details["license_key"]


def test_show_license_details_cli(
    *,
    vws_credentials: VWSCredentials,
    license_name: str,
) -> None:
    """Test showing license details via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password

    runner = CliRunner()

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-license-details",
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
    details = yaml.safe_load(stream=result.output)
    assert details["license_name"] == license_name
    assert details["license_key"]

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-license-details",
            "--license-name",
            license_name,
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
    assert env_vars["VUFORIA_LICENSE_NAME"] == license_name
    assert env_vars["VUFORIA_LICENSE_KEY"]


def test_create_databases_cli(
    *,
    vws_credentials: VWSCredentials,
    cli_license_name: str,
) -> None:
    """Test creating databases via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-ci-{today_date}-{random_str}"

    runner = CliRunner()

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "show-license-details",
            "--license-name",
            cli_license_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    license_details = yaml.safe_load(stream=result.output)
    assert license_details["license_name"] == cli_license_name
    assert license_details["license_key"]

    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "create-vws-cloud-database",
            "--license-name",
            cli_license_name,
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
