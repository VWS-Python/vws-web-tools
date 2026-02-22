"""Tools for interacting with the VWS (Vuforia Web Services) website."""

import contextlib
import logging
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import click
import yaml
from beartype import beartype
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from tenacity import retry, retry_if_exception_type, stop_after_attempt

LOGGER = logging.getLogger(name=__name__)

_TIMEOUT_RETRY_DECORATOR = retry(
    retry=retry_if_exception_type(
        exception_types=TimeoutException,
    ),
    stop=stop_after_attempt(max_attempt_number=3),
)


@beartype
def create_chrome_driver() -> WebDriver:
    """Create a headless Chrome WebDriver."""
    options = ChromeOptions()
    options.add_argument(argument="--headless=new")
    options.add_argument(argument="--no-sandbox")
    options.add_argument(argument="--disable-dev-shm-usage")
    # Use a large window so that pagination controls are visible
    # and clickable without scrolling.
    options.add_argument(argument="--window-size=1920,1080")
    return ChromeDriver(options=options)


@beartype
class DatabaseDict(TypedDict):
    """A dictionary type which represents a database."""

    database_name: str
    server_access_key: str
    server_secret_key: str
    client_access_key: str
    client_secret_key: str


@beartype
class VuMarkDatabaseDict(TypedDict):
    """A dictionary type which represents a VuMark database.

    VuMark databases only have server access keys.
    """

    database_name: str
    server_access_key: str
    server_secret_key: str


@beartype
def _log_in_once(
    *,
    driver: WebDriver,
    email_address: str,
    password: str,
) -> None:
    """Submit the login form once."""
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
    *,
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
def wait_for_logged_in(*, driver: WebDriver) -> None:
    """Wait for the user to be logged in.

    Without this, we sometimes get a redirect to a post-login page.
    """
    sixty_second_wait = WebDriverWait(
        driver=driver,
        timeout=60,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )
    sixty_second_wait.until(
        method=lambda d: (
            "/auth/login" not in d.current_url
            and d.execute_script(  # pyright: ignore[reportUnknownMemberType]
                "return document.readyState",
            )
            == "complete"
        ),
    )
    _dismiss_cookie_banner(driver=driver)


@_TIMEOUT_RETRY_DECORATOR
@beartype
def log_in(
    *,
    driver: WebDriver,
    email_address: str,
    password: str,
) -> None:
    """Log in to Vuforia web services, retrying on timeout."""
    _log_in_once(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)


@beartype
def create_license(
    *,
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
    thirty_second_wait.until(
        method=expected_conditions.url_changes(url=new_license_url),
    )


@_TIMEOUT_RETRY_DECORATOR
@beartype
def delete_license(
    *,
    driver: WebDriver,
    license_name: str,
) -> None:
    """Delete a license."""
    licenses_url = "https://developer.vuforia.com/develop/licenses"
    driver.get(url=licenses_url)
    _dismiss_cookie_banner(driver=driver)

    thirty_second_wait = WebDriverWait(
        driver=driver,
        timeout=30,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "table_search"),
        ),
    )
    thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_app_name"),
        ),
    )

    search_input_element = driver.find_element(
        by=By.ID,
        value="table_search",
    )
    search_input_element.clear()
    search_input_element.send_keys(license_name)
    search_input_element.send_keys(Keys.ENTER)

    @beartype
    def _click_license_row(
        *,
        driver: WebDriver,
    ) -> bool:
        """Find and click the row matching license_name."""
        rows = driver.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                " and contains(@id, '_app_name')]"
            ),
        )
        for row in rows:
            if row.text.strip() == license_name:
                row.click()
                return True
        return False

    thirty_second_wait.until(
        method=lambda d: _click_license_row(driver=d),
    )

    thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "license-header-name"),
        ),
    )
    _dismiss_cookie_banner(driver=driver)

    delete_link = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.LINK_TEXT, "Delete License Key"),
        ),
    )
    delete_link.click()

    confirm_button = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "delete"),
        ),
    )
    confirm_button.click()
    thirty_second_wait.until(
        method=expected_conditions.staleness_of(element=confirm_button),
    )


