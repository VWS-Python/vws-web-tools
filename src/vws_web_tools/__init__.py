"""Tools for interacting with the VWS (Vuforia Web Services) website."""

import contextlib
import datetime
import logging
import re
import shlex
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, TypeGuard
from urllib.parse import quote, urlparse

import click
import requests
import yaml
from beartype import beartype
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

LOGGER = logging.getLogger(name=__name__)

# A CAD model to use with the Model Target Web API.
#
# This is pinned to a commit rather than to a branch so that the file
# does not change under us. A pinned URL can still stop resolving - if
# the repository is renamed, deleted or rewritten - so callers can pass
# their own URL to ``get_model_target_web_api_details``.
MODEL_TARGET_WEB_API_CAD_DATA_URL = (
    "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/"
    "d7a3cc8e51d7c573771ae77a57f16b0662a905c6/"
    "2.0/Duck/glTF-Binary/Duck.glb"
)
MODEL_TARGET_WEB_API_STANDARD_SCOPE = "modeltargets.standardmodeltarget.all"
MODEL_TARGET_WEB_API_ADVANCED_SCOPE = "modeltargets.advancedmodeltarget.all"
MODEL_TARGET_WEB_API_STANDARD_SCOPES: tuple[str, ...] = (
    MODEL_TARGET_WEB_API_STANDARD_SCOPE,
)
MODEL_TARGET_WEB_API_ADVANCED_SCOPES: tuple[str, ...] = (
    MODEL_TARGET_WEB_API_STANDARD_SCOPE,
    MODEL_TARGET_WEB_API_ADVANCED_SCOPE,
)
_OAUTH2_CLIENT_CREDENTIALS_SCOPE = "oauth2.clientcredentials.all"
_REQUEST_TIMEOUT_SECONDS = 30
_DATABASE_PAGE_URL_PATH_PATTERN = re.compile(
    pattern=r"^/develop/databases/(?P<database_id>[^/]+)/",
)
_TARGET_ID_PATTERN = re.compile(pattern=r"[0-9a-zA-Z]{32}")

# Locators for the controls in the target manager's dialog for adding a
# VuMark target. The dialog gives these inputs no id and no name, so
# there is nothing steadier to match on than their type and their
# placeholder text - which means a wording change in the target manager
# breaks uploads. Keeping them here at least puts every locator that has
# to be revisited when that happens in one place.
_VUMARK_TEMPLATE_FILE_LOCATOR = (By.CSS_SELECTOR, "input[type='file']")
_VUMARK_TEMPLATE_WIDTH_LOCATOR = (
    By.CSS_SELECTOR,
    "input[placeholder='Width']",
)
_VUMARK_TEMPLATE_NAME_LOCATOR = (By.CSS_SELECTOR, "input[placeholder='Name']")

_TIMEOUT_RETRY_DECORATOR = retry(
    retry=retry_if_exception_type(
        exception_types=TimeoutException,
    ),
    stop=stop_after_attempt(max_attempt_number=5),
    wait=wait_fixed(wait=5),
)


@beartype
def create_chrome_driver() -> WebDriver:
    """Create a headless Chrome WebDriver."""
    options = ChromeOptions()
    # Return from ``driver.get`` once the DOM is ready, without waiting
    # for sub-resources. Every element this package looks for is behind
    # an explicit wait, and ``wait_for_logged_in`` asks for
    # ``document.readyState`` where a full load is what matters, so
    # waiting for images and analytics scripts to load only adds time
    # and turns slow third-party requests into timeouts.
    options.page_load_strategy = "eager"  # noqa: V101
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
    database_id: str
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
class LicenseDict(TypedDict):
    """A dictionary type which represents a license."""

    license_name: str
    license_key: str


@beartype
class ModelTargetWebAPIDict(TypedDict):
    """A dictionary type which represents Model Target Web API details."""

    client_id: str
    client_secret: str
    cad_data_url: str


@beartype
@dataclass(frozen=True, kw_only=True)
class _ModelTargetWebAPIClientCredentials:
    """Model Target Web API client credentials."""

    client_id: str
    client_secret: str


