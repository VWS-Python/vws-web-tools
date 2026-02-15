"""Tools for interacting with the VWS (Vuforia Web Services) website."""

import contextlib
import time
from typing import TypedDict

import click
import yaml
from beartype import beartype
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait


@beartype
class DatabaseDict(TypedDict):
    """A dictionary type which represents a database."""

    database_name: str
    server_access_key: str
    server_secret_key: str
    client_access_key: str
    client_secret_key: str


@beartype
def log_in(
    driver: WebDriver,
    email_address: str,
    password: str,
) -> None:
    """Log in to Vuforia web services."""
    log_in_url = "https://developer.vuforia.com/auth/login"
    driver.get(url=log_in_url)
    thirty_second_wait = WebDriverWait(driver=driver, timeout=30)
    email_address_input_element = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "login_email"),
        ),
    )
    email_address_input_element.send_keys(email_address)

    password_input_element = driver.find_element(
        by=By.ID,
        value="login_password",
    )
    password_input_element.send_keys(password)

    _dismiss_cookie_banner(driver=driver)
    login_button = driver.find_element(by=By.ID, value="login")
    login_button.click()


@beartype
def _dismiss_cookie_banner(
    driver: WebDriver,
) -> None:
    """Dismiss the OneTrust cookie consent banner if present."""
    driver.execute_script(  # pyright: ignore[reportUnknownMemberType]
        """
        // Remove any existing banner immediately
        var banner = document.getElementById('onetrust-banner-sdk');
        if (banner) banner.remove();
        var consent = document.getElementById('onetrust-consent-sdk');
        if (consent) consent.remove();

        // Set up observer to remove banner if it appears later
        if (!window.__otObserver) {
            window.__otObserver = new MutationObserver(function() {
                var b = document.getElementById('onetrust-banner-sdk');
                if (b) b.remove();
                var c = document.getElementById('onetrust-consent-sdk');
                if (c) c.remove();
            });
            window.__otObserver.observe(
                document.documentElement,
                {childList: true, subtree: true}
            );
        }
        """
    )


@beartype
def wait_for_logged_in(driver: WebDriver) -> None:
    """Wait for the user to be logged in.

    Without this, we sometimes get a redirect to a post-login page.
    """
    thirty_second_wait = WebDriverWait(driver=driver, timeout=30)
    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.CLASS_NAME, "userNameInHeaderSpan"),
        ),
    )
    _dismiss_cookie_banner(driver=driver)


@beartype
def create_license(
    driver: WebDriver,
    license_name: str,
) -> None:
    """Create a license."""
    new_license_url = "https://developer.vuforia.com/develop/licenses/free/new"
    driver.get(url=new_license_url)
    _dismiss_cookie_banner(driver=driver)

    thirty_second_wait = WebDriverWait(driver=driver, timeout=30)

    license_name_input_element = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "license-name"),
        ),
    )

    license_name_input_element.send_keys(license_name)

    agree_terms_checkbox_element = driver.find_element(
        by=By.ID,
        value="agree-terms-checkbox",
    )
    agree_terms_checkbox_element.click()

    confirm_button = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "confirm"),
        ),
    )
    confirm_button.click()
    time.sleep(5)


