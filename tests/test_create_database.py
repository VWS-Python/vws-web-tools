"""Tests which create real databases on Vuforia.

This creates 100 licenses and databases.

If this passes around ~20 times we can be confident that at
least most of our tool works.
"""

import datetime
import json
import os
import uuid
from pathlib import Path

from selenium import webdriver

import vws_web_tools

_VWS_EMAIL_ADDRESS_VAR = "VWS_EMAIL_ADDRESS"
_VWS_PASSWORD_VAR = "VWS_PASSWORD"  # noqa: S105


def test_create_databases(
    tmp_path: Path,
) -> None:  # pragma: no cover
    """Test creating licenses and databases."""
    email_address = os.environ[_VWS_EMAIL_ADDRESS_VAR]
    password = os.environ[_VWS_PASSWORD_VAR]
    random_str = uuid.uuid4().hex[:5]
    today_date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    output_file_path = tmp_path / f"databases_details_{random_str}.txt"
    license_name_start = f"license-ci-{today_date}-{random_str}-"
    database_name_start = f"database-ci-{today_date}-{random_str}-"

    options: webdriver.ChromeOptions = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # type: ignore[misc]
    options.add_argument("--no-sandbox")  # type: ignore[misc]
    options.add_argument("--disable-dev-shm-usage")  # type: ignore[misc]
    driver = webdriver.Chrome(options=options)

    vws_web_tools.log_in(
        driver=driver,
        email_address=email_address,
        password=password,
    )

    vws_web_tools.wait_for_logged_in(driver=driver)

    for index in range(100):
        license_name = f"{license_name_start}{index}"
        database_name = f"{database_name_start}{index}"
        vws_web_tools.create_license(
            driver=driver,
            license_name=license_name,
        )
        vws_web_tools.create_database(
            driver=driver,
            database_name=database_name,
            license_name=license_name,
        )

        details = vws_web_tools.get_database_details(
            driver=driver,
            database_name=database_name,
        )

        assert details["database_name"]
        assert details["server_access_key"]
        assert details["server_secret_key"]
        assert details["client_access_key"]
        assert details["client_secret_key"]

        with output_file_path.open(mode="a") as handler:
            handler.write(json.dumps(obj=details))
            handler.write("\n")

    driver.close()