@beartype
@dataclass(frozen=True, kw_only=True)
class _ModelTargetWebAPICredentialsAPISession:
    """Authenticated session for the credentials management API."""

    session: requests.Session
    access_token: str


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

        // Set up observer to remove banner if it appears later.
        // Disconnect any observer this function set up earlier on this
        // document first, so that only one is ever running.
        if (window.__otObserver) window.__otObserver.disconnect();
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


@_TIMEOUT_RETRY_DECORATOR
@beartype
def create_license(
    *,
    driver: WebDriver,
    license_name: str,
) -> None:
    """Create a license."""
    new_license_url = "https://developer.vuforia.com/develop/licenses/free/new"
    driver.get(url=new_license_url)
    wait_for_logged_in(driver=driver)
    _dismiss_cookie_banner(driver=driver)

    sixty_second_wait = WebDriverWait(
        driver=driver,
        timeout=60,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    try:
        license_name_input_element = sixty_second_wait.until(
            method=expected_conditions.element_to_be_clickable(
                mark=(By.ID, "license-name"),
            ),
        )
    except TimeoutException:  # pragma: no cover
        licenses_url = "https://developer.vuforia.com/develop/licenses"
        driver.get(url=licenses_url)
        wait_for_logged_in(driver=driver)
        _dismiss_cookie_banner(driver=driver)

        generate_basic_license_link = sixty_second_wait.until(
            method=expected_conditions.element_to_be_clickable(
                mark=(By.ID, "generate-basic-license-link"),
            ),
        )
        generate_basic_license_link.click()
        license_name_input_element = sixty_second_wait.until(
            method=expected_conditions.element_to_be_clickable(
                mark=(By.ID, "license-name"),
            ),
        )

    license_name_input_element.clear()
    license_name_input_element.send_keys(license_name)

    agree_terms_checkbox_element = sixty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "agree-terms-checkbox"),
        ),
    )
    agree_terms_checkbox_element.click()

    confirm_button = sixty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "confirm"),
        ),
    )
    confirm_button.click()
    sixty_second_wait.until(
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
    # This dismisses the cookie banner as well as waiting for the
    # licenses page, rather than for a redirect to the login page.
    wait_for_logged_in(driver=driver)

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
        """Find and click the row matching license_name.

        The search filter is applied asynchronously, so the table can
        still hold unfiltered rows when this first runs. Wait for every
        row shown to match the search text before clicking, rather than
        clicking a row which is about to be replaced.
        """
        rows = driver.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                " and contains(@id, '_app_name')]"
            ),
        )
        row_texts = [row.text.strip() for row in rows]
        if not row_texts or not all(
            license_name in row_text for row_text in row_texts
        ):
            return False
        if license_name not in row_texts:  # pragma: no cover
            # Every row contains the search text by now, but a row whose
            # text merely contains it is not the row we want.
            return False
        rows[row_texts.index(license_name)].click()
        return True

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
    # The dialog sometimes does not open on the first click. Click
    # again, ignoring the errors which mean that the first click did
    # open it: the button is then covered by the dialog, hidden, or
    # gone from the DOM.
    with contextlib.suppress(
        ElementClickInterceptedException,
        ElementNotInteractableException,
        StaleElementReferenceException,
    ):
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
    wait: WebDriverWait[WebDriver],
) -> None:
    """Click the generate button and wait for the dialog to close."""
    generate_button = wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "generate-btn"),
        ),
    )
    generate_button.click()
    wait.until(
        method=expected_conditions.staleness_of(element=generate_button),
    )


@_TIMEOUT_RETRY_DECORATOR
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

    @beartype
    def _matching_license_options(driver: WebDriver) -> list[WebElement]:
        """Return the drop-down options for the wanted license."""
        license_select = Select(
            webelement=driver.find_element(
                by=By.ID,
                value="cloud-license-dropdown",
            ),
        )
        return [
            option
            for option in license_select.options
            if option.text == license_name
        ]

    matching_options = wait.until(method=_matching_license_options)
    if len(matching_options) > 1:  # pragma: no cover
        message = (
            f"{len(matching_options)} licenses in the drop-down are named "
            f"'{license_name}'. Which one to attach the new database to "
            "is ambiguous."
        )
        raise ValueError(message)

    Select(
        webelement=driver.find_element(
            by=By.ID,
            value="cloud-license-dropdown",
        ),
    ).select_by_visible_text(
        text=license_name,
    )

    _submit_add_database_dialog(wait=wait)


