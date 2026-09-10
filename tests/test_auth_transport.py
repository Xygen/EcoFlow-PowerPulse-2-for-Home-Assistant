"""Transport-level tests for EcoFlow sign-in and provider reads.

The real ``aiohttp`` and ``cryptography`` packages are not test dependencies,
so both are replaced by minimal stubs. The modules under test are the real
ones: only the network boundary is doubled.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest


def _install_transport_stubs() -> None:
    """Provide the small external surface the auth modules import."""
    if "aiohttp" not in sys.modules:
        aiohttp = ModuleType("aiohttp")

        class ClientError(Exception):
            """Stand-in for the aiohttp error base class."""

        class ClientSession:
            """Only used as a type annotation by the code under test."""

        class ClientTimeout:
            def __init__(self, total: float | None = None) -> None:
                self.total = total

        aiohttp.ClientError = ClientError
        aiohttp.ClientSession = ClientSession
        aiohttp.ClientTimeout = ClientTimeout
        sys.modules["aiohttp"] = aiohttp

    if "cryptography" not in sys.modules:
        for name in (
            "cryptography",
            "cryptography.hazmat",
            "cryptography.hazmat.primitives",
            "cryptography.hazmat.primitives.ciphers",
            "cryptography.hazmat.primitives.ciphers.modes",
            "cryptography.hazmat.decrepit",
            "cryptography.hazmat.decrepit.ciphers",
            "cryptography.hazmat.decrepit.ciphers.modes",
        ):
            sys.modules.setdefault(name, ModuleType(name))
        ciphers = sys.modules["cryptography.hazmat.primitives.ciphers"]
        ciphers.Cipher = object
        ciphers.algorithms = object()
        sys.modules["cryptography.hazmat.decrepit.ciphers.modes"].CFB = object


_install_transport_stubs()

from custom_components.ecoflow_powerpulse2.api import (  # noqa: E402
    PowerPulse2ApiClient,
)
from custom_components.ecoflow_powerpulse2.auth_classification import (  # noqa: E402
    PowerPulse2AuthError,
    PowerPulse2ConnectionError,
)
from custom_components.ecoflow_powerpulse2.ecoflow.enhanced_auth import (  # noqa: E402
    enhanced_login,
)

ACCEPTED = {"code": "0", "data": {"token": "jwt", "user": {"userId": "42"}}}
REJECTED = {"code": "6042", "message": "invalid password"}
EMAIL = "user@example.invalid"


class _Response:
    def __init__(self, status: int, body: Any, json_error: Exception | None = None):
        self.status = status
        self._body = body
        self._json_error = json_error

    async def json(self, content_type: str | None = "application/json") -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._body


class _Attempt:
    """One queued answer: a response, or an exception raised by the request."""

    def __init__(self, answer: _Response | Exception) -> None:
        self._answer = answer

    async def __aenter__(self) -> _Response:
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class _Session:
    def __init__(self, *answers: _Response | Exception) -> None:
        self._answers = list(answers)
        self.urls: list[str] = []

    def _next(self, url: str) -> _Attempt:
        self.urls.append(url)
        assert self._answers, f"no queued answer for {url}"
        return _Attempt(self._answers.pop(0))

    def post(self, url: str, **_kwargs: Any) -> _Attempt:
        return self._next(url)

    def get(self, url: str, **_kwargs: Any) -> _Attempt:
        return self._next(url)


def _client(session: _Session) -> PowerPulse2ApiClient:
    return PowerPulse2ApiClient(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_login_returns_the_token_and_the_endpoint_that_accepted_it() -> None:
    session = _Session(_Response(200, ACCEPTED))
    result = await enhanced_login(session, EMAIL, "secret")
    assert result["token"] == "jwt"
    assert result["user_id"] == "42"
    assert result["base_url"].startswith("https://")
    assert len(session.urls) == 1


@pytest.mark.asyncio
async def test_rejection_by_every_endpoint_reports_a_credential_error() -> None:
    session = _Session(_Response(200, REJECTED), _Response(200, REJECTED))
    with pytest.raises(PowerPulse2AuthError):
        await enhanced_login(session, EMAIL, "wrong")
    assert len(session.urls) == 2


@pytest.mark.asyncio
async def test_outage_alongside_a_rejection_reports_a_connection_error() -> None:
    """The regional case: one host refuses, the other never answers.

    Reporting a credential error here would prompt for a password that may be
    perfectly correct for the region that stayed silent.
    """
    session = _Session(_Response(200, REJECTED), TimeoutError())
    with pytest.raises(PowerPulse2ConnectionError):
        await enhanced_login(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_refused_bearer_status_reports_a_credential_error() -> None:
    session = _Session(_Response(401, None), _Response(401, None))
    with pytest.raises(PowerPulse2AuthError):
        await enhanced_login(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_server_outage_never_reports_a_credential_error() -> None:
    session = _Session(_Response(503, None), _Response(500, "<html>"))
    with pytest.raises(PowerPulse2ConnectionError):
        await enhanced_login(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_accepted_login_without_a_token_is_a_connection_error() -> None:
    session = _Session(
        _Response(200, {"code": "0", "data": {"user": {"userId": "42"}}}),
        _Response(200, {"code": "0", "data": {}}),
    )
    with pytest.raises(PowerPulse2ConnectionError):
        await enhanced_login(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_unparsable_body_is_a_connection_error() -> None:
    session = _Session(
        _Response(200, None, json_error=ValueError("not json")),
        _Response(200, None, json_error=ValueError("not json")),
    )
    with pytest.raises(PowerPulse2ConnectionError):
        await enhanced_login(session, EMAIL, "secret")


@pytest.mark.asyncio
async def test_discovery_reports_a_refused_session_as_a_credential_error() -> None:
    client = _client(_Session(_Response(403, None)))
    with pytest.raises(PowerPulse2AuthError):
        await client.async_discover()


@pytest.mark.asyncio
async def test_refused_session_on_the_provider_path_stops_being_silent() -> None:
    """An expired token used to disable the provider path permanently.

    Every endpoint refusing the bearer token is an expired session, not the
    transient read failure the bounded fallback is allowed to swallow.
    """
    client = _client(_Session(_Response(401, None), _Response(401, None)))
    with pytest.raises(PowerPulse2AuthError):
        await client.async_read({"serial": "C376-test", "product_type": "CP307"})


@pytest.mark.asyncio
async def test_business_error_on_the_provider_path_yields_no_data() -> None:
    """A device-level error must not be mistaken for an expired session."""
    refused = _Response(200, {"code": "500", "message": "device not found"})
    client = _client(_Session(refused, refused))
    assert await client.async_read({"serial": "C376-test"}) == {}


@pytest.mark.asyncio
async def test_transient_read_failure_still_yields_no_data() -> None:
    client = _client(_Session(TimeoutError(), _Response(503, None)))
    assert await client.async_read({"serial": "C376-test"}) == {}
