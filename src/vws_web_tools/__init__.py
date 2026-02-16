"""Tools for interacting with the VWS (Vuforia Web Services) website."""

import contextlib
from pathlib import Path
from typing import Literal, TypedDict

import click
import yaml
from beartype import beartype
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait


@beartype
def create_chrome_driver() -> WebDriver:
    """Create a headless Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument(argument="--headless=new")
    options.add_argument(argument="--no-sandbox")
    options.add_argument(argument="--disable-dev-shm-usage")
    # Use a large window so that pagination controls are visible
    # and clickable without scrolling.
    options.add_argument(argument="--window-size=1920,1080")
    return webdriver.Chrome(options=options)


@beartype
class DatabaseDict(TypedDict):
    """A dictionary type which represents a database."""

    database_name: str
    server_access_key: str
    server_secret_key: str
    client_access_key: str
    client_secret_key: str


DatabaseType = Literal["cloud", "vumark"]


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
            or bool(
                d.find_elements(
                    by=By.CSS_SELECTOR,
                    value=".userNameInHeaderSpan",
                ),
            )
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
    thirty_second_wait.until(
        method=expected_conditions.url_changes(url=new_license_url),
    )


@beartype
def create_database(
    driver: WebDriver,
    database_name: str,
    license_name: str | None = None,
    *,
    database_type: DatabaseType = "cloud",
) -> None:
    """Create a database."""
    if database_type == "cloud" and not license_name:
        msg = "license_name is required for cloud databases."
        raise ValueError(msg)
    if database_type not in {"cloud", "vumark"}:
        msg = "database_type must be one of {'cloud', 'vumark'}."
        raise ValueError(msg)

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

    # Vuforia has changed radio IDs before, so we first try known IDs and
    # then fall back to matching visible type labels.
    if database_type == "vumark":
        vumark_selected = False
        for vumark_radio_id in ("vumark-radio-btn", "vu-mark-radio-btn"):
            with contextlib.suppress(NoSuchElementException):
                vumark_type_radio_element = driver.find_element(
                    by=By.ID,
                    value=vumark_radio_id,
                )
                vumark_type_radio_element.click()
                vumark_selected = True
                break

        if not vumark_selected:
            vumark_label_matches = driver.find_elements(
                by=By.XPATH,
                value=(
                    "//label[normalize-space()='VuMark']"
                    "|//*[self::span or self::div]"
                    "[normalize-space()='VuMark']"
                ),
            )
            if vumark_label_matches:
                vumark_label_matches[0].click()
                vumark_selected = True

        if not vumark_selected:
            msg = "Could not find a VuMark database type option in the UI."
            raise NoSuchElementException(msg)
    else:
        cloud_type_radio_element = driver.find_element(
            by=By.ID,
            value="cloud-radio-btn",
        )
        cloud_type_radio_element.click()

        thirty_second_wait.until(
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

    generate_button = driver.find_element(
        by=By.ID,
        value="generate-btn",
    )
    generate_button.click()
    thirty_second_wait.until(
        method=expected_conditions.staleness_of(element=generate_button),
    )


@beartype
def upload_vumark_svg_template(
    driver: WebDriver,
    database_name: str,
    svg_template_path: Path,
    target_name: str,
) -> None:
    """Upload a VuMark SVG template to a VuMark database."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)
    three_minute_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )
    three_minute_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_project_name"),
        ),
    )

    def _click_database_row(
        d: WebDriver,
    ) -> bool:
        """Click the database row when visible, paging until it
        appears.
        """
        rows = d.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                f" and contains(@id, '_project_name')"
                f" and normalize-space(text())='{database_name}']"
            ),
        )
        if rows:
            rows[0].click()
            return True
        d.execute_script(  # pyright: ignore[reportUnknownMemberType]
            """
            const nextButton = document.querySelector(
                "button.p-paginator-next:not(.p-disabled)"
            );
            const firstButton = document.querySelector(
                "button.p-paginator-first:not(.p-disabled)"
            );
            (nextButton || firstButton)?.click();
            """
        )
        return False

    three_minute_wait.until(
        method=_click_database_row,
    )

    one_minute_wait = WebDriverWait(
        driver=driver,
        timeout=60,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    add_target_button = one_minute_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(
                By.XPATH,
                "//button[contains(normalize-space(), 'Add Target')]"
                "|//a[contains(normalize-space(), 'Add Target')]",
            ),
        ),
    )
    add_target_button.click()

    svg_template_input = one_minute_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.CSS_SELECTOR, "input[type='file']"),
        ),
    )
    svg_template_input.send_keys(str(svg_template_path.resolve(strict=True)))

    target_name_input = one_minute_wait.until(
        method=expected_conditions.visibility_of_element_located(
            locator=(
                By.XPATH,
                "//input[@id='target-name' or @name='target-name'"
                " or @id='name' or @name='name']",
            ),
        ),
    )
    target_name_input.clear()
    target_name_input.send_keys(target_name)

    add_button = one_minute_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(
                By.XPATH,
                "//div[@role='dialog']//button[normalize-space()='Add'"
                " or normalize-space()='Add Target']"
                "|//button[normalize-space()='Add'"
                " or normalize-space()='Add Target']",
            ),
        ),
    )
    add_button.click()
    one_minute_wait.until(
        method=expected_conditions.staleness_of(element=add_button),
    )