@_TIMEOUT_RETRY_DECORATOR
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

    _submit_add_database_dialog(wait=wait)


@_TIMEOUT_RETRY_DECORATOR
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
            locator=_VUMARK_TEMPLATE_FILE_LOCATOR,
        ),
    )
    file_input.send_keys(f"{svg_file_path.resolve()}")

    width_input = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=_VUMARK_TEMPLATE_WIDTH_LOCATOR,
        ),
    )
    width_input.clear()
    width_input.send_keys(f"{width}")

    name_input = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=_VUMARK_TEMPLATE_NAME_LOCATOR,
        ),
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
    """Return an XPath string literal.

    XPath 1.0 string literals have no escape syntax, so a value which
    contains an apostrophe cannot be wrapped in apostrophes. Wrap such a
    value in quotation marks instead, and build a ``concat()``
    expression for a value which contains both.
    """
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'

    apostrophe_literal = '"\'"'
    segments: list[str] = []
    for index, part in enumerate(iterable=value.split(sep="'")):
        if index:
            segments.append(apostrophe_literal)
        if part:
            segments.append(f"'{part}'")
    joined_segments = ", ".join(segments)
    return f"concat({joined_segments})"


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
    if not target_link_elements:
        message = (
            f"No link was found for the target named '{target_name}'. "
            "The target manager renders a target's name as plain text "
            "rather than as a link while the target is still processing."
        )
        raise ValueError(message)
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


@beartype
def _open_target_key_tab(
    *,
    wait: WebDriverWait[WebDriver],
) -> None:
    """Click the target-key tab of a VuMark database.

    The tab is clicked exactly once. The wait is what makes the tab
    being slow to render survivable: it retries until the click goes
    through, and returns as soon as one has.
    """

    @beartype
    def _click_target_key_tab(driver: WebDriver) -> bool:
        """Click the target-key tab."""
        target_key_tab = driver.find_element(
            by=By.ID,
            value="target-key-tab",
        )
        target_key_tab.click()
        return True

    wait.until(method=_click_target_key_tab)


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

    _open_target_key_tab(wait=long_wait)

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


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_vumark_target_id(
    *,
    driver: WebDriver,
    database_name: str,
    target_name: str,
) -> str:
    """Get the ID for a VuMark target in a database.

    Limitation:
        While a target is still processing, VWS renders plain text in
        the target-name column rather than a link, and no target ID is
        available. This waits up to 30 seconds for the link, and then
        hard-errors. Use ``wait_for_vumark_target_link`` first to wait
        for longer than that.
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

    _open_target_key_tab(wait=short_wait)
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
    # Wait for a link rather than for any element which matches, as the
    # target manager renders the target's name as plain text until the
    # target has finished processing, and only a link carries the ID.
    short_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.XPATH, f"//a[{target_row_predicate}]"),
        ),
    )

    target_link = _find_vumark_target_link(
        driver=driver,
        target_name=target_name,
    )

    url_path = urlparse(url=target_link).path
    target_id = url_path.rstrip("/").split(sep="/")[-1]
    if not _TARGET_ID_PATTERN.fullmatch(string=target_id):  # pragma: no cover
        message = (
            f"Expected the last path segment of the target link "
            f"'{target_link}' to be a target ID, but it was "
            f"'{target_id}'."
        )
        raise ValueError(message)
    return target_id


@beartype
def navigate_to_database(
    *,
    driver: WebDriver,
    database_name: str,
) -> None:
    """Navigate to a database's page in the target manager."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    # This dismisses the cookie banner as well as waiting for the target
    # manager, rather than for a redirect to the login page.
    wait_for_logged_in(driver=driver)

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
        """Find and click the row matching database_name.

        The search filter is applied asynchronously, so the table can
        still hold unfiltered rows when this first runs. Wait for every
        row shown to match the search text before clicking, rather than
        clicking a row which is about to be replaced.
        """
        rows = driver.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                " and contains(@id, '_project_name')]"
            ),
        )
        row_texts = [row.text.strip() for row in rows]
        if not row_texts or not all(
            database_name in row_text for row_text in row_texts
        ):
            return False
        if database_name not in row_texts:  # pragma: no cover
            # Every row contains the search text by now, but a row whose
            # text merely contains it is not the row we want.
            return False
        rows[row_texts.index(database_name)].click()
        return True

    long_wait.until(method=lambda d: _click_database_row(driver=d))


