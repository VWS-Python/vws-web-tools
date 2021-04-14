"""
Tools for interacting with the VWS (Vuforia Web Services) website.
"""

import time
from typing import TypedDict

import click
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


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
    log_in_url = 'https://developer.vuforia.com/vui/auth/login'
    driver.get(log_in_url)
    email_address_input_element = driver.find_element_by_id('login_email')
    email_address_input_element.send_keys(email_address)

    password_input_element = driver.find_element_by_id('login_password')
    password_input_element.send_keys(password)
    password_input_element.send_keys(Keys.RETURN)

    # This shows that the log in is complete.
    ten_second_wait = WebDriverWait(driver, 10)

    ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, 'get-development-key'),
        ),
    )


def create_license(
    driver: WebDriver,
    license_name: str,
) -> None:  # pragma: no cover
    """
    Create a license.
    """
    licenses_url = 'https://developer.vuforia.com/vui/develop/licenses'
    driver.get(licenses_url)

    ten_second_wait = WebDriverWait(driver, 10)

    get_development_key_button_element = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, 'get-development-key'),
        ),
    )

    get_development_key_button_element.click()

    license_name_input_element = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, 'license-name'),
        ),
    )

    license_name_input_element.send_keys(license_name)

    agree_terms_id = 'agree-terms-checkbox'
    agree_terms_checkbox_element = driver.find_element_by_id(agree_terms_id)
    agree_terms_checkbox_element.submit()


def create_database(
    driver: WebDriver,
    database_name: str,
    license_name: str,
) -> None:  # pragma: no cover
    """
    Create a database.
    """
    target_manager_url = 'https://developer.vuforia.com/vui/develop/databases'
    driver.get(target_manager_url)
    ten_second_wait = WebDriverWait(driver, 10)

    add_database_button_element = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, 'add-dialog-btn'),
        ),
    )
    time.sleep(1)
    add_database_button_element.click()

    database_name_element = driver.find_element_by_id('database-name')
    database_name_element.send_keys(database_name)

    cloud_type_radio_element = driver.find_element_by_id('cloud-radio-btn')
    cloud_type_radio_element.click()

    license_dropdown_element = driver.find_element_by_id(
        'cloud-license-dropdown',
    )
    time.sleep(1)
    license_name_no_underscores = license_name.replace('_', '-')
    license_dropdown_id = 'cloud-license-' + license_name_no_underscores
    dropdown_choice_element = license_dropdown_element.find_element_by_id(
        license_dropdown_id,
    )
    dropdown_choice_element.click()

    create_button = driver.find_element_by_id('create-btn')
    create_button.click()


def get_database_details(
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:  # pragma: no cover
    """
    Get details of a database.
    """
    target_manager_url = 'https://developer.vuforia.com/vui/develop/databases'
    driver.get(target_manager_url)
    database_name_xpath = "//span[text()='" + database_name + "']"
    ten_second_wait = WebDriverWait(driver, 10)

    database_cell_element = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.XPATH, database_name_xpath),
        ),
    )
    database_cell_element.click()

    access_keys_tab_item = ten_second_wait.until(
        expected_conditions.presence_of_element_located(
            (By.LINK_TEXT, 'Database Access Keys'),
        ),
    )

    access_keys_tab_item.click()

    # Without this we sometimes get empty strings for the keys.
    time.sleep(1)

    client_access_key = driver.find_element_by_class_name(
        'client-access-key',
    ).text
    client_secret_key = driver.find_element_by_class_name(
        'client-secret-key',
    ).text
    server_access_key = driver.find_element_by_class_name(
        'server-access-key',
    ).text
    server_secret_key = driver.find_element_by_class_name(
        'server-secret-key',
    ).text

    return {
        'database_name': database_name,
        'server_access_key': str(server_access_key),
        'server_secret_key': str(server_secret_key),
        'client_access_key': str(client_access_key),
        'client_secret_key': str(client_secret_key),
    }


@click.group(name='vws-web')
def vws_web_tools_group() -> None:
    """
    Commands for interacting with VWS.
    """


@click.command()
@click.option('--license-name', required=True)
@click.option('--email-address', envvar='VWS_EMAIL_ADDRESS', required=True)
@click.option('--password', envvar='VWS_PASSWORD', required=True)
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
    create_license(driver=driver, license_name=license_name)
    driver.close()


@click.command()
@click.option('--license-name', required=True)
@click.option('--database-name', required=True)
@click.option('--email-address', envvar='VWS_EMAIL_ADDRESS', required=True)
@click.option('--password', envvar='VWS_PASSWORD', required=True)
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
    create_database(
        driver=driver,
        database_name=database_name,
        license_name=license_name,
    )
    driver.close()


@click.command()
@click.option('--database-name', required=True)
@click.option('--email-address', envvar='VWS_EMAIL_ADDRESS', required=True)
@click.option('--password', envvar='VWS_PASSWORD', required=True)
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
    details = get_database_details(driver=driver, database_name=database_name)
    driver.close()
    click.echo(yaml.dump(details), nl=False)


vws_web_tools_group.add_command(create_vws_database)
vws_web_tools_group.add_command(create_vws_license)
vws_web_tools_group.add_command(show_database_details)