@_TIMEOUT_RETRY_DECORATOR
@beartype
def _open_add_database_dialog(
    *,
    driver: WebDriver,
    database_name: str,
) -> WebDriverWait[WebDriver]:
    """Navigate to databases page, open the add-database dialog, and enter
    the name.

    Returns a ``WebDriverWait`` for further use.
    """
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)

    thirty_second_wait = WebDriverWait(
        driver=driver,
        timeout=30,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

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
    return thirty_second_wait


@beartype
def _submit_add_database_dialog(
    *,
    driver: WebDriver,
    wait: WebDriverWait[WebDriver],
) -> None:
    """Click the generate button and wait for the dialog to close."""
    generate_button = driver.find_element(
        by=By.ID,
        value="generate-btn",
    )
    generate_button.click()
    wait.until(
        method=expected_conditions.staleness_of(element=generate_button),
    )


@beartype
def create_cloud_database(
    *,
    driver: WebDriver,
    database_name: str,
    license_name: str,
) -> None:
    """Create a cloud database."""
    wait = _open_add_database_dialog(
        driver=driver,
        database_name=database_name,
    )

    database_type_radio_element = driver.find_element(
        by=By.ID,
        value="cloud-radio-btn",
    )
    database_type_radio_element.click()

    wait.until(
        method=lambda d: any(
            opt.text == license_name
            for opt in Select(
                webelement=d.find_element(
                    by=By.ID,
                    value="cloud-license-dropdown",
                ),
            ).options
        ),
    )
    Select(
        webelement=driver.find_element(
            by=By.ID,
            value="cloud-license-dropdown",
        ),
    ).select_by_visible_text(
        text=license_name,
    )

    _submit_add_database_dialog(driver=driver, wait=wait)


@beartype
def create_vumark_database(
    *,
    driver: WebDriver,
    database_name: str,
) -> None:
    """Create a VuMark database."""
    wait = _open_add_database_dialog(
        driver=driver,
        database_name=database_name,
    )

    database_type_radio_element = driver.find_element(
        by=By.ID,
        value="vumark-radio-btn",
    )
    database_type_radio_element.click()

    _submit_add_database_dialog(driver=driver, wait=wait)


@beartype
def upload_vumark_template(
    *,
    driver: WebDriver,
    database_name: str,
    svg_file_path: Path,
    template_name: str,
    width: float,
) -> None:
    """Upload a VuMark SVG template to a VuMark database."""
    navigate_to_database(driver=driver, database_name=database_name)

    thirty_second_wait = WebDriverWait(
        driver=driver,
        timeout=30,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    add_target_button = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "add-dialog-btn"),
        ),
    )
    add_target_button.click()

    # Upload the SVG file via the file input element.
    file_input = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.CSS_SELECTOR, "input[type='file']"),
        ),
    )
    file_input.send_keys(f"{svg_file_path.resolve()}")

    width_input = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.CSS_SELECTOR, "input[placeholder='Width']"),
        ),
    )
    width_input.clear()
    width_input.send_keys(f"{width}")

    name_input = driver.find_element(
        by=By.CSS_SELECTOR,
        value="input[placeholder='Name']",
    )
    name_input.clear()
    name_input.send_keys(template_name)

    add_button = thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "add"),
        ),
    )
    add_button.click()

    # Wait for the uploaded template to appear in the targets table.
    # The add button can remain attached to the DOM after submission,
    # so waiting for staleness here is flaky.
    target_name_xpath_literal = _xpath_literal(value=template_name)
    target_name_cell_predicate = (
        "starts-with(@id, 'table_row_')"
        " and substring("
        "@id,"
        " string-length(@id) - string-length('_target_name') + 1"
        " ) = '_target_name'"
        f" and normalize-space(.) = {target_name_xpath_literal}"
    )
    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )
    long_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.XPATH, f"//*[{target_name_cell_predicate}]"),
        ),
    )


@beartype
def _xpath_literal(
    *,
    value: str,
) -> str:
    """Return an XPath string literal."""
    return f"'{value}'"


