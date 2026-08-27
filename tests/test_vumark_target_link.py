# pyright: reportPrivateUsage=false
# pylint: disable=protected-access,super-init-not-called
# ruff: noqa: ANN401, SLF001
"""Tests for finding VuMark target links."""

from typing import Any

import pytest
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

import vws_web_tools


class _NoElementsDriver(WebDriver):
    """A WebDriver shell which finds no elements."""

    def __init__(self) -> None:
        """Avoid starting a browser session."""

    def find_elements(  # noqa: V105
        self,
        *args: Any,
        **kwargs: Any,
    ) -> list[WebElement]:
        """Return no elements."""
        assert not args
        assert kwargs
        return []


def test_find_vumark_target_link_without_a_link() -> None:
    """A target which is not rendered as a link raises a useful error."""
    with pytest.raises(
        expected_exception=ValueError,
        match="No link was found for the target named 'my-target'",
    ):
        vws_web_tools._find_vumark_target_link(
            driver=_NoElementsDriver(),
            target_name="my-target",
        )
