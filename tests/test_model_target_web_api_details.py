# pyright: reportPrivateUsage=false
# pylint: disable=protected-access,super-init-not-called
# ruff: noqa: ANN401, SLF001
"""Tests for Model Target Web API detail helpers."""

from collections.abc import Sequence
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


class _NavigationDriver(WebDriver):
    """A WebDriver shell which records navigation."""

    def __init__(self) -> None:
        """Create an empty navigation record."""
        self.requested_urls: list[str] = []

    def get(self, url: str) -> None:
        """Record a requested URL."""
        self.requested_urls.append(url)


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


def test_create_model_target_web_api_client_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client credentials are created with the requested name and
    scopes.
    """
    driver = _NavigationDriver()
    session = _Session(
        response=_response(
            content=(
                b'{"clientId": "client-id", "clientSecret": "client-secret"}'
            ),
        ),
    )

    def credentials_api_session(
        *,
        driver: WebDriver,
    ) -> tuple[requests.Session, str]:
        """Return the controlled authenticated session."""
        assert driver is not None
        return session, "access-token"

    monkeypatch.setattr(
        target=vws_web_tools,
        name="_model_target_web_api_credentials_api_session",
        value=credentials_api_session,
    )

    credentials = (
        vws_web_tools._create_model_target_web_api_client_credentials(
            driver=driver,
            credential_name="credential-name",
            scopes=("scope-one", "scope-two"),
        )
    )

    assert credentials.client_id == "client-id"
    assert credentials.client_secret == "client-secret"  # noqa: S105
    assert session.prepared_request is not None
    assert session.prepared_request.method == "POST"
    assert session.prepared_request.url == (
        "https://vws.vuforia.com/oauth2/clientcredentials"
    )
    assert session.prepared_request.body == (
        b'{"name": "credential-name", "scopes": ["scope-one", "scope-two"]}'
    )
    assert session.prepared_request.headers["Authorization"] == (
        "Bearer access-token"
    )


def test_delete_model_target_web_api_client_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the credential with the exact client ID is deleted."""
    driver = _NavigationDriver()
    session = _Session(response=_response(status_code=204, content=b""))

    def credentials_api_session(
        *,
        driver: WebDriver,
    ) -> tuple[requests.Session, str]:
        """Return the controlled authenticated session."""
        assert driver is not None
        return session, "access-token"

    def wait_for_logged_in(*, driver: WebDriver) -> None:
        """Record that login waiting was requested."""
        assert driver is not None

    monkeypatch.setattr(
        target=vws_web_tools,
        name="_model_target_web_api_credentials_api_session",
        value=credentials_api_session,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="wait_for_logged_in",
        value=wait_for_logged_in,
    )

    vws_web_tools.delete_model_target_web_api_client_credentials(
        driver=driver,
        client_id="client/id",
    )

    assert session.prepared_request is not None
    assert driver.requested_urls == [
        "https://developer.vuforia.com/develop/credentials",
    ]
    assert session.prepared_request.method == "DELETE"
    assert session.prepared_request.url == (
        "https://vws.vuforia.com/oauth2/clientcredentials/client%2Fid"
    )
    assert session.prepared_request.body is None
    assert session.prepared_request.headers["Authorization"] == (
        "Bearer access-token"
    )


def test_get_model_target_web_api_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Details use unique credential names and the requested scopes."""
    driver = _NavigationDriver()
    created_credential_names: list[str] = []
    created_scopes: list[Sequence[str]] = []

    def wait_for_logged_in(*, driver: WebDriver) -> None:
        """Record that login waiting was requested."""
        assert driver is not None

    def create_client_credentials(
        *,
        driver: WebDriver,
        credential_name: str,
        scopes: Sequence[str],
    ) -> vws_web_tools._ModelTargetWebAPIClientCredentials:
        """Record creation inputs and return controlled credentials."""
        assert driver is not None
        created_credential_names.append(credential_name)
        created_scopes.append(scopes)
        return vws_web_tools._ModelTargetWebAPIClientCredentials(
            client_id="client-id",
            client_secret="client-secret",  # noqa: S106
        )

    monkeypatch.setattr(
        target=vws_web_tools,
        name="wait_for_logged_in",
        value=wait_for_logged_in,
    )
    monkeypatch.setattr(
        target=vws_web_tools,
        name="_create_model_target_web_api_client_credentials",
        value=create_client_credentials,
    )

    details = vws_web_tools.get_model_target_web_api_details(
        driver=driver,
        scopes=("scope",),
    )

    assert driver.requested_urls == [
        "https://developer.vuforia.com/develop/credentials",
    ]
    assert created_scopes == [("scope",)]
    assert len(created_credential_names) == 1
    credential_name = created_credential_names[0]
    assert credential_name.startswith("vws-web-tools-model-target-web-api-")
    credential_uuid = credential_name.rsplit(sep="-", maxsplit=1)[1]
    uuid_hex_length = 32
    assert len(credential_uuid) == uuid_hex_length
    assert all(
        character in "0123456789abcdef" for character in credential_uuid
    )
    assert details == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "cad_data_url": vws_web_tools._MODEL_TARGET_WEB_API_CAD_DATA_URL,
    }


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
