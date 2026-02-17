"""Unit tests for VuMark target helper behavior."""

from __future__ import annotations

# mypy: ignore-errors
# ruff: noqa: ARG005,PLR2004,SLF001,TC003
# pylint: disable=protected-access,super-init-not-called
from collections.abc import Callable

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

import vws_web_tools


class _FakeLinkElement:
    """A fake Selenium element with a configurable link URL attribute."""

    def __init__(
        self,
        *,
        href: str | None,
    ) -> None:
        """Store the link URL returned by ``get_attribute``."""
        self._href = href

    def get_attribute(
        self,
        *,
        name: str,
    ) -> str | None:
        """Return configured link URL for the expected attribute."""
        assert name == "href"
        return self._href


class _FakeClickableElement:
    """A fake clickable Selenium element."""

    def click(self) -> None:
        """No-op click."""


class _FakeDriver(WebDriver):
    """A fake Selenium driver for deterministic helper tests."""

    def __init__(
        self,
        *,
        link_elements: list[object] | None = None,
        non_link_elements: list[object] | None = None,
    ) -> None:
        """Store fake element lists returned by ``find_elements``."""
        self._link_elements = [] if link_elements is None else link_elements
        self._non_link_elements = (
            [] if non_link_elements is None else non_link_elements
        )

    def find_elements(
        self,
        by: str = By.ID,
        value: str | None = None,
    ) -> list[object]:
        """Return fake elements based on requested locator expression."""
        assert by == By.XPATH
        assert value is not None
        if value.startswith("//a["):
            return self._link_elements
        if "not(self::a)" in value:
            return self._non_link_elements
        return []


class _FakeWait:
    """A fake WebDriverWait that evaluates callbacks synchronously."""

    def __init__(
        self,
        *,
        driver: WebDriver,
        timeout: int,
        ignored_exceptions: tuple[type[Exception], ...],
    ) -> None:
        """Store driver state used by ``until``."""
        self._driver = driver
        del timeout
        del ignored_exceptions
        self._until_calls = 0

    def until(
        self,
        method: Callable[[WebDriver], object],
    ) -> object:
        """Run the condition until it returns true."""
        self._until_calls += 1
        if self._until_calls == 1:
            return _FakeClickableElement()

        for _ in range(5):
            result = method(self._driver)
            if result:
                return result
        msg = "Condition never became truthy."
        raise AssertionError(msg)


def _fake_presence_of_element_located(
    *,
    locator: tuple[str, str],
) -> Callable[[WebDriver], object]:
    """Return a condition callable that is immediately true."""
    del locator
    return lambda driver: _FakeClickableElement()


def _patch_database_page_ready(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch page-readiness waits to resolve immediately."""
    monkeypatch.setattr(
        vws_web_tools,
        "WebDriverWait",
        _FakeWait,
    )
    monkeypatch.setattr(
        vws_web_tools.expected_conditions,
        "presence_of_element_located",
        _fake_presence_of_element_located,
    )


def test_xpath_literal_handles_quoted_values() -> None:
    """Quote handling should support both quote styles in target names."""
    assert vws_web_tools._xpath_literal(value="a'b") == '"a\'b"'
    assert (
        vws_web_tools._xpath_literal(value="a'\"b")
        == "concat('a', \"'\", '\"b')"
    )


def test_find_vumark_target_link_raises_when_href_missing() -> None:
    """A matching link row without a URL should hard-error."""
    driver = _FakeDriver(link_elements=[_FakeLinkElement(href=None)])
    with pytest.raises(vws_web_tools._VuMarkTargetNameNotLinkError):
        vws_web_tools._find_vumark_target_link(
            driver=driver,
            target_name="template",
        )


def test_find_vumark_target_link_raises_when_target_name_is_not_link() -> None:
    """A plain-text target-name cell should hard-error."""
    driver = _FakeDriver(non_link_elements=[object()])
    with pytest.raises(vws_web_tools._VuMarkTargetNameNotLinkError):
        vws_web_tools._find_vumark_target_link(
            driver=driver,
            target_name="template",
        )


def test_wait_for_vumark_target_link_retries_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry predicate should treat non-link and missing-link as not ready."""
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )
    _patch_database_page_ready(monkeypatch=monkeypatch)

    attempt_number = 0

    def fake_find_vumark_target_link(
        *,
        driver: WebDriver,
        target_name: str,
    ) -> str:
        """Raise not-ready errors before eventually returning a link."""
        del driver
        del target_name
        nonlocal attempt_number
        attempt_number += 1
        if attempt_number == 1:
            msg = "Target name present but not link yet."
            raise vws_web_tools._VuMarkTargetNameNotLinkError(msg)
        if attempt_number == 2:
            msg = "Target row not found yet."
            raise vws_web_tools._VuMarkTargetLinkNotFoundError(msg)
        return (
            "https://developer.vuforia.com/develop/databases/"
            "database/targets/44db1c5c467641328c98e485b7e61222"
        )

    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        fake_find_vumark_target_link,
    )
    vws_web_tools.wait_for_vumark_target_link(
        driver=_FakeDriver(),
        database_name="database",
        target_name="template",
        timeout=1,
    )
    assert attempt_number == 3


