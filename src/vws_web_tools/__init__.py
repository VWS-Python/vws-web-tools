"""
Tools for interacting with the VWS (Vuforia Web Services) website.
"""

import contextlib
import time
from typing import TypedDict

import click
import yaml
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait


class DatabaseDict(TypedDict):
    """
    A dictionary type which represents a database.
    """

    database_name: str
    server_access_key: str
    server_secret_key: str
    client_access_key: str
    client_secret_key: str


def log_in(
    driver: WebDriver,
    email_address: str,
    password: str,
) -> None:  # pragma: no cover
    """
    Log in to Vuforia web services.
    """
    log_in_url = "https://developer.vuforia.com/vui/auth/login"
    driver.get(log_in_url)
    email_address_input_element = driver.find_element(By.ID, "login_email")
    email_address_input_element.send_keys(email_address)

    password_input_element = driver.find_element(By.ID, "login_password")
    password_input_element.send_keys(password)
    password_input_element.send_keys(Keys.RETURN)


def wait_for_logged_in(
    driver: WebDriver,
) -> None:  # pragma: no cover
    """
    Wait for the user to be logged in.

    Without this, we sometimes get a redirect to a post-login page.
    """
    ten_second_wait = WebDriverWait(driver, 10)
    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, "userNameInHeaderSpan"),
        ),
    )


def create_license(
    driver: WebDriver,
    license_name: str,
) -> None:  # pragma: no cover
    """
    Create a license.
    """
    licenses_url = "https://developer.vuforia.com/vui/develop/licenses"
    driver.get(licenses_url)

    ten_second_wait = WebDriverWait(driver, 10)

    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, "get-development-key"),
        ),
    )

    ten_second_wait.until(
        expected_conditions.element_to_be_clickable(
            (By.ID, "get-development-key"),
        ),
    )

    get_development_key_button_element = driver.find_element(
        By.ID,
        "get-development-key",
    )
    get_development_key_button_element.click()
    try:
        get_development_key_button_element.click()
        time.sleep(1)
        get_development_key_button_element.click()
    except WebDriverException:
        pass

    license_name_input_element = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, "license-name"),
        ),
    )

    license_name_input_element.send_keys(license_name)

    agree_terms_id = "agree-terms-checkbox"
    agree_terms_checkbox_element = driver.find_element(
        By.ID,
        agree_terms_id,
    )
    agree_terms_checkbox_element.submit()


def create_database(
    driver: WebDriver,
    database_name: str,
    license_name: str,
) -> None:  # pragma: no cover
    """
    Create a database.
    """
    target_manager_url = "https://developer.vuforia.com/vui/develop/databases"
    driver.get(target_manager_url)
    ten_second_wait = WebDriverWait(driver, 10)

    add_database_button_id = "add-dialog-btn"
    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, add_database_button_id),
        ),
    )

    ten_second_wait.until(
        expected_conditions.element_to_be_clickable(
            (By.ID, add_database_button_id),
        ),
    )

    add_database_button_element = driver.find_element(
        By.ID,
        add_database_button_id,
    )
    add_database_button_element.click()
    with contextlib.suppress(WebDriverException):
        add_database_button_element.click()
    database_name_id = "database-name"
    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, database_name_id),
        ),
    )

    database_name_element = driver.find_element(By.ID, database_name_id)
    database_name_element.send_keys(database_name)

    cloud_type_radio_element = driver.find_element(By.ID, "cloud-radio-btn")
    cloud_type_radio_element.click()

    license_dropdown_element = Select(
        driver.find_element(
            By.ID,
            "cloud-license-dropdown",
        ),
    )

    # Sleeping 1 second here did not work, so we sleep 5 seconds.
    time.sleep(5)
    license_dropdown_element.select_by_visible_text(text=license_name)

    create_button = driver.find_element(By.ID, "create-btn")
    create_button.click()


def get_database_details(
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:  # pragma: no cover
    """
    Get details of a database.
    """
    target_manager_url = "https://developer.vuforia.com/vui/develop/databases"
    driver.get(target_manager_url)
    ten_second_wait = WebDriverWait(driver, 10)

    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, "table_search"),
        ),
    )

    search_input_element = driver.find_element(By.ID, "table_search")
    search_input_element.send_keys(database_name)
    search_input_element.send_keys(Keys.RETURN)
    # # This is a hack.
    # #
    # # Not all items are shown on the first page and we do not yet support going
    # # through pages.
    # #
    # # In our use cases so far we always want the latest databases.
    # #
    # #
    # # Therefore we sort by last modified date.
    # time.sleep(5)
    # date_modified_element = driver.find_element(
    #     By.ID,
    #     "sort-by-last-modified-date",
    # )
    # date_modified_element.click()
    # time.sleep(10)
    # date_modified_element.click()
    # date_modified_element.click()

    # time.sleep(2)
    # database_name_xpath = "//span[text()='" + database_name + "']"

    breakpoint()
    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, "table_row_0_app_name"),
        ),
    )

    database_cell_element = ten_second_wait.until(
        expected_conditions.element_to_be_clickable(
            (By.XPATH, "table_row_0_app_name"),
        ),
    )

    database_cell_element.click()

    access_keys_tab_item = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.LINK_TEXT, "Database Access Keys"),
        ),
    )

    access_keys_tab_item.click()

    # Without this we sometimes get empty strings for the keys.
    time.sleep(1)

    client_access_key = driver.find_element(
        By.CLASS_NAME,
        "client-access-key",
    ).text
    client_secret_key = driver.find_element(
        By.CLASS_NAME,
        "client-secret-key",
    ).text
    server_access_key = driver.find_element(
        By.CLASS_NAME,
        "server-access-key",
    ).text
    server_secret_key = driver.find_element(
        By.CLASS_NAME,
        "server-secret-key",
    ).text

    return {
        "database_name": database_name,
        "server_access_key": str(server_access_key),
        "server_secret_key": str(server_secret_key),
        "client_access_key": str(client_access_key),
        "client_secret_key": str(client_secret_key),
    }


@click.group(name="vws-web")
def vws_web_tools_group() -> None:
    """
    Commands for interacting with VWS.
    """


@click.command()
@click.option("--license-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
def create_vws_license(
    license_name: str,
    email_address: str,
    password: str,
) -> None:  # pragma: no cover
    """
    Create a license.
    """
    driver = webdriver.Safari()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    create_license(driver=driver, license_name=license_name)
    driver.close()


@click.command()
@click.option("--license-name", required=True)
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
def create_vws_database(
    database_name: str,
    license_name: str,
    email_address: str,
    password: str,
) -> None:  # pragma: no cover
    """
    Create a database.
    """
    driver = webdriver.Safari()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    create_database(
        driver=driver,
        database_name=database_name,
        license_name=license_name,
    )
    driver.close()


@click.command()
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
def show_database_details(
    database_name: str,
    email_address: str,
    password: str,
) -> None:  # pragma: no cover
    """
    Show the details of a database.
    """
    driver = webdriver.Safari()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    details = get_database_details(driver=driver, database_name=database_name)
    driver.close()
    click.echo(yaml.dump(details), nl=False)


vws_web_tools_group.add_command(create_vws_database)
vws_web_tools_group.add_command(create_vws_license)
vws_web_tools_group.add_command(show_database_details)
