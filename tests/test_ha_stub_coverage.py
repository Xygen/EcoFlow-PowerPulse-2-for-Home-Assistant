"""The coordinator harness must stub everything the coordinator imports.

Home Assistant is not installed in this test environment, so the transaction
harness replaces the modules the coordinator imports from. When the coordinator
gains an import the harness does not name, every test using that harness fails
with an ImportError that says nothing about the cause.

Worse, it fails only where both files meet. A branch that adds the import and a
branch that adds the harness each pass on their own, and the breakage appears
at the merge, which is where it is most expensive and least expected. That
happened three times while stage 1 and stage 2 of V2-AUTH-01 and the stream
diagnostics were merged.

This checks the two against each other directly, so the gap shows up on
whichever branch opens it, named for what is missing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
COORDINATOR = ROOT / "custom_components/ecoflow_powerpulse2/coordinator.py"
HARNESS = ROOT / "tests/test_coordinator_transactions.py"


def _imported_names() -> dict[str, set[str]]:
    """Return the Home Assistant names the coordinator imports, by module."""
    imported: dict[str, set[str]] = {}
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "homeassistant"
        ):
            names = imported.setdefault(node.module or "", set())
            names.update(alias.name for alias in node.names)
    return imported


def _stubbed_names() -> dict[str, set[str]]:
    """Return the names the harness provides, by module.

    The harness builds each stub with a local ``module(name, **attributes)``
    helper, so the call sites carry the whole contract.
    """
    stubbed: dict[str, set[str]] = {}
    tree = ast.parse(HARNESS.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Name)
            or node.func.id != "module"
            or not node.args
            or not isinstance(node.args[0], ast.Constant)
        ):
            continue
        name = node.args[0].value
        if not isinstance(name, str) or not name.startswith("homeassistant"):
            continue
        stubbed.setdefault(name, set()).update(
            keyword.arg for keyword in node.keywords if keyword.arg
        )
    return stubbed


def test_the_harness_is_still_the_right_shape() -> None:
    """Guard the two assumptions the checks below rest on."""
    assert _imported_names(), "no Home Assistant imports found in the coordinator"
    assert _stubbed_names(), "no module() stubs found in the harness"


@pytest.mark.parametrize("module", sorted(_imported_names()))
def test_every_imported_module_is_stubbed(module: str) -> None:
    assert module in _stubbed_names(), (
        f"{module} is imported by the coordinator but the transaction harness "
        f"does not stub it"
    )


@pytest.mark.parametrize(
    ("module", "name"),
    sorted(
        (module, name)
        for module, names in _imported_names().items()
        for name in names
    ),
)
def test_every_imported_name_is_stubbed(module: str, name: str) -> None:
    provided = _stubbed_names().get(module, set())
    assert name in provided, (
        f"the coordinator imports {name} from {module}, which the transaction "
        f"harness stubs without it"
    )
