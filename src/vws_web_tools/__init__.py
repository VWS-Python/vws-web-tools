"""
Tools for interacting with the VWS (Vuforia Web Services) website.
"""

import click
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


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


@click.group(name='vws-web')
def vws_web_tools_group() -> None:
    """
    Commands for interacting with VWS.
    """


@click.command()
@click.option('--license-name')
@click.option('--email-address', envvar='VWS_EMAIL_ADDRESS')
@click.option('--password', envvar='VWS_PASSWORD')
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


vws_web_tools_group.add_command(create_vws_license)
