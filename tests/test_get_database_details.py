"""Unit tests for ``get_database_details``."""

import inspect
from collections.abc import Callable
from typing import cast

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions

import vws_web_tools


class _FakeDriver:
    """A minimal WebDriver-like object for exercising retry logic."""

    def __init__(self) -> None:
        """Initialize driver state for assertions."""
        self.visited_urls: list[str] = []

    def get(self, url: str) -> None:
        """Record visited URLs."""
        self.visited_urls.append(url)

    def find_elements(
        self,
        *,
        by: str,
        value: str,
    ) -> list[object]:
        """Return no database rows."""
        assert by == By.XPATH
        assert "_project_name" in value
        return []

    def find_element(
        self,
        *,
        by: str,
        value: str,
    ) -> object:
        """Raise when no next-page button exists."""
        assert by == By.CSS_SELECTOR
        assert value == "button.p-paginator-next:not(.p-disabled)"
        raise NoSuchElementException


class _FakeWebDriverWait:
    """A deterministic substitute for ``WebDriverWait``."""

    def __init__(
        self,
        *,
        driver: _FakeDriver,
        timeout: int,
        ignored_exceptions: list[type[Exception]] | None = None,
    ) -> None:
        """Store the fake driver and ignore wait configuration."""
        del timeout, ignored_exceptions
        self._driver = driver

    def until(self, method: Callable[[_FakeDriver], object]) -> object:
        """Evaluate exactly once and timeout on a falsey response."""
        result = method(self._driver)
        if result is False:
            raise TimeoutException
        return result


def test_get_database_details_refreshes_when_last_page_has_no_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The databases page is reloaded when pagination cannot continue."""
    dismissed_drivers: list[_FakeDriver] = []

    def _fake_dismiss_cookie_banner(driver: _FakeDriver) -> None:
        """Record each call so we can assert reload behavior."""
        dismissed_drivers.append(driver)

    monkeypatch.setattr(
        target=vws_web_tools,
        name="_dismiss_cookie_banner",
        value=_fake_dismiss_cookie_banner,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="WebDriverWait",
        value=_FakeWebDriverWait,
    )

    def _fake_element_to_be_clickable(
        mark: tuple[str, str],
    ) -> Callable[[_FakeDriver], bool]:
        """Return a predicate which always considers the element clickable."""
        del mark

        def _always_clickable(_driver: _FakeDriver) -> bool:
            """Pretend the expected element is clickable."""
            return True

        return _always_clickable

    monkeypatch.setattr(
        target=expected_conditions,
        name="element_to_be_clickable",
        value=_fake_element_to_be_clickable,
    )

    driver = _FakeDriver()
    unwrapped_get_database_details = cast(
        "Callable[..., object]",
        inspect.unwrap(vws_web_tools.get_database_details),
    )
    with pytest.raises(expected_exception=TimeoutException):
        unwrapped_get_database_details(
            driver=driver,
            database_name="database-does-not-exist",
        )

    target_manager_url = "https://developer.vuforia.com/develop/databases"
    assert driver.visited_urls == [target_manager_url, target_manager_url]
    assert dismissed_drivers == [driver, driver]
