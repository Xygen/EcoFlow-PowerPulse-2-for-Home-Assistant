"""Structural contract of the coordinator's authentication recovery.

Home Assistant is not a test dependency, so the coordinator cannot be
instantiated here and the runtime behaviour is established by the live test
recorded in the validation document. What this file pins down are the
invariants that decide whether the user is troubled at all: a refused request
must first be retried with the stored credentials, only a refused sign-in may
open the repair dialog, and the retry must be rate limited.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
COORDINATOR = ROOT / "custom_components/ecoflow_powerpulse2/coordinator.py"


def _method(name: str) -> ast.AsyncFunctionDef | ast.FunctionDef:
    """Return one method, async or not. A transport callback cannot be async."""
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
            and node.name == name
        ):
            return node
    raise AssertionError(f"{name} is missing")


def _attribute_names(tree: ast.AST) -> set[str]:
    """Return every attribute mentioned, called or handed on as a value."""
    return {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }


def _handlers(
    method: ast.AsyncFunctionDef, exception: str
) -> list[ast.ExceptHandler]:
    """Return every handler for one exception, innermost order not assumed."""
    found: list[ast.ExceptHandler] = []
    for node in ast.walk(method):
        if not isinstance(node, ast.ExceptHandler):
            continue
        names: list[str] = []
        if isinstance(node.type, ast.Name):
            names = [node.type.id]
        elif isinstance(node.type, ast.Tuple):
            names = [e.id for e in node.type.elts if isinstance(e, ast.Name)]
        if exception in names:
            found.append(node)
    assert found, f"no handler for {exception}"
    return found


def _handler(method: ast.AsyncFunctionDef, exception: str) -> ast.ExceptHandler:
    handlers = _handlers(method, exception)
    assert len(handlers) == 1, f"expected one handler for {exception}"
    return handlers[0]


def _raised(tree: ast.AST) -> set[str]:
    raised: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            func = node.exc.func
            if isinstance(func, ast.Name):
                raised.add(func.id)
            elif isinstance(func, ast.Attribute):
                raised.add(func.attr)
    return raised


def _is_truthy(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and bool(node.value)


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def test_refused_request_is_renewed_before_the_user_is_asked() -> None:
    handlers = _handlers(_method("_async_update_data"), "PowerPulse2AuthError")
    assert any("_async_renew_session" in _called_names(h) for h in handlers)


def test_update_cycle_never_opens_the_dialog_on_its_own() -> None:
    """Only a refused sign-in is evidence the user has to act on.

    An expired token reaches the same handler, and prompting for a password
    that still works would be a false alarm.
    """
    assert "ConfigEntryAuthFailed" not in _raised(_method("_async_update_data"))


def test_only_a_refused_sign_in_opens_the_dialog() -> None:
    renew = _method("_async_renew_session")
    assert "ConfigEntryAuthFailed" in _raised(_handler(renew, "PowerPulse2AuthError"))
    assert "ConfigEntryAuthFailed" not in _raised(_method("_async_sign_in_again"))


def test_unreachable_sign_in_never_opens_the_dialog() -> None:
    """A re-login that failed on the network says nothing about the password."""
    handler = _handler(_method("_async_sign_in_again"), "PowerPulse2ConnectionError")
    assert not _raised(handler)
    assert any(
        isinstance(node, ast.Return) and not _is_truthy(node.value)
        for node in ast.walk(handler)
    )


def test_unreachable_endpoint_only_fails_the_cycle() -> None:
    handler = _handler(_method("_async_update_data"), "PowerPulse2ConnectionError")
    assert _raised(handler) == {"UpdateFailed"}


@pytest.mark.parametrize(
    ("method", "constant"),
    [
        ("_async_sign_in_again", "SESSION_RENEWAL_INTERVAL_SECONDS"),
        ("_async_refresh_mqtt_credentials", "CREDENTIAL_REFRESH_INTERVAL_SECONDS"),
    ],
)
def test_recovery_attempts_are_rate_limited(method: str, constant: str) -> None:
    """Without a floor, a repeated refusal means one request per cycle."""
    names = {
        node.id
        for node in ast.walk(_method(method))
        if isinstance(node, ast.Name)
    }
    assert constant in names


@pytest.mark.parametrize("name", ["_async_update_data", "_async_maintain_mqtt"])
def test_mqtt_setup_lets_a_refusal_through(name: str) -> None:
    """A refused credential cannot be retried into working by the watchdog.

    Both call sites wrap MQTT setup in a broad handler that downgrades any
    failure to a log line. A refusal has to escape that handler unchanged.
    """
    assert any(
        any(isinstance(node, ast.Raise) and node.exc is None for node in h.body)
        for h in _handlers(_method(name), "PowerPulse2AuthError")
    )


def test_setup_no_longer_reports_a_builtin_connection_error() -> None:
    """The builtin error carries no source, so it cannot be classified."""
    assert "ConnectionError" not in _raised(_method("_async_setup_mqtt"))


def _keywords(tree: ast.AST, call_name: str) -> set[str]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == call_name
        ):
            return {k.arg for k in node.keywords if k.arg}
    raise AssertionError(f"no call to {call_name}")


def test_mqtt_setup_consumes_the_expired_certificate_detection() -> None:
    """The transport has always detected this and logged a refresh.

    Nothing was listening, so that log line described work that never
    happened. Setup has to hand it a handler for the message to be true.
    """
    setup = _method("_async_setup_mqtt")
    assert "auth_error_handler" in _keywords(setup, "EcoFlowMQTTClient")


def test_mqtt_setup_dials_the_address_the_credentials_name() -> None:
    assert "update_broker" in _called_names(_method("_async_setup_mqtt"))


def test_the_transport_callback_hands_its_work_to_the_event_loop() -> None:
    """It runs on the paho network thread, where coordinator state is not safe
    to touch and a coroutine cannot be awaited."""
    assert "call_soon_threadsafe" in _called_names(_method("_on_mqtt_auth_error"))


def test_the_refresh_task_never_raises() -> None:
    """Both callers sit outside the update cycle error mapping, and one is a
    task started from the transport thread, where nothing would catch it."""
    assert _raised(_method("_async_refresh_mqtt_credentials")) == set()
    assert _raised(_method("_async_apply_mqtt_credentials")) == set()


def test_an_unchanged_certificate_keeps_the_session() -> None:
    """Rebuilding a healthy session costs a data gap for nothing."""
    apply = _method("_async_apply_mqtt_credentials")
    # Handed to an executor rather than called, so look for the reference.
    assert "force_reconnect" in _attribute_names(apply)
    guards = [
        node
        for node in ast.walk(apply)
        if isinstance(node, ast.If)
        and any(isinstance(inner, ast.Continue) for inner in node.body)
    ]
    assert len(guards) == 1, "no single early exit before the rebuild"
    tested = {
        node.id for node in ast.walk(guards[0].test) if isinstance(node, ast.Name)
    }
    # Both halves matter: a new address needs a rebuild even with the same
    # certificate, and a new certificate needs one even at the same address.
    assert "moved" in tested
    assert "previous_account" in tested
    assert "account" in tested
