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


def _method(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is missing")


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
    assert "UpdateFailed" in _raised(_handler(renew, "PowerPulse2ConnectionError"))


def test_unreachable_endpoint_only_fails_the_cycle() -> None:
    handler = _handler(_method("_async_update_data"), "PowerPulse2ConnectionError")
    assert _raised(handler) == {"UpdateFailed"}


def test_renewal_is_rate_limited() -> None:
    """Without a floor, a repeatedly refused token means a sign-in per cycle."""
    renew = _method("_async_renew_session")
    names = {
        node.id for node in ast.walk(renew) if isinstance(node, ast.Name)
    }
    assert "SESSION_RENEWAL_INTERVAL_SECONDS" in names


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