@beartype
def _database_id_from_current_url(
    *,
    driver: WebDriver,
) -> str:
    """Get a database's ID from the URL of its page in the target manager.

    ``navigate_to_database`` lands on a URL with a path of the form
    ``/develop/databases/{database_id}/targets``, and the ID is not shown
    anywhere else on the page.
    """
    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    @beartype
    def _database_id_in_url(driver: WebDriver) -> str | None:
        """Get the database ID in the current URL.

        This returns ``None`` while the browser has not yet landed on a
        database's page, so that the wait keeps polling.
        """
        match = _DATABASE_PAGE_URL_PATH_PATTERN.match(
            string=urlparse(url=driver.current_url).path,
        )
        return None if match is None else match.group("database_id")

    database_id = long_wait.until(method=_database_id_in_url)
    if database_id is None:  # pragma: no cover
        # ``WebDriverWait.until`` never returns a false value, so this
        # is unreachable. It is here to narrow the type.
        message = "No database ID was found in the URL."
        raise ValueError(message)
    return database_id


@beartype
def navigate_to_license(
    *,
    driver: WebDriver,
    license_name: str,
) -> None:
    """Navigate to a license's page in the developer portal."""
    licenses_url = "https://developer.vuforia.com/develop/licenses"
    driver.get(url=licenses_url)
    # This dismisses the cookie banner as well as waiting for the
    # licenses page, rather than for a redirect to the login page.
    wait_for_logged_in(driver=driver)

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
            locator=(By.ID, "table_search"),
        ),
    )
    search_input_element = driver.find_element(
        by=By.ID,
        value="table_search",
    )
    search_input_element.clear()
    search_input_element.send_keys(license_name)
    search_input_element.send_keys(Keys.ENTER)

    license_name_xpath = _xpath_literal(value=license_name)

    @beartype
    def _click_license_row(
        *,
        driver: WebDriver,
    ) -> bool:
        """Find and click the row matching license_name."""
        element = driver.find_element(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                " and contains(@id, '_app_name')"
                f" and normalize-space(.)={license_name_xpath}]"
            ),
        )
        element.click()
        return True

    long_wait.until(method=lambda d: _click_license_row(driver=d))


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_license_details(
    *,
    driver: WebDriver,
    license_name: str,
) -> LicenseDict:
    """Get details of a license."""
    navigate_to_license(driver=driver, license_name=license_name)
    long_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    # Use the value the wait returned rather than reading the element
    # again: the wait only returns a non-empty key, but a second read
    # can land after a re-render and see an empty box.
    license_key = long_wait.until(
        method=lambda d: d.find_element(
            by=By.CLASS_NAME,
            value="license-key-box",
        ).text.strip(),
    )

    return {
        "license_name": license_name,
        "license_key": license_key,
    }


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_database_details(
    *,
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:
    """Get details of a database."""
    navigate_to_database(driver=driver, database_name=database_name)
    database_id = _database_id_from_current_url(driver=driver)
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
        "database_id": database_id,
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


@beartype
def _create_model_target_web_api_client_credentials(
    *,
    driver: WebDriver,
    credential_name: str,
    scopes: Sequence[str],
) -> _ModelTargetWebAPIClientCredentials:
    """Create OAuth2 client credentials for the Model Target Web API."""
    api_session = _model_target_web_api_credentials_api_session(
        driver=driver,
    )

    credentials_response = _json_request(
        session=api_session.session,
        method="POST",
        url="https://vws.vuforia.com/oauth2/clientcredentials",
        data={
            "name": credential_name,
            "scopes": list(scopes),
        },
        access_token=api_session.access_token,
    )
    client_id = _string_from_json(
        value=credentials_response,
        keys=("client_id", "clientId"),
    )
    client_secret = _string_from_json(
        value=credentials_response,
        keys=("client_secret", "clientSecret"),
    )
    return _ModelTargetWebAPIClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )


@beartype
def delete_model_target_web_api_client_credentials(
    *,
    driver: WebDriver,
    client_id: str,
) -> None:
    """Delete one OAuth2 client credential by its exact client ID."""
    driver.get(url="https://developer.vuforia.com/develop/credentials")
    wait_for_logged_in(driver=driver)
    api_session = _model_target_web_api_credentials_api_session(
        driver=driver,
    )
    encoded_client_id = quote(string=client_id, safe="")
    _request(
        session=api_session.session,
        method="DELETE",
        url=(
            "https://vws.vuforia.com/oauth2/clientcredentials/"
            f"{encoded_client_id}"
        ),
        data=None,
        access_token=api_session.access_token,
    )


@beartype
def _model_target_web_api_credentials_api_session(
    *,
    driver: WebDriver,
) -> _ModelTargetWebAPICredentialsAPISession:
    """Return a session and token for the credentials management API."""
    session = _requests_session_from_driver(driver=driver)

    logged_in_user = _json_request(
        session=session,
        method="GET",
        url=(
            "https://developer.vuforia.com"
            "/targetmanager/vuforiaUtil/getLoggedInUser"
        ),
        data=None,
        access_token=None,
    )
    user_id = _string_from_json(
        value=logged_in_user,
        keys=("eguid", "eGuid", "userId", "user_id"),
    )

    access_token_response = _json_request(
        session=session,
        method="POST",
        url=(
            "https://developer.vuforia.com"
            "/targetmanager/oauth2/credentials/accessToken"
        ),
        data={
            "userId": user_id,
            "scopes": [_OAUTH2_CLIENT_CREDENTIALS_SCOPE],
        },
        access_token=None,
    )
    access_token = _string_from_json(
        value=access_token_response,
        keys=("access_token", "accessToken"),
    )
    return _ModelTargetWebAPICredentialsAPISession(
        session=session,
        access_token=access_token,
    )


@beartype
def _requests_session_from_driver(
    *,
    driver: WebDriver,
) -> requests.Session:
    """Create a requests session using the browser's authenticated cookies."""
    session = requests.Session()
    # https://github.com/SeleniumHQ/selenium/pull/17536
    user_agent = driver.execute_script(  # pyright: ignore[reportUnknownMemberType]
        "return navigator.userAgent",
    )
    if isinstance(user_agent, str):
        session.headers.update({"User-Agent": user_agent})

    # https://github.com/SeleniumHQ/selenium/pull/17537
    raw_cookies: Any = driver.get_cookies()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    cookies: object = raw_cookies
    if not _is_json_array(cookies):
        return session

    for cookie in cookies:
        if not _is_json_object(cookie):
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue

        domain = cookie.get("domain")
        path = cookie.get("path")
        cookie_kwargs = {
            "path": path if isinstance(path, str) else "/",
        }
        if isinstance(domain, str):
            cookie_kwargs["domain"] = domain
        session.cookies.set(
            name=name,
            value=value,
            **cookie_kwargs,
        )

    return session


@beartype
def _is_json_object(value: object, /) -> TypeGuard[dict[object, object]]:
    """Return whether value is a JSON object."""
    return isinstance(value, dict)


@beartype
def _is_json_array(value: object, /) -> TypeGuard[list[object]]:
    """Return whether value is a JSON array."""
    return isinstance(value, list)


@beartype
def _string_from_json(
    *,
    value: object,
    keys: tuple[str, ...],
) -> str:
    """Find a non-empty string in a JSON-like value."""
    if _is_json_object(value):
        for key in keys:
            child = value.get(key)
            if isinstance(child, str):
                if child:
                    return child
                # An object which has the key but with an empty value is
                # the object we were looking for, and it is malformed.
                # Do not fall through to a nested object which happens
                # to have the same key.
                message = f"Response included an empty '{key}'."
                raise ValueError(message)
        for child in value.values():
            with contextlib.suppress(ValueError):
                return _string_from_json(value=child, keys=keys)

    if _is_json_array(value):
        for child in value:
            with contextlib.suppress(ValueError):
                return _string_from_json(value=child, keys=keys)

    message = f"Response did not include any of: {keys}"
    raise ValueError(message)


