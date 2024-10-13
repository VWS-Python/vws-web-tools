"""
Tools for interacting with the VWS (Vuforia Web Services) website.
"""

import contextlib
import time
from typing import TypedDict

import click
import yaml
from beartype import beartype
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait


@beartype
class DatabaseDict(TypedDict):
    """
    A dictionary type which represents a database.
    """

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
) -> None:  # pragma: no cover
    """
    Log in to Vuforia web services.
    """
    log_in_url = "https://developer.vuforia.com/vui/auth/login"
    driver.get(url=log_in_url)
    email_address_input_element = driver.find_element(
        by=By.ID,
        value="login_email",
    )


import pytest


@pytest.mark.parametrize("foo", ["bar"])
def test_example(foo: int) -> None:
    """
    Test example.
    """
    assert foo == "bar"
