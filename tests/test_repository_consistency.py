import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_consistency import (
    COMPONENT,
    check_links,
    check_translations,
    check_versions,
    markdown_info,
)


@pytest.fixture
def repository(tmp_path):
    (tmp_path / COMPONENT / "translations").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / COMPONENT / "manifest.json").write_text('{"version":"1.0.5-beta.1"}')
    (tmp_path / "CHANGELOG.md").write_text("## Unreleased\n\n## 1.0.5-beta.1 - 2026-09-10\n\n## 1.0.4 - 2026-09-07\n")
    for name in ("README.md", "docs/index.md"):
        (tmp_path / name).write_text("Current stable release: `1.0.4`.\nHistorical release: 0.1.0.\n")
    for name in ("strings.json", "translations/en.json", "translations/de.json"):
        (tmp_path / COMPONENT / name).write_text('{"entity":{"sensor":{"name":"Example"}}}')
    return tmp_path


def test_current_versions_allow_beta_and_historical_mentions(repository):
    assert not check_versions(repository, "v1.0.5-beta.1")
    assert check_versions(repository, "v1.0.4")


@pytest.mark.parametrize("file", ["README.md", "docs/index.md", "CHANGELOG.md"])
def test_inconsistent_current_version_fails(repository, file):
    path = repository / file
    path.write_text(path.read_text().replace("1.0.5-beta.1" if file == "CHANGELOG.md" else "1.0.4", "1.0.0"))
    assert check_versions(repository)


def test_translation_parity_detects_missing_and_extra_keys(repository):
    assert not check_translations(repository)
    (repository / COMPONENT / "translations/de.json").write_text(json.dumps({"extra": "value"}))
    errors = check_translations(repository)
    assert any("missing translation key entity.sensor.name" in error for error in errors)
    assert any("extra translation key extra" in error for error in errors)


def test_markdown_links_reference_links_images_and_anchors(repository):
    (repository / "docs/page.md").write_text("# Heading\n\n# Heading\n\n<a id=\"explicit\"></a>\n")
    (repository / "README.md").write_text(
        "[valid](docs/page.md#heading-1)\n\n[reference][r]\n\n[r]: docs/page.md#explicit\n"
        "\n![missing](missing.png)\n\n[bad](docs/page.md#absent)\n"
        "\n```md\n[ignored](also-missing.md)\n```\n"
        "\n`[ignored](inline-missing.md)`\n[external](https://example.com/no-check)\n"
    )
    errors = check_links(repository)
    assert len(errors) == 2
    assert any("missing.png" in error for error in errors)
    assert any("#absent" in error for error in errors)


def test_heading_slugs_and_percent_encoded_links(repository):
    (repository / "docs/a b.md").write_text("# Über **Strom** und `Werte`!\n", encoding="utf-8")
    (repository / "README.md").write_text("[ok](docs/a%20b.md#%C3%BCber-strom-und-werte)")
    assert not check_links(repository)
    assert markdown_info("# Same\n# Same\n# Same\n")[0] == {"same", "same-1", "same-2"}


def test_quality_commands_reject_deliberate_failures(tmp_path):
    bad_test = tmp_path / "test_failure.py"
    bad_test.write_text("def test_failure():\n    assert False\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(bad_test)], cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "1 failed" in result.stdout
    bad_code = tmp_path / "bad_code.py"
    bad_code.write_text("print(undefined_name)\n")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated", "--select", "F821", str(bad_code)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "F821" in result.stdout


def _caught_exception_names(node: ast.expr | None) -> set[str]:
    """Return the exception class names from one except clause."""
    if isinstance(node, (ast.Name, ast.Attribute)):
        return {node.id if isinstance(node, ast.Name) else node.attr}
    if isinstance(node, ast.Tuple):
        return set().union(*(_caught_exception_names(item) for item in node.elts))
    return set()


def _scan_raised_translation_keys(
    tree: ast.AST, where: str
) -> tuple[dict[str, str], list[str]]:
    """Scan translated errors and reject unsupported key expressions.

    A key must be an inline string literal. The sole dynamic form allowed is
    ``exc.translation_key`` inside an ``except SmartDeadlineError as exc``
    handler, because that forwards a key whose literal constructors are also
    scanned. Names, calls, interpolations and all other attributes are errors.
    """
    forwarded_attributes: set[int] = set()
    for handler in (node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)):
        if (
            isinstance(handler.name, str)
            and "SmartDeadlineError" in _caught_exception_names(handler.type)
        ):
            forwarded_attributes.update(
                id(node)
                for node in ast.walk(handler)
                if isinstance(node, ast.Attribute)
                and node.attr == "translation_key"
                and isinstance(node.value, ast.Name)
                and node.value.id == handler.name
            )

    raised: dict[str, str] = {}
    unsupported: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else getattr(node.func, "id", "")
        )
        if not name.endswith("Error"):
            continue
        for keyword in node.keywords:
            if keyword.arg != "translation_key":
                continue
            if isinstance(keyword.value, ast.Constant) and isinstance(
                keyword.value.value, str
            ):
                raised[keyword.value.value] = where
            elif id(keyword.value) not in forwarded_attributes:
                unsupported.append(
                    f"{where}:{keyword.value.lineno}: {ast.unparse(keyword.value)}"
                )
    return raised, unsupported


def test_module_constant_translation_key_is_rejected() -> None:
    """A missing key hidden behind a module constant must not pass the scan."""
    tree = ast.parse(
        'MISSING = "not_declared"\n'
        "raise HomeAssistantError(translation_key=MISSING)\n"
    )

    raised, unsupported = _scan_raised_translation_keys(tree, "broken.py")

    assert raised == {}
    assert unsupported == ["broken.py:2: MISSING"]


def test_every_raised_translation_key_exists_under_exceptions() -> None:
    """A translated error with no entry shows the user the key, not a message.

    `check_translations` keeps `strings.json` and the language files in step
    with each other, and nothing keeps the code in step with `strings.json`.
    A key raised but never declared fails silently, in the one place where the
    user is already being told something went wrong.
    """
    root = Path(__file__).parents[1]
    component = root / COMPONENT
    declared = set(
        json.loads((component / "strings.json").read_text(encoding="utf-8"))
        .get("exceptions", {})
    )

    raised: dict[str, str] = {}
    unsupported: list[str] = []
    for path in sorted(component.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found, invalid = _scan_raised_translation_keys(
            tree, str(path.relative_to(root))
        )
        raised.update(found)
        unsupported.extend(invalid)

    assert raised, "the scan found no translated exceptions, so it proves nothing"
    assert not unsupported, f"unsupported translation_key expressions: {unsupported}"
    missing = {key: where for key, where in raised.items() if key not in declared}
    assert not missing, f"translation keys raised but not declared: {missing}"