@beartype
def _json_request(
    *,
    session: requests.Session,
    method: str,
    url: str,
    data: dict[str, str | list[str]] | None,
    access_token: str | None,
) -> object:
    """Make a JSON request and return the response body."""
    response = _request(
        session=session,
        method=method,
        url=url,
        data=data,
        access_token=access_token,
    )

    try:
        response_body: object = response.json()
    except requests.JSONDecodeError as exc:
        content_type = response.headers.get("Content-Type", "unset")
        message = (
            f"Expected JSON from {url}, but the response had status "
            f"{response.status_code} and content type {content_type}: "
            f"{response.text[:500]}"
        )
        raise RuntimeError(message) from exc
    return response_body


@beartype
def _request(
    *,
    session: requests.Session,
    method: str,
    url: str,
    data: dict[str, str | list[str]] | None,
    access_token: str | None,
) -> requests.Response:
    """Make a request to the Vuforia credentials API."""
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        response = session.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        body_excerpt = ""
        if exc.response is not None:
            body_excerpt = f": {exc.response.text[:500]}"
        message = f"Could not call the Vuforia credentials API{body_excerpt}"
        raise RuntimeError(message) from exc
    return response


@_TIMEOUT_RETRY_DECORATOR
@beartype
def get_model_target_web_api_details(
    *,
    driver: WebDriver,
    scopes: Sequence[str] = MODEL_TARGET_WEB_API_STANDARD_SCOPES,
    cad_data_url: str = MODEL_TARGET_WEB_API_CAD_DATA_URL,
) -> ModelTargetWebAPIDict:
    """Get Model Target Web API credentials and a CAD data URL.

    The ``scopes`` argument selects which OAuth2 scopes are requested for
    the created credential. It defaults to
    ``MODEL_TARGET_WEB_API_STANDARD_SCOPES``, which is the only set of
    scopes available on non-Enterprise developer accounts. Pass
    ``MODEL_TARGET_WEB_API_ADVANCED_SCOPES`` to additionally request the
    advanced Model Target scope; this requires a Vuforia Enterprise
    developer account, and credential creation raises a ``RuntimeError``
    if the account is not entitled to a requested scope.

    The ``cad_data_url`` argument is returned as-is, as the
    ``cad_data_url`` item of the result. It defaults to
    ``MODEL_TARGET_WEB_API_CAD_DATA_URL``, a model pinned to a commit in
    the glTF sample models repository. Pass another URL to use a
    different model, or if that one stops resolving.
    """
    driver.get(url="https://developer.vuforia.com/develop/credentials")
    wait_for_logged_in(driver=driver)

    credential_name = (
        "vws-web-tools-model-target-web-api-"
        f"{datetime.datetime.now(tz=datetime.UTC):%Y-%m-%d-%H-%M-%S}-"
        f"{uuid.uuid4().hex}"
    )
    credentials = _create_model_target_web_api_client_credentials(
        driver=driver,
        credential_name=credential_name,
        scopes=scopes,
    )

    return {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "cad_data_url": cad_data_url,
    }


