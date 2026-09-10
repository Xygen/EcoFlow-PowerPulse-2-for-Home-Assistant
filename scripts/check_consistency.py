"""Offline repository checks; archive version mentions are intentionally ignored."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

COMPONENT = Path("custom_components/ecoflow_powerpulse2")
MARKDOWN = MarkdownIt("commonmark")


def leaf_keys(value: dict, prefix: str = "") -> set[str]:
    keys = set()
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        keys.update(leaf_keys(child, path) if isinstance(child, dict) else {path})
    return keys


def check_translations(root: Path) -> list[str]:
    canonical = leaf_keys(json.loads((root / COMPONENT / "strings.json").read_text(encoding="utf-8")))
    errors = []
    for path in sorted((root / COMPONENT / "translations").glob("*.json")):
        actual = leaf_keys(json.loads(path.read_text(encoding="utf-8")))
        for key in sorted(canonical - actual):
            errors.append(f"{path.relative_to(root)}: missing translation key {key}")
        for key in sorted(actual - canonical):
            errors.append(f"{path.relative_to(root)}: extra translation key {key}")
    return errors


def check_versions(root: Path, tag: str | None = None) -> list[str]:
    version = json.loads((root / COMPONENT / "manifest.json").read_text(encoding="utf-8"))["version"]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = re.findall(r"^## (\d+\.\d+\.\d+(?:-[\w.]+)?) - \d{4}-\d{2}-\d{2}$", changelog, re.M)
    errors = []
    if not releases or releases[0] != version:
        errors.append("CHANGELOG.md: newest dated release must match manifest version")
    stable = next((v for v in releases if "-" not in v), None)
    for name in ("README.md", "docs/index.md"):
        declared = re.findall(r"Current stable release: `([^`]+)`", (root / name).read_text(encoding="utf-8"))
        if declared != [stable]:
            errors.append(f"{name}: declare exactly one Current stable release: `{stable}`")
    if tag is not None and tag != f"v{version}":
        errors.append(f"Release tag {tag!r} does not match v{version}")
    return errors


def markdown_info(text: str) -> tuple[set[str], list[str]]:
    tokens = MARKDOWN.parse(text)
    anchors: set[str] = set()
    links = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            inline = tokens[index + 1]
            title = "".join(t.content for t in inline.children or [] if t.type in ("text", "code_inline", "image"))
            base = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
            slug, suffix = base, 0
            while slug in anchors:
                suffix += 1
                slug = f"{base}-{suffix}"
            anchors.add(slug)
        for child in token.children or []:
            if child.type in ("link_open", "image"):
                links.append(child.attrGet("href") if child.type == "link_open" else child.attrGet("src"))
        if token.type in ("html_block", "inline"):
            anchors.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', token.content))
    return anchors, links


def check_links(root: Path) -> list[str]:
    files = sorted(root.glob("*.md")) + sorted((root / "docs").rglob("*.md"))
    parsed = {p.resolve(): markdown_info(p.read_text(encoding="utf-8")) for p in files}
    errors = []
    for path in files:
        for link in parsed[path.resolve()][1]:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (root / unquote(url.path).lstrip("/") if url.path.startswith("/")
                      else path.parent / unquote(url.path)) if url.path else path
            target = target.resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():
                errors.append(f"{path.relative_to(root)}: missing local target {link}")
            elif url.fragment and target.suffix.lower() == ".md":
                if target not in parsed:
                    parsed[target] = markdown_info(target.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in parsed[target][0]:
                    errors.append(f"{path.relative_to(root)}: missing heading {link}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tag = os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None
    errors = check_versions(root, tag) + check_translations(root) + check_links(root)
    print("\n".join(errors) if errors else "Version, translation and local Markdown checks passed.")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
