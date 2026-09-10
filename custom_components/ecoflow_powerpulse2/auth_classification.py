"""Classify EcoFlow authentication outcomes from observed response evidence.

The transport modules used to collapse every failure into a single ``None``,
which made a wrong password indistinguishable from an unreachable endpoint.
This module holds the decision on its own so it can be tested without aiohttp,
Home Assistant or a network, and so both credential endpoints classify the
same evidence the same way.

The rule is deliberately asymmetric. Reporting a rejected credential starts a
Home Assistant repair flow and asks the user for a password, so it requires
positive evidence that the server received the request and refused it.
Anything else is treated as a transport problem and retried, because a
retry costs a coordinator cycle while a false prompt costs the user's trust.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any


class PowerPulse2AuthError(Exception):
    """EcoFlow received the request and rejected the stored credentials."""


class PowerPulse2ConnectionError(Exception):
    """EcoFlow was unreachable, or answered in a way that cannot be used."""


class AuthOutcome(Enum):
    """What one endpoint answer proves about the credentials."""

    SUCCESS = "success"
    AUTH_FAILURE = "auth_failure"
    CONNECTION_FAILURE = "connection_failure"


# A rejected bearer token or credential pair. The only statuses that are
# evidence of a credential problem on their own.
_AUTH_STATUSES = frozenset({401, 403})

# Explicitly temporary by definition of the status itself.
_RETRYABLE_STATUSES = frozenset({408, 425, 429})


def _classify_transport(status: int) -> AuthOutcome | None:
    """Decide from the HTTP status alone, or defer to the response body."""
    if status in _AUTH_STATUSES:
        return AuthOutcome.AUTH_FAILURE
    if status in _RETRYABLE_STATUSES or status >= 500:
        return AuthOutcome.CONNECTION_FAILURE
    if not 200 <= status < 300:
        # Any other non-success status is unexplained. Retrying is safe;
        # asking the user for a password on this evidence is not.
        return AuthOutcome.CONNECTION_FAILURE
    return None


def _application_code(body: Any) -> str | None:
    """Return EcoFlow's application-level result code, if the body carries one."""
    if not isinstance(body, Mapping):
        return None
    code = body.get("code")
    return None if code is None else str(code)


def classify_credential_response(status: int, body: Any) -> AuthOutcome:
    """Classify an answer from a credential endpoint.

    Sign-in and certification answer ``200`` with an application ``code``
    rather than a transport status, and for these two endpoints a non-zero
    code is the documented shape of a refused credential.
    """
    decided = _classify_transport(status)
    if decided is not None:
        return decided
    code = _application_code(body)
    if code is None:
        return AuthOutcome.CONNECTION_FAILURE
    if code != "0":
        return AuthOutcome.AUTH_FAILURE
    return AuthOutcome.SUCCESS


def classify_data_response(status: int, body: Any) -> AuthOutcome:
    """Classify an answer from a data endpoint.

    Device list and device detail reuse the same envelope, but their non-zero
    codes report business conditions — an unknown serial, an offline device,
    a temporarily unavailable record. Reading those as a credential problem
    would turn a missing device into a password prompt, so here only the
    transport statuses are evidence about the session, and everything else is
    simply an answer that carries no data.
    """
    decided = _classify_transport(status)
    if decided is not None:
        return decided
    if _application_code(body) != "0":
        return AuthOutcome.CONNECTION_FAILURE
    return AuthOutcome.SUCCESS


def classify_login_response(status: int, body: Any) -> AuthOutcome:
    """Classify a login answer, including its payload completeness.

    A success that carries no token or user id is unexpected server behaviour,
    not proof of a wrong password, so it is reported as a transport problem.
    """
    outcome = classify_credential_response(status, body)
    if outcome is not AuthOutcome.SUCCESS:
        return outcome
    data = body.get("data") if isinstance(body, Mapping) else None
    if not isinstance(data, Mapping):
        return AuthOutcome.CONNECTION_FAILURE
    user = data.get("user")
    user_id = user.get("userId") if isinstance(user, Mapping) else None
    if not data.get("token") or not user_id:
        return AuthOutcome.CONNECTION_FAILURE
    return AuthOutcome.SUCCESS


def aggregate_outcomes(outcomes: Sequence[AuthOutcome]) -> AuthOutcome:
    """Reduce the per-endpoint outcomes of one attempt to a single decision.

    A rejection counts only when every attempted endpoint rejected. EcoFlow
    serves regions from different hosts, so one host declining while another
    never answered is not evidence about the credentials: it is the shape of a
    regional account meeting a partial outage. Requiring unanimity means a
    genuinely wrong password is reported as soon as every endpoint is
    reachable, and never before.
    """
    if not outcomes:
        return AuthOutcome.CONNECTION_FAILURE
    if AuthOutcome.SUCCESS in outcomes:
        return AuthOutcome.SUCCESS
    if all(outcome is AuthOutcome.AUTH_FAILURE for outcome in outcomes):
        return AuthOutcome.AUTH_FAILURE
    return AuthOutcome.CONNECTION_FAILURE


def describe_response(status: int, body: Any) -> str:
    """Return a log-safe reason built only from non-credential fields."""
    if not isinstance(body, Mapping):
        return f"status={status}"
    code = body.get("code")
    message = body.get("message")
    parts = [f"status={status}"]
    if code is not None:
        parts.append(f"code={code}")
    if isinstance(message, str) and message:
        parts.append(f"msg={message}")
    return " ".join(parts)


def raise_for_outcome(outcome: AuthOutcome, reason: str) -> None:
    """Raise the typed error matching a non-success outcome."""
    if outcome is AuthOutcome.AUTH_FAILURE:
        raise PowerPulse2AuthError(reason)
    if outcome is AuthOutcome.CONNECTION_FAILURE:
        raise PowerPulse2ConnectionError(reason)
