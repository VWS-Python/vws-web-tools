"""Tests for VuMark target lookup flows."""

from collections.abc import Callable

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

import vws_web_tools


def _fake_navigate_to_database(
    *,
    driver: WebDriver,
    database_name: str,
) -> None:
    """Test double for database navigation."""
    del driver, database_name


class _FakeElement:
    """A minimal Selenium element test double."""

    def click(self) -> None:
        """Simulate clicking an element."""


class _FakeDriver(WebDriver):
    """A minimal Selenium WebDriver test double."""

    def __init__(self) -> None:
        """Initialise captured XPath queries."""
        self.xpath_queries: list[str] = []

    def find_element(self, by: str, value: str) -> _FakeElement:
        """Return an element while capturing XPath lookups."""
        if by == "xpath":
            self.xpath_queries.append(value)
        return _FakeElement()

    def find_elements(self, by: str, value: str) -> list[_FakeElement]:
        """Return elements while capturing XPath lookups."""
        if by == "xpath":
            self.xpath_queries.append(value)
            return [_FakeElement()]
        return []


class _FakeWebDriverWait:
    """A minimal WebDriverWait test double."""

    def __init__(
        self,
        *,
        driver: WebDriver,
        timeout: int,
        ignored_exceptions: tuple[type[Exception], ...],
    ) -> None:
        """Store the driver used for `until` callbacks."""
        del timeout, ignored_exceptions
        self._driver = driver

    def until(
        self,
        *,
        method: Callable[[WebDriver], object],
    ) -> object:
        """Evaluate the supplied method once."""
        value = method(self._driver)
        if value:
            return value
        raise TimeoutException


def test_wait_for_vumark_target_link_with_single_quote(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single quotes in target names produce valid XPath in wait flow."""
    target_name = "template's name"
    driver = _FakeDriver()
    monkeypatch.setattr(
        target=vws_web_tools,
        name="navigate_to_database",
        value=_fake_navigate_to_database,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="WebDriverWait",
        value=_FakeWebDriverWait,
    )

    vws_web_tools.wait_for_vumark_target_link(
        driver=driver,
        database_name="database-name",
        target_name=target_name,
        timeout=1,
    )

    assert any(
        f'normalize-space(.) = "{target_name}"' in xpath_query
        for xpath_query in driver.xpath_queries
    )


def test_get_vumark_target_id_with_single_quote(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single quotes in target names produce valid XPath in ID lookup."""
    target_name = "template's name"
    expected_target_id = "0123456789abcdef0123456789abcdef"
    driver = _FakeDriver()

    def _fake_find_vumark_target_link(
        *,
        driver: WebDriver,
        target_name: str,
    ) -> str:
        """Test double for target-link lookup."""
        del driver, target_name
        return f"https://developer.vuforia.com/targetmanager/database/abc/{expected_target_id}"

    monkeypatch.setattr(
        target=vws_web_tools,
        name="navigate_to_database",
        value=_fake_navigate_to_database,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="WebDriverWait",
        value=_FakeWebDriverWait,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="_find_vumark_target_link",
        value=_fake_find_vumark_target_link,
    )

    target_id = vws_web_tools.get_vumark_target_id(
        driver=driver,
        database_name="database-name",
        target_name=target_name,
    )

    assert target_id == expected_target_id
    assert any(
        f'normalize-space(.) = "{target_name}"' in xpath_query
        for xpath_query in driver.xpath_queries
    )