@beartype
def _find_vumark_target_link(
    *,
    driver: WebDriver,
    target_name: str,
) -> str:
    """Find and return a target-name link."""
    target_name_xpath_literal = _xpath_literal(value=target_name)
    target_row_predicate = (
        "starts-with(@id, 'table_row_')"
        " and substring("
        "@id,"
        " string-length(@id) - string-length('_target_name') + 1"
        " ) = '_target_name'"
        f" and normalize-space(.) = {target_name_xpath_literal}"
    )
    target_link_elements = driver.find_elements(
        by=By.XPATH,
        value=f"//a[{target_row_predicate}]",
    )
    LOGGER.debug(
        "Found %d matching target-name links while searching for '%s'.",
        len(target_link_elements),
        target_name,
    )
    target_link_element = target_link_elements[0]
    target_link = target_link_element.get_attribute(  # pyright: ignore[reportUnknownMemberType]
        name="href",
    )
    LOGGER.debug(
        "Found VuMark target link '%s' for '%s'.",
        target_link,
        target_name,
    )
    return str(object=target_link)


@_TIMEOUT_RETRY_DECORATOR
@beartype
def wait_for_vumark_target_link(
    *,
    driver: WebDriver,
    database_name: str,
    target_name: str,
    timeout: int = 180,
) -> None:
    """Wait for a VuMark target row to be rendered on the target-key
    tab.

    This waits until the matching target row is rendered as a clickable
    link.
    """
    navigate_to_database(driver=driver, database_name=database_name)
    long_wait = WebDriverWait(
        driver=driver,
        timeout=timeout,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    def _click_target_key_tab(d: WebDriver) -> bool:
        """Click the target-key tab once it is clickable."""
        target_key_tab = d.find_element(by=By.ID, value="target-key-tab")
        target_key_tab.click()
        return True

    long_wait.until(
        method=_click_target_key_tab,
    )

    target_name_xpath_literal = _xpath_literal(value=target_name)
    target_row_predicate = (
        "starts-with(@id, 'table_row_')"
        " and substring("
        "@id,"
        " string-length(@id) - string-length('_target_name') + 1"
        " ) = '_target_name'"
        f" and normalize-space(.) = {target_name_xpath_literal}"
    )

    def _target_link_found(d: WebDriver) -> bool:
        """Return whether the target row is visible as a link."""
        return bool(
            d.find_elements(
                by=By.XPATH,
                value=f"//a[{target_row_predicate}]",
            ),
        )

    long_wait.until(
        method=_target_link_found,
    )


@beartype
def get_vumark_target_id(
    *,
    driver: WebDriver,
    database_name: str,
    target_name: str,
) -> str:
    """Get the ID for a VuMark target in a database.

    Limitation:
        This navigates to the requested database but does not wait for
        readiness. It hard-errors if the target name is not yet rendered
        as a clickable link. While a target is still processing, VWS
        often renders plain text in that column and no target ID link is
        available.
    """
    LOGGER.debug(
        "Getting VuMark target ID for database '%s' and target '%s'.",
        database_name,
        target_name,
    )
    navigate_to_database(
        driver=driver,
        database_name=database_name,
    )
    short_wait = WebDriverWait(
        driver=driver,
        timeout=30,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    def _click_target_key_tab(d: WebDriver) -> bool:
        """Click the target-key tab once it is clickable."""
        target_key_tab = d.find_element(by=By.ID, value="target-key-tab")
        target_key_tab.click()
        return True

    short_wait.until(
        method=_click_target_key_tab,
    )
    short_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "table_search"),
        ),
    )
    target_name_xpath_literal = _xpath_literal(value=target_name)
    target_row_predicate = (
        "starts-with(@id, 'table_row_')"
        " and substring("
        "@id,"
        " string-length(@id) - string-length('_target_name') + 1"
        " ) = '_target_name'"
        f" and normalize-space(.) = {target_name_xpath_literal}"
    )
    short_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.XPATH, f"//*[{target_row_predicate}]"),
        ),
    )

    target_link = _find_vumark_target_link(
        driver=driver,
        target_name=target_name,
    )

    url_path = urlparse(url=target_link).path
    return url_path.rstrip("/").split(sep="/")[-1]