@beartype
def create_database(
    driver: WebDriver,
    database_name: str,
    license_name: str,
) -> None:
    """Create a database."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)
    thirty_second_wait = WebDriverWait(driver=driver, timeout=30)

    add_database_button_id = "add-dialog-btn"
    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, add_database_button_id),
        ),
    )

    thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, add_database_button_id),
        ),
    )

    add_database_button_element = driver.find_element(
        by=By.ID,
        value=add_database_button_id,
    )
    add_database_button_element.click()
    with contextlib.suppress(WebDriverException):
        add_database_button_element.click()
    database_name_id = "database-name"
    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, database_name_id),
        ),
    )

    database_name_element = driver.find_element(
        by=By.ID,
        value=database_name_id,
    )
    database_name_element.send_keys(database_name)

    cloud_type_radio_element = driver.find_element(
        by=By.ID,
        value="cloud-radio-btn",
    )
    cloud_type_radio_element.click()

    license_dropdown_element = Select(
        webelement=driver.find_element(
            by=By.ID,
            value="cloud-license-dropdown",
        ),
    )

    # Sleeping 1 second here did not work, so we sleep 5 seconds.
    time.sleep(5)
    license_dropdown_element.select_by_visible_text(
        text=license_name,
    )

    generate_button = driver.find_element(
        by=By.ID,
        value="generate-btn",
    )
    generate_button.click()
    # Without this we might close the driver before the database
    # is created.
    time.sleep(5)


@beartype
def get_database_details(
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:
    """Get details of a database."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)
    thirty_second_wait = WebDriverWait(driver=driver, timeout=30)

    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "table_search"),
        ),
    )

    search_input_element = driver.find_element(
        by=By.ID,
        value="table_search",
    )
    thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_project_name"),
        ),
    )
    search_input_element.send_keys(database_name)
    # Wait for the search results to update.
    time.sleep(2)

    database_cell_element = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_project_name"),
        ),
    )

    database_cell_element.click()

    access_keys_tab_item = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.LINK_TEXT, "Database Access Keys"),
        ),
    )

    access_keys_tab_item.click()

    # Without this we sometimes get empty strings for the keys.
    time.sleep(1)

    client_key_div = driver.find_element(
        by=By.ID,
        value="client-access-key",
    )
    client_grey_boxes = client_key_div.find_elements(
        by=By.CLASS_NAME,
        value="grey-box",
    )
    client_access_key = client_grey_boxes[0].text.strip()
    client_secret_key = client_grey_boxes[1].text.strip()

    server_key_div = driver.find_element(
        by=By.ID,
        value="server-access-key",
    )
    server_grey_boxes = server_key_div.find_elements(
        by=By.CLASS_NAME,
        value="grey-box",
    )
    server_access_key = server_grey_boxes[0].text.strip()
    server_secret_key = server_grey_boxes[1].text.strip()

    return {
        "database_name": database_name,
        "server_access_key": server_access_key,
        "server_secret_key": server_secret_key,
        "client_access_key": client_access_key,
        "client_secret_key": client_secret_key,
    }


@click.group(name="vws-web")
@beartype
def vws_web_tools_group() -> None:
    """Commands for interacting with VWS."""


@click.command()
@click.option("--license-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def create_vws_license(  # pragma: no cover
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a license."""
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
@beartype
def create_vws_database(  # pragma: no cover
    database_name: str,
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a database."""
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
@click.option("--env-var-format", is_flag=True)
@beartype
def show_database_details(  # pragma: no cover
    database_name: str,
    email_address: str,
    password: str,
    *,
    env_var_format: bool,
) -> None:
    """Show the details of a database."""
    driver = webdriver.Safari()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    details = get_database_details(
        driver=driver,
        database_name=database_name,
    )
    driver.close()
    if env_var_format:
        env_var_format_details = {
            "VUFORIA_TARGET_MANAGER_DATABASE_NAME": details["database_name"],
            "VUFORIA_SERVER_ACCESS_KEY": details["server_access_key"],
            "VUFORIA_SERVER_SECRET_KEY": details["server_secret_key"],
            "VUFORIA_CLIENT_ACCESS_KEY": details["client_access_key"],
            "VUFORIA_CLIENT_SECRET_KEY": details["client_secret_key"],
        }

        for key, value in env_var_format_details.items():
            click.echo(message=f"{key}={value}")
    else:
        click.echo(message=yaml.dump(data=details), nl=False)


vws_web_tools_group.add_command(cmd=create_vws_database)
vws_web_tools_group.add_command(cmd=create_vws_license)
vws_web_tools_group.add_command(cmd=show_database_details)
