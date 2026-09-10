# pyright: reportPrivateUsage=false
# pylint: disable=protected-access
# ruff: noqa: SLF001
"""Tests for finding VuMark target links."""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import vws_web_tools


class _NoElementsDriver:
    """A WebDriver shell which finds no elements."""

    @staticmethod
    def find_elements(
        *,
        by: str,
        value: str,
    ) -> list[WebElement]:
        """Return no elements."""
        assert by == By.XPATH
        assert value.startswith("//a[")
        return []


def test_find_vumark_target_link_without_a_link() -> None:
    """A target which is not rendered as a link raises a useful error."""
    with pytest.raises(
        expected_exception=ValueError,
        match="No link was found for the target named 'my-target'",
    ):
        _ = vws_web_tools._find_vumark_target_link(
            driver=_NoElementsDriver(),
            target_name="my-target",
        )
