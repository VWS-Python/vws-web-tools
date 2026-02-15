"""Tests which create real databases on Vuforia."""

import datetime
import os
import uuid
from collections.abc import Iterator

import pytest
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

import vws_web_tools


@pytest.fixture(name="chrome_driver")
def fixture_chrome_driver() -> Iterator[WebDriver]:
    """Yield a headless Chrome WebDriver, quitting on tear down."""
    options: webdriver.ChromeOptions = webdriver.ChromeOptions()
    options.add_argument(argument="--headless=new")
    options.add_argument(argument="--no-sandbox")
    options.add_argument(argument="--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def test_create_databases(
    chrome_driver: WebDriver,
) -> None:
    """Test creating licenses and databases."""
    email_address = os.environ["VWS_EMAIL_ADDRESS"]
    password = os.environ["VWS_PASSWORD"]
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
    vws_web_tools.create_database(
        driver=chrome_driver,
        database_name=database_name,
        license_name=license_name,
    )

    details = vws_web_tools.get_database_details(
        driver=chrome_driver,
        database_name=database_name,
    )

    assert details["database_name"]
    assert details["server_access_key"]
    assert details["server_secret_key"]
    assert details["client_access_key"]
    assert details["client_secret_key"]