@beartype
def get_database_details(
    driver: WebDriver,
    database_name: str,
) -> DatabaseDict:
    """Get details of a database."""
    target_manager_url = "https://developer.vuforia.com/develop/databases"
    driver.get(url=target_manager_url)
    _dismiss_cookie_banner(driver=driver)
    thirty_second_wait = WebDriverWait(
        driver=driver,
        timeout=180,
        ignored_exceptions=(
            NoSuchElementException,
            StaleElementReferenceException,
        ),
    )

    # We find the database by scanning table rows and paginating
    # rather than using the table search input. The search input
    # does not reliably trigger table filtering in headless Chrome
    # (send_keys does not fire the expected change events).
    thirty_second_wait.until(
        method=expected_conditions.element_to_be_clickable(
            mark=(By.ID, "table_row_0_project_name"),
        ),
    )

    def _click_database_row(
        d: WebDriver,
    ) -> bool:
        """Find the row matching database_name on the current page.

        If not found, click the next-page button and return False to
        retry. If there is no next page, reload the listing so that
        newly created databases can appear.
        """
        rows = d.find_elements(
            by=By.XPATH,
            value=(
                "//span[starts-with(@id, 'table_row_')"
                f" and contains(@id, '_project_name')"
                f" and normalize-space(text())='{database_name}']"
            ),
        )
        if rows:
            rows[0].click()
            return True
        d.execute_script(  # pyright: ignore[reportUnknownMemberType]
            """
            const nextButton = document.querySelector(
                "button.p-paginator-next:not(.p-disabled)"
            );
            const firstButton = document.querySelector(
                "button.p-paginator-first:not(.p-disabled)"
            );
            (nextButton || firstButton)?.click();
            """
        )
        return False

    thirty_second_wait.until(
        method=_click_database_row,
    )

    access_keys_tab_item = thirty_second_wait.until(
        method=expected_conditions.presence_of_element_located(
            locator=(By.LINK_TEXT, "Database Access Keys"),
        ),
    )

    access_keys_tab_item.click()

    expected_key_boxes = 2

    thirty_second_wait.until(
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
    license_name: str,
    email_address: str,
    password: str,
) -> None:
    """Create a license."""
    driver = create_chrome_driver()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    create_license(driver=driver, license_name=license_name)
    driver.quit()


@click.command()
@click.option("--license-name")
@click.option("--database-name", required=True)
@click.option(
    "--database-type",
    default="cloud",
    show_default=True,
    type=click.Choice(choices=["cloud", "vumark"], case_sensitive=False),
)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def create_vws_database(
    database_name: str,
    license_name: str | None,
    database_type: str,
    email_address: str,
    password: str,
) -> None:
    """Create a database."""
    if database_type.lower() == "cloud" and not license_name:
        msg = "--license-name is required when --database-type is cloud."
        raise click.UsageError(msg)

    driver = create_chrome_driver()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    create_database(
        driver=driver,
        database_name=database_name,
        license_name=license_name,
        database_type=database_type.lower(),
    )
    driver.quit()


@click.command()
@click.option("--database-name", required=True)
@click.option(
    "--svg-template-path",
    required=True,
    type=click.Path(
        exists=True,
        dir_okay=False,
        path_type=Path,
    ),
)
@click.option("--target-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@beartype
def upload_vumark_template(
    database_name: str,
    svg_template_path: Path,
    target_name: str,
    email_address: str,
    password: str,
) -> None:
    """Upload a VuMark SVG template to a database."""
    driver = create_chrome_driver()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    upload_vumark_svg_template(
        driver=driver,
        database_name=database_name,
        svg_template_path=svg_template_path,
        target_name=target_name,
    )
    driver.quit()


@click.command()
@click.option("--database-name", required=True)
@click.option("--email-address", envvar="VWS_EMAIL_ADDRESS", required=True)
@click.option("--password", envvar="VWS_PASSWORD", required=True)
@click.option("--env-var-format", is_flag=True)
@beartype
def show_database_details(
    database_name: str,
    email_address: str,
    password: str,
    *,
    env_var_format: bool,
) -> None:
    """Show the details of a database."""
    driver = create_chrome_driver()
    log_in(driver=driver, email_address=email_address, password=password)
    wait_for_logged_in(driver=driver)
    details = get_database_details(
        driver=driver,
        database_name=database_name,
    )
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


vws_web_tools_group.add_command(cmd=create_vws_database)
vws_web_tools_group.add_command(cmd=create_vws_license)
vws_web_tools_group.add_command(cmd=show_database_details)
vws_web_tools_group.add_command(cmd=upload_vumark_template)