@beartype
def navigate_to_database(
    *,
    driver: WebDriver,
    database_name: str,
) -> None:
    """Navigate to a database's page in the target manager."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)

    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    # The table search field needs ENTER to trigger filtering
    # in our Selenium runs.
    long_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.ID, "table_search"),
        ),
    )
    long_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_project_name"),
        ),
    )
    search_input_element = driver.find_element(
        by=By.ID,
        value="table_search",
    )
    search_input_element.clear()
    search_input_element.send_keys(database_name)
    search_input_element.send_keys(Keys.ENTER)

    @beartype
    def _click_database_row(
        *,
        driver: WebDriver,
    ) -> bool:
        """Find and click the row matching database_name."""
        rows = driver.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                " and contains(@id, '_project_name')]"
            ),
        )
        for row in rows:
            if row.text.strip() == database_name:
                row.click()
                return True
        return False

    long_wait.until(method=lambda d: _click_database_row(driver=d))


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_database_details(
    *,
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:
    """Get details of a database."""
    navigate_to_database(driver=driver, database_name=database_name)
    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    access_keys_tab_item = long_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.LINK_TEXT, "Database Access Keys"),
        ),
    )

    access_keys_tab_item.click()

    expected_key_boxes = 2

    long_wait.until(
        method=lambda d: all(
            len(
                boxes := d.find_element(
                    by=By.ID,
                    value=key_id,
                ).find_elements(by=By.CLASS_NAME, value="grey-box"),
            )
            >= expected_key_boxes
            and all(box.text.strip() for box in boxes[:expected_key_boxes])
            for key_id in ("client-access-key", "server-access-key")
        ),
    )

    client_grey_boxes = driver.find_element(
        by=By.ID,
        value="client-access-key",
    ).find_elements(by=By.CLASS_NAME, value="grey-box")
    client_access_key = client_grey_boxes[0].text.strip()
    client_secret_key = client_grey_boxes[1].text.strip()

    server_grey_boxes = driver.find_element(
        by=By.ID,
        value="server-access-key",
    ).find_elements(by=By.CLASS_NAME, value="grey-box")
    server_access_key = server_grey_boxes[0].text.strip()
    server_secret_key = server_grey_boxes[1].text.strip()

    return {
        "database_name": database_name,
        "server_access_key": server_access_key,
        "server_secret_key": server_secret_key,
        "client_access_key": client_access_key,
        "client_secret_key": client_secret_key,
    }


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_vumark_database_details(
    *,
    driver: WebDriver,
    database_name: str,
) -> VuMarkDatabaseDict:
    """Get details of a VuMark database.

    VuMark databases only have server access keys.
    """
    navigate_to_database(driver=driver, database_name=database_name)
    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    access_keys_tab_item = long_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.LINK_TEXT, "Database Access Keys"),
        ),
    )

    access_keys_tab_item.click()

    expected_key_boxes = 2

    long_wait.until(
        method=lambda d: (
            len(
                boxes := d.find_element(
                    by=By.ID,
                    value="server-access-key",
                ).find_elements(by=By.CLASS_NAME, value="grey-box"),
            )
            >= expected_key_boxes
            and all(box.text.strip() for box in boxes[:expected_key_boxes])
        ),
    )

    server_grey_boxes = driver.find_element(
        by=By.ID,
        value="server-access-key",
    ).find_elements(by=By.CLASS_NAME, value="grey-box")
    server_access_key = server_grey_boxes[0].text.strip()
    server_secret_key = server_grey_boxes[1].text.strip()

    return {
        "database_name": database_name,
        "server_access_key": server_access_key,
        "server_secret_key": server_secret_key,
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
def create_vws_license(
    *,
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a license."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        create_license(driver=driver, license_name=license_name)
    finally:
        driver.quit()


@click.command()
@click.option("--license-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def delete_vws_license(
    *,
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Delete a license."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        delete_license(driver=driver, license_name=license_name)
    finally:
        driver.quit()


@click.command()
@click.option("--license-name", required=True)
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def create_vws_cloud_database(
    *,
    database_name: str,
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a cloud database."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        create_cloud_database(
            driver=driver,
            database_name=database_name,
            license_name=license_name,
        )
    finally:
        driver.quit()


@click.command()
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def create_vws_vumark_database(
    *,
    database_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a VuMark database."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        create_vumark_database(
            driver=driver,
            database_name=database_name,
        )
    finally:
        driver.quit()


@click.command(name="upload-vumark-template")
@click.option("--database-name", required=True)
@click.option(
    "--svg-file-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--template-name", required=True)
@click.option("--width", type=float, required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def upload_vumark_template_to_database(  # noqa: PLR0913
    *,
    database_name: str,
    svg_file_path: Path,
    template_name: str,
    width: float,
    email_address: str,
    password: str,
) -> None:
    """Upload a VuMark SVG template to a VuMark database."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        upload_vumark_template(
            driver=driver,
            database_name=database_name,
            svg_file_path=svg_file_path,
            template_name=template_name,
            width=width,
        )
    finally:
        driver.quit()


