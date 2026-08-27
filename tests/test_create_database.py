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


@pytest.fixture(name="_logged_in_session", autouse=True)
def fixture_logged_in_session(
    logged_in_chrome_driver: WebDriver,
    vws_credentials: VWSCredentials,
) -> None:
    """Log in again if the shared session has expired.

    ``logged_in_chrome_driver`` is module-scoped, so it logs in once and
    every test in the module shares that one session. A module which
    runs for longer than the session lasts leaves the later tests
    driving a logged-out browser, which surfaces as a timeout waiting
    for an element that is never going to appear. Load a page which
    needs a session before each test, and log in again if the portal
    sends the browser to the login page instead.
    """
    logged_in_chrome_driver.get(
        url="https://developer.vuforia.com/develop/databases",
    )
    current_url = logged_in_chrome_driver.current_url
    if "/auth/login" in current_url:  # pragma: no cover
        vws_web_tools.log_in(
            driver=logged_in_chrome_driver,
            email_address=vws_credentials.email_address,
            password=vws_credentials.password,
        )


@pytest.fixture(name="license_name", scope="module")
def fixture_license_name(
    logged_in_chrome_driver: WebDriver,
) -> str:
    """Create a license and return its name."""
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    license_name = f"license-ci-{today_date}-{random_str}"
    vws_web_tools.create_license(
        driver=logged_in_chrome_driver,
        license_name=license_name,
    )
    return license_name


@pytest.fixture(name="cli_license_name", scope="module")
def fixture_cli_license_name(
    vws_credentials: VWSCredentials,
) -> str:
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

    expected_database_id_length = 32
    assert len(details["database_id"]) == expected_database_id_length
    assert details["database_id"].isalnum()


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
    target_id = vws_web_tools.upload_vumark_template(
        driver=chrome_driver,
        database_name=database_name,
        svg_file_path=svg_path,
        template_name=template_name,
        width=1.0,
    )

    assert template_name in chrome_driver.page_source
    expected_target_id_length = 32
    assert len(target_id) == expected_target_id_length
    assert target_id.isalnum()


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


def test_get_model_target_web_api_details_library(
    *,
    logged_in_chrome_driver: WebDriver,
) -> None:
    """Test getting Model Target Web API details via the library."""
    with vws_web_tools.model_target_web_api_details(
        driver=logged_in_chrome_driver,
    ) as details:
        assert details["client_id"]
        assert details["client_secret"]
        assert details["cad_data_url"] == (
            "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/"
            "d7a3cc8e51d7c573771ae77a57f16b0662a905c6/"
            "2.0/Duck/glTF-Binary/Duck.glb"
        )
        assert details["cad_data_url"] == (
            vws_web_tools.MODEL_TARGET_WEB_API_CAD_DATA_URL
        )


def test_delete_model_target_web_api_credentials_cli(
    *,
    vws_credentials: VWSCredentials,
    logged_in_chrome_driver: WebDriver,
) -> None:
    """Test deleting Model Target Web API credentials via the CLI."""
    details = vws_web_tools.get_model_target_web_api_details(
        driver=logged_in_chrome_driver,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli=vws_web_tools_group,
        args=[
            "delete-model-target-web-api-credentials",
            "--client-id",
            details["client_id"],
            "--email-address",
            vws_credentials.email_address,
            "--password",
            vws_credentials.password,
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0


def test_show_model_target_web_api_details_cli(
    *,
    vws_credentials: VWSCredentials,
    logged_in_chrome_driver: WebDriver,
) -> None:
    """Test showing Model Target Web API details via the CLI."""
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    runner = CliRunner()
    client_ids: list[str] = []

    try:
        result = runner.invoke(
            cli=vws_web_tools_group,
            args=[
                "show-model-target-web-api-details",
                "--email-address",
                email_address,
                "--password",
                password,
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        details = yaml.safe_load(stream=result.output)
        client_ids.append(details["client_id"])
        assert details["client_secret"]
        assert details["cad_data_url"]

        result = runner.invoke(
            cli=vws_web_tools_group,
            args=[
                "show-model-target-web-api-details",
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
        client_ids.append(env_vars["MODEL_TARGET_VUFORIA_CLIENT_ID"])
        assert env_vars["MODEL_TARGET_VUFORIA_CLIENT_SECRET"]
        assert (
            env_vars["MODEL_TARGET_VUFORIA_CAD_DATA_URL"]
            == (details["cad_data_url"])
        )
    finally:
        for client_id in client_ids:
            vws_web_tools.delete_model_target_web_api_client_credentials(
                driver=logged_in_chrome_driver,
                client_id=client_id,
            )


def test_show_license_details_cli(
    *,
    vws_credentials: VWSCredentials,
    cli_license_name: str,
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
            cli_license_name,
            "--email-address",
            email_address,
            "--password",
            password,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    details = yaml.safe_load(stream=result.output)
    assert details["license_name"] == cli_license_name
    assert details["license_key"]

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
            "--env-var-format",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    env_vars: dict[str, str] = dict(
        line.split(sep="=", maxsplit=1)
        for line in result.output.strip().split(sep="\n")
    )
    assert env_vars["VUFORIA_LICENSE_NAME"] == cli_license_name
    assert env_vars["VUFORIA_LICENSE_KEY"]


def test_create_databases_cli(
    *,
    vws_credentials: VWSCredentials,
    cli_license_name: str,
) -> None:
    """Test creating databases via the CLI.

    Every CLI invocation here starts a browser and logs in, so each one
    added costs the slowest test in the suite another browser session.
    ``show-license-details`` is covered by
    ``test_show_license_details_cli``, against the same license, so it
    is deliberately not repeated here.
    """
    email_address = vws_credentials.email_address
    password = vws_credentials.password
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    database_name = f"database-ci-{today_date}-{random_str}"

    runner = CliRunner()

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

    expected_database_id_length = 32
    database_id = details["database_id"]
    assert len(database_id) == expected_database_id_length
    assert database_id.isalnum()

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
    assert env_vars["VUFORIA_DATABASE_ID"] == database_id
    assert env_vars["VUFORIA_SERVER_ACCESS_KEY"]
    assert env_vars["VUFORIA_SERVER_SECRET_KEY"]
    assert env_vars["VUFORIA_CLIENT_ACCESS_KEY"]
    assert env_vars["VUFORIA_CLIENT_SECRET_KEY"]
