"""Structural contract of the config flow's authentication steps.

Home Assistant is not a test dependency here, so the flow's runtime behaviour
is not exercised; that remains a live acceptance step, and closing the gap is
roadmap item ``V2-QA-02``. What this file does check is the part that silently
breaks without any error: a step, error or abort key the flow names but no
translation defines, and a repair path that replaces the config entry instead
of updating it.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components/ecoflow_powerpulse2"
FLOW = COMPONENT / "config_flow.py"

REPAIR_STEPS = ("async_step_reauth_confirm", "async_step_reconfigure")


def _module() -> ast.Module:
    return ast.parse(FLOW.read_text(encoding="utf-8"))


def _flow_class() -> ast.ClassDef:
    for node in _module().body:
        if isinstance(node, ast.ClassDef) and node.name == "PowerPulse2ConfigFlow":
            return node
    raise AssertionError("PowerPulse2ConfigFlow is missing")


def _method(name: str) -> ast.AsyncFunctionDef:
    for node in _flow_class().body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is missing")


def _keyword_literals(tree: ast.AST, keyword: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for item in node.keywords:
            if item.arg == keyword and isinstance(item.value, ast.Constant):
                if isinstance(item.value.value, str):
                    found.add(item.value.value)
    return found


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _strings(section: str) -> set[str]:
    data = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    return set(data["config"][section])


@pytest.mark.parametrize(
    "name",
    [
        "async_step_user",
        "async_step_reauth",
        "async_step_reauth_confirm",
        "async_step_reconfigure",
    ],
)
def test_flow_offers_setup_and_both_repair_paths(name: str) -> None:
    assert _method(name)


def test_every_named_step_has_a_translation() -> None:
    assert _keyword_literals(_flow_class(), "step_id") <= _strings("step")


def test_every_named_abort_reason_has_a_translation() -> None:
    assert _keyword_literals(_flow_class(), "reason") <= _strings("abort")


def test_every_reported_error_key_has_a_translation() -> None:
    check = _method("_async_check_credentials")
    reported = {
        node.value.elts[0].value
        for node in ast.walk(check)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Tuple)
        and node.value.elts
        and isinstance(node.value.elts[0], ast.Constant)
        and node.value.elts[0].value
    }
    assert reported, "the credential check reports no error keys at all"
    assert "invalid_auth" in reported
    assert "cannot_connect" in reported
    assert reported <= _strings("error")


def test_credential_check_separates_the_two_failure_kinds() -> None:
    """A refused credential and an unreachable endpoint must not share a key."""
    check = _method("_async_check_credentials")
    handled = {
        handler.type.id
        for handler in ast.walk(check)
        if isinstance(handler, ast.ExceptHandler) and isinstance(handler.type, ast.Name)
    }
    assert {"PowerPulse2AuthError", "PowerPulse2ConnectionError"} <= handled


@pytest.mark.parametrize("name", REPAIR_STEPS)
def test_repair_updates_the_entry_instead_of_replacing_it(name: str) -> None:
    """Replacing the entry would discard entity IDs, history and Smart drafts."""
    called = _called_names(_method(name))
    assert "async_update_reload_and_abort" in called
    assert "async_create_entry" not in called


@pytest.mark.parametrize("name", REPAIR_STEPS)
def test_repair_refuses_a_different_account(name: str) -> None:
    """New credentials for another account would orphan every entity."""
    assert "_abort_if_unique_id_mismatch" in _called_names(_method(name))
    assert "wrong_account" in _keyword_literals(_method(name), "reason")