@click.command(name="get-vumark-instance-id")
@click.option("--database-name", required=True)
@click.option("--target-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def get_vumark_instance_id(
    *,
    database_name: str,
    target_name: str,
    email_address: str,
    password: str,
) -> None:
    """Get the VuMark instance ID for a target."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        instance_id = get_vumark_target_id(
            driver=driver,
            database_name=database_name,
            target_name=target_name,
        )
    finally:
        driver.quit()
    click.echo(message=instance_id)


@click.command(name="wait-for-vumark-instance-id")
@click.option("--database-name", required=True)
@click.option("--target-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@click.option("--timeout", type=int, default=180, show_default=True)
@beartype
def wait_for_vumark_instance_id(
    *,
    database_name: str,
    target_name: str,
    email_address: str,
    password: str,
    timeout: int,
) -> None:
    """Wait for and get the VuMark instance ID for a target."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        wait_for_vumark_target_link(
            driver=driver,
            database_name=database_name,
            target_name=target_name,
            timeout=timeout,
        )
        instance_id = get_vumark_target_id(
            driver=driver,
            database_name=database_name,
            target_name=target_name,
        )
    finally:
        driver.quit()
    click.echo(message=instance_id)


@click.command()
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@click.option("--env-var-format", is_flag=True)
@beartype
def show_database_details(
    *,
    database_name: str,
    email_address: str,
    password: str,
    env_var_format: bool,
) -> None:
    """Show the details of a database."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        details = get_database_details(
            driver=driver,
            database_name=database_name,
        )
    finally:
        driver.quit()
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


@click.command()
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@click.option("--env-var-format", is_flag=True)
@beartype
def show_vumark_database_details(
    *,
    database_name: str,
    email_address: str,
    password: str,
    env_var_format: bool,
) -> None:
    """Show the details of a VuMark database."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        details = get_vumark_database_details(
            driver=driver,
            database_name=database_name,
        )
    finally:
        driver.quit()
    if env_var_format:
        env_var_format_details = {
            "VUFORIA_TARGET_MANAGER_DATABASE_NAME": details["database_name"],
            "VUFORIA_SERVER_ACCESS_KEY": details["server_access_key"],
            "VUFORIA_SERVER_SECRET_KEY": details["server_secret_key"],
        }

        for key, value in env_var_format_details.items():
            click.echo(message=f"{key}={value}")
    else:
        click.echo(message=yaml.dump(data=details), nl=False)


vws_web_tools_group.add_command(cmd=create_vws_cloud_database)
vws_web_tools_group.add_command(cmd=create_vws_license)
vws_web_tools_group.add_command(cmd=create_vws_vumark_database)
vws_web_tools_group.add_command(cmd=delete_vws_license)
vws_web_tools_group.add_command(cmd=get_vumark_instance_id)
vws_web_tools_group.add_command(cmd=show_database_details)
vws_web_tools_group.add_command(cmd=show_vumark_database_details)
vws_web_tools_group.add_command(cmd=upload_vumark_template_to_database)
vws_web_tools_group.add_command(cmd=wait_for_vumark_instance_id)
