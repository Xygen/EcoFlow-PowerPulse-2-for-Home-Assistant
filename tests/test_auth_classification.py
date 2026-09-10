"""Decision tests for EcoFlow authentication classification."""

from __future__ import annotations

import pytest

from custom_components.ecoflow_powerpulse2.auth_classification import (
    AuthOutcome,
    PowerPulse2AuthError,
    PowerPulse2ConnectionError,
    aggregate_outcomes,
    classify_credential_response,
    classify_data_response,
    classify_login_response,
    describe_response,
    raise_for_outcome,
)

ACCEPTED = {"code": "0", "data": {"token": "jwt", "user": {"userId": "42"}}}


def test_accepted_login_reports_success() -> None:
    assert classify_login_response(200, ACCEPTED) is AuthOutcome.SUCCESS


@pytest.mark.parametrize("status", [401, 403])
def test_rejecting_status_is_credential_evidence(status: int) -> None:
    assert classify_credential_response(status, None) is AuthOutcome.AUTH_FAILURE
    assert classify_data_response(status, None) is AuthOutcome.AUTH_FAILURE


@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503])
def test_temporary_status_never_blames_the_credentials(status: int) -> None:
    # A readable body must not promote a server-side outage to a rejection.
    assert (
        classify_credential_response(status, {"code": "1", "message": "nope"})
        is AuthOutcome.CONNECTION_FAILURE
    )


@pytest.mark.parametrize("status", [301, 400, 404, 418])
def test_unexplained_status_is_retried_not_blamed(status: int) -> None:
    assert classify_credential_response(status, None) is AuthOutcome.CONNECTION_FAILURE


def test_credential_endpoint_treats_application_code_as_rejection() -> None:
    outcome = classify_credential_response(200, {"code": "6042", "message": "bad"})
    assert outcome is AuthOutcome.AUTH_FAILURE


def test_data_endpoint_treats_application_code_as_missing_data() -> None:
    """A business error from a data endpoint is not evidence about the session.

    Device list and device detail answer with the same envelope as sign-in, so
    reading their non-zero codes as a credential problem would turn an unknown
    or offline device into a password prompt.
    """
    outcome = classify_data_response(200, {"code": "500", "message": "no device"})
    assert outcome is AuthOutcome.CONNECTION_FAILURE


@pytest.mark.parametrize("body", [None, "not json", [], {"data": {}}])
def test_unusable_body_is_a_transport_problem(body: object) -> None:
    assert classify_credential_response(200, body) is AuthOutcome.CONNECTION_FAILURE


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"token": "jwt"},
        {"token": "", "user": {"userId": "42"}},
        {"token": "jwt", "user": {}},
        {"token": "jwt", "user": "42"},
    ],
)
def test_accepted_login_without_usable_payload_is_not_a_rejection(data: dict) -> None:
    assert (
        classify_login_response(200, {"code": "0", "data": data})
        is AuthOutcome.CONNECTION_FAILURE
    )


def test_unanimous_rejection_is_the_only_reported_rejection() -> None:
    assert (
        aggregate_outcomes([AuthOutcome.AUTH_FAILURE, AuthOutcome.AUTH_FAILURE])
        is AuthOutcome.AUTH_FAILURE
    )


def test_one_silent_endpoint_defers_the_rejection() -> None:
    """One host declining while another never answered proves nothing.

    EcoFlow serves regions from different hosts, so this is the shape of a
    regional account meeting a partial outage. The rejection is reported on a
    later attempt, once every endpoint has answered.
    """
    assert (
        aggregate_outcomes([AuthOutcome.AUTH_FAILURE, AuthOutcome.CONNECTION_FAILURE])
        is AuthOutcome.CONNECTION_FAILURE
    )


def test_any_success_wins_and_no_attempt_is_not_a_rejection() -> None:
    assert (
        aggregate_outcomes([AuthOutcome.CONNECTION_FAILURE, AuthOutcome.SUCCESS])
        is AuthOutcome.SUCCESS
    )
    assert aggregate_outcomes([]) is AuthOutcome.CONNECTION_FAILURE


def test_description_reports_only_non_credential_fields() -> None:
    described = describe_response(200, {"code": "6042", "message": "bad", "data": "x"})
    assert described == "status=200 code=6042 msg=bad"
    assert describe_response(503, "<html>") == "status=503"


def test_outcome_raises_its_own_error_type() -> None:
    with pytest.raises(PowerPulse2AuthError):
        raise_for_outcome(AuthOutcome.AUTH_FAILURE, "rejected")
    with pytest.raises(PowerPulse2ConnectionError):
        raise_for_outcome(AuthOutcome.CONNECTION_FAILURE, "unreachable")
    raise_for_outcome(AuthOutcome.SUCCESS, "accepted")