def test_get_vumark_target_id_wraps_not_link_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-link target names should raise a lookup error."""
    _patch_database_page_ready(monkeypatch=monkeypatch)
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )

    def fake_find_vumark_target_link(
        *,
        driver: WebDriver,
        target_name: str,
    ) -> str:
        """Simulate a non-link target cell."""
        del driver
        del target_name
        msg = "Target name present but not link."
        raise vws_web_tools._VuMarkTargetNameNotLinkError(msg)

    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        fake_find_vumark_target_link,
    )

    with pytest.raises(
        expected_exception=vws_web_tools._VuMarkTargetIdLookupError,
        match="only available",
    ):
        vws_web_tools.get_vumark_target_id(
            driver=_FakeDriver(),
            database_name="database",
            target_name="template",
        )


def test_get_vumark_target_id_wraps_missing_link_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing target rows should raise a lookup error."""
    _patch_database_page_ready(monkeypatch=monkeypatch)
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )

    def fake_find_vumark_target_link(
        *,
        driver: WebDriver,
        target_name: str,
    ) -> str:
        """Simulate no matching target row."""
        del driver
        del target_name
        msg = "Target row not found."
        raise vws_web_tools._VuMarkTargetLinkNotFoundError(msg)

    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        fake_find_vumark_target_link,
    )

    with pytest.raises(
        expected_exception=vws_web_tools._VuMarkTargetIdLookupError,
        match="not found",
    ):
        vws_web_tools.get_vumark_target_id(
            driver=_FakeDriver(),
            database_name="database",
            target_name="template",
        )


def test_get_vumark_target_id_raises_for_empty_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty returned link should raise a lookup error."""
    _patch_database_page_ready(monkeypatch=monkeypatch)
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )
    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        lambda *, driver, target_name: "",
    )

    with pytest.raises(
        expected_exception=vws_web_tools._VuMarkTargetIdLookupError,
        match="not found",
    ):
        vws_web_tools.get_vumark_target_id(
            driver=_FakeDriver(),
            database_name="database",
            target_name="template",
        )


def test_get_vumark_target_id_raises_for_missing_target_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed link without a target ID should raise a lookup
    error.
    """
    _patch_database_page_ready(monkeypatch=monkeypatch)
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )
    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        lambda *, driver, target_name: "https://developer.vuforia.com/",
    )

    with pytest.raises(
        expected_exception=vws_web_tools._VuMarkTargetIdLookupError,
        match="not found in the target link",
    ):
        vws_web_tools.get_vumark_target_id(
            driver=_FakeDriver(),
            database_name="database",
            target_name="template",
        )


def test_get_vumark_target_id_raises_for_missing_target_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the target row never appears, raise a lookup error."""

    class _FakeWaitMissingRow(_FakeWait):
        """Raise timeout on the target-row wait."""

        def until(
            self,
            method: Callable[[WebDriver], object],
        ) -> object:
            """Raise timeout on the third condition check."""
            del method
            self._until_calls += 1
            if self._until_calls == 3:
                raise TimeoutException
            return _FakeClickableElement()

    monkeypatch.setattr(
        vws_web_tools,
        "WebDriverWait",
        _FakeWaitMissingRow,
    )
    monkeypatch.setattr(
        vws_web_tools.expected_conditions,
        "presence_of_element_located",
        _fake_presence_of_element_located,
    )
    monkeypatch.setattr(
        vws_web_tools,
        "navigate_to_database",
        lambda *, driver, database_name: None,
    )
    monkeypatch.setattr(
        vws_web_tools,
        "_find_vumark_target_link",
        lambda *, driver, target_name: (
            "https://developer.vuforia.com/develop/databases/"
            "database/targets/44db1c5c467641328c98e485b7e61222"
        ),
    )

    with pytest.raises(
        expected_exception=vws_web_tools._VuMarkTargetIdLookupError,
        match="row was not found",
    ):
        vws_web_tools.get_vumark_target_id(
            driver=_FakeDriver(),
            database_name="database",
            target_name="template",
        )
