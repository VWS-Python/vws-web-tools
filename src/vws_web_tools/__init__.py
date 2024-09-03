"""
Tools for interacting with the VWS (Vuforia Web Services) website.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


def get_database_details(driver: WebDriver) -> None:  # pragma: no cover
    """Get the database details."""
    driver.find_element(
        By.CLASS_NAME,
        "client-access-key",
    )
