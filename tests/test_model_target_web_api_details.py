# pyright: reportPrivateUsage=false
# pylint: disable=protected-access,super-init-not-called
# ruff: noqa: ANN401, SLF001
"""Tests for Model Target Web API detail helpers."""

from typing import Any

import pytest
import requests
from selenium.webdriver.remote.webdriver import WebDriver

import vws_web_tools


class _BrowserStateDriver(WebDriver):
    """A WebDriver shell with controlled browser state."""

    def __init__(
        self,
        *,
        user_agent: object,
        cookies: object,
    ) -> None:
        """Store controlled browser state."""
        self._user_agent = user_agent
        self._cookies = cookies

    def execute_script(self, script: str, *args: object) -> object:
        """Return the controlled user agent."""
        assert script == "return navigator.userAgent"
        assert not args
        return self._user_agent

    def get_cookies(self) -> Any:
        """Return the controlled cookies."""
        return self._cookies


def test_requests_session_from_driver_copies_browser_state() -> None:
    """Cookies and the user agent are copied into a requests session."""
    driver = _BrowserStateDriver(
        user_agent="test browser",
        cookies=[
            {
                "name": "session",
                "value": "abc",
                "domain": "example.com",
                "path": "/developer",
            },
            {"name": "host", "value": "only"},
            {"name": "bad-value", "value": 123},
            "not a cookie",
        ],
    )

    session = vws_web_tools._requests_session_from_driver(driver=driver)

    assert session.headers["User-Agent"] == "test browser"
    assert session.cookies.get(name="session", domain="example.com") == "abc"
    assert session.cookies.get(name="host") == "only"
    assert session.cookies.get(name="bad-value") is None


@pytest.mark.parametrize(
    argnames=("user_agent", "cookies"),
    argvalues=[
        (None, []),
        ("test browser", "not a cookie list"),
    ],
)
def test_requests_session_from_driver_handles_unexpected_browser_state(
    *,
    user_agent: object,
    cookies: object,
) -> None:
    """Unexpected browser state is ignored."""
    driver = _BrowserStateDriver(
        user_agent=user_agent,
        cookies=cookies,
    )

    session = vws_web_tools._requests_session_from_driver(driver=driver)

    assert session.headers["User-Agent"] == (
        user_agent if isinstance(user_agent, str) else "python-requests/2.34.2"
    )
    assert not session.cookies


def test_string_from_json_finds_nested_values() -> None:
    """A non-empty matching string is found recursively."""
    result = vws_web_tools._string_from_json(
        value={
            "client_id": "",
            "nested": [
                {"clientId": "client-id"},
            ],
        },
        keys=("client_id", "clientId"),
    )

    assert result == "client-id"


def test_string_from_json_raises_for_missing_values() -> None:
    """A missing matching string raises a useful error."""
    with pytest.raises(
        expected_exception=ValueError,
        match="Response did not include any of",
    ):
        vws_web_tools._string_from_json(
            value={"nested": [None, {"client_id": ""}]},
            keys=("client_id", "clientId"),
        )


def _response(
    *,
    status_code: int = 200,
    content: bytes = b'{"ok": true}',
) -> requests.Response:
    """Return a minimal requests response."""
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://example.com"
    response._content = content  # noqa: V101
    return response


class _Session(requests.Session):
    """A requests session with a controlled response."""

    def __init__(
        self,
        *,
        response: requests.Response,
    ) -> None:
        """Store the response returned by the fake session."""
        super().__init__()
        self.prepared_request: requests.PreparedRequest | None = None
        self.send_kwargs: dict[str, object] | None = None
        self._response = response

    def send(  # noqa: V105
        self,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        """Store the prepared request and return the controlled
        response.
        """
        self.prepared_request = request
        self.send_kwargs = kwargs
        return self._response


class _FailingSession(requests.Session):
    """A requests session which fails before receiving a response."""

    def send(  # noqa: V105
        self,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        """Raise a request failure without an HTTP response."""
        assert request.url == "https://example.com/"
        assert kwargs["timeout"] == vws_web_tools._REQUEST_TIMEOUT_SECONDS
        raise requests.ConnectionError


def test_json_request_sends_json_headers_and_returns_response_body() -> None:
    """JSON requests include headers, payloads, and access tokens."""
    session = _Session(response=_response())

    response = vws_web_tools._json_request(
        session=session,
        method="POST",
        url="https://example.com",
        data={"name": "credential", "scopes": ["scope"]},
        access_token="test-access-token",  # noqa: S106
    )

    assert response == {"ok": True}
    assert session.prepared_request is not None
    assert session.prepared_request.method == "POST"
    assert session.prepared_request.body == (
        b'{"name": "credential", "scopes": ["scope"]}'
    )
    assert (
        session.prepared_request.headers["Authorization"]
        == "Bearer test-access-token"
    )
    assert session.send_kwargs is not None
    assert (
        session.send_kwargs["timeout"]
        == vws_web_tools._REQUEST_TIMEOUT_SECONDS
    )


def test_json_request_raises_runtime_error_for_request_failure() -> None:
    """Request failures include a response body excerpt."""
    session = _Session(
        response=_response(
            status_code=500,
            content=b"response body",
        ),
    )

    with pytest.raises(expected_exception=RuntimeError, match="response body"):
        vws_web_tools._json_request(
            session=session,
            method="GET",
            url="https://example.com",
        )


def test_json_request_raises_runtime_error_for_connection_failure() -> None:
    """Connection failures raise a stable runtime error."""
    with pytest.raises(
        expected_exception=RuntimeError,
        match=r"Could not call the Vuforia credentials API$",
    ):
        vws_web_tools._json_request(
            session=_FailingSession(),
            method="GET",
            url="https://example.com",
        )


def test_json_request_raises_runtime_error_for_invalid_json() -> None:
    """Invalid JSON responses raise a stable runtime error."""
    session = _Session(response=_response(content=b"not json"))

    with pytest.raises(
        expected_exception=RuntimeError, match="unexpected shape"
    ):
        vws_web_tools._json_request(
            session=session,
            method="GET",
            url="https://example.com",
        )