# ``Generator[...]`` with defaulted type arguments is not valid at
# runtime on Python 3.12, which this package supports.
@contextlib.contextmanager  # pyright: ignore[reportDeprecated]
@beartype
def model_target_web_api_details(
    *,
    driver: WebDriver,
    scopes: Sequence[str] = MODEL_TARGET_WEB_API_STANDARD_SCOPES,
    cad_data_url: str = MODEL_TARGET_WEB_API_CAD_DATA_URL,
) -> Iterator[ModelTargetWebAPIDict]:
    """Yield Model Target Web API details, then delete the credential.

    ``get_model_target_web_api_details`` creates an OAuth2 client
    credential on the Vuforia account, and nothing deletes it. A caller
    which raises before it gets to
    ``delete_model_target_web_api_client_credentials`` leaves the
    credential on the account. This deletes the credential however the
    ``with`` block is left.

    See ``get_model_target_web_api_details`` for the ``scopes`` and
    ``cad_data_url`` arguments.
    """
    details = get_model_target_web_api_details(
        driver=driver,
        scopes=scopes,
        cad_data_url=cad_data_url,
    )
    try:
        yield details
    finally:
        delete_model_target_web_api_client_credentials(
            driver=driver,
            client_id=details["client_id"],
        )


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
        click.echo(message=instance_id)
    finally:
        driver.quit()


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
        click.echo(message=instance_id)
    finally:
        driver.quit()


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
        if env_var_format:
            env_var_format_details = {
                "VUFORIA_TARGET_MANAGER_DATABASE_NAME": details[
                    "database_name"
                ],
                "VUFORIA_DATABASE_ID": details["database_id"],
                "VUFORIA_SERVER_ACCESS_KEY": details["server_access_key"],
                "VUFORIA_SERVER_SECRET_KEY": details["server_secret_key"],
                "VUFORIA_CLIENT_ACCESS_KEY": details["client_access_key"],
                "VUFORIA_CLIENT_SECRET_KEY": details["client_secret_key"],
            }

            for key, value in env_var_format_details.items():
                click.echo(message=f"{key}={shlex.quote(s=value)}")
        else:
            click.echo(message=yaml.dump(data=details), nl=False)
    finally:
        driver.quit()


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
        if env_var_format:
            env_var_format_details = {
                "VUFORIA_TARGET_MANAGER_DATABASE_NAME": details[
                    "database_name"
                ],
                "VUFORIA_SERVER_ACCESS_KEY": details["server_access_key"],
                "VUFORIA_SERVER_SECRET_KEY": details["server_secret_key"],
            }

            for key, value in env_var_format_details.items():
                click.echo(message=f"{key}={shlex.quote(s=value)}")
        else:
            click.echo(message=yaml.dump(data=details), nl=False)
    finally:
        driver.quit()


@click.command(name="delete-model-target-web-api-credentials")
@click.option("--client-id", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def delete_model_target_web_api_credentials(
    *,
    client_id: str,
    email_address: str,
    password: str,
) -> None:
    """Delete one Model Target Web API client credential."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        delete_model_target_web_api_client_credentials(
            driver=driver,
            client_id=client_id,
        )
    finally:
        driver.quit()


@click.command()
@click.option("--license-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@click.option("--env-var-format", is_flag=True)
@beartype
def show_license_details(
    *,
    license_name: str,
    email_address: str,
    password: str,
    env_var_format: bool,
) -> None:
    """Show the details of a license."""
    driver = create_chrome_driver()
    try:
        log_in(
            driver=driver,
            email_address=email_address,
            password=password,
        )
        details = get_license_details(
            driver=driver,
            license_name=license_name,
        )
        if env_var_format:
            env_var_format_details = {
                "VUFORIA_LICENSE_NAME": details["license_name"],
                "VUFORIA_LICENSE_KEY": details["license_key"],
            }
            for key, value in env_var_format_details.items():
                click.echo(message=f"{key}={shlex.quote(s=value)}")
        else:
            click.echo(message=yaml.dump(data=details), nl=False)
    finally:
        driver.quit()


vws_web_tools_group.add_command(cmd=create_vws_cloud_database)
vws_web_tools_group.add_command(cmd=create_vws_license)
vws_web_tools_group.add_command(cmd=create_vws_vumark_database)
vws_web_tools_group.add_command(cmd=delete_model_target_web_api_credentials)
vws_web_tools_group.add_command(cmd=delete_vws_license)
vws_web_tools_group.add_command(cmd=get_vumark_instance_id)
vws_web_tools_group.add_command(cmd=show_database_details)
vws_web_tools_group.add_command(cmd=show_license_details)
vws_web_tools_group.add_command(cmd=show_vumark_database_details)
vws_web_tools_group.add_command(cmd=upload_vumark_template_to_database)
vws_web_tools_group.add_command(cmd=wait_for_vumark_instance_id)
