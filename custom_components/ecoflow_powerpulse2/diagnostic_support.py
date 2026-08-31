"""Pure, bounded helpers for privacy-safe diagnostic exports."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

_SERIAL_TEXT_RE = re.compile(r"(?<![A-Z0-9])[A-Z][A-Z0-9]{9,23}(?![A-Z0-9])")
_SERIAL_BYTES_RE = re.compile(rb"(?<![A-Z0-9])[A-Z][A-Z0-9]{9,23}(?![A-Z0-9])")
_PRESANITIZED_KEYS = frozenset({"redacted_hex", "runtime_fingerprint"})


def redact_serial_shaped_bytes(payload: bytes, identifiers: Iterable[str]) -> bytes:
    """Mask known and serial-shaped ASCII identifiers without changing length."""
    redacted = payload
    for identifier in identifiers:
        encoded = identifier.encode("ascii", errors="ignore")
        if encoded:
            redacted = redacted.replace(encoded, b"X" * len(encoded))

    def replace(match: re.Match[bytes]) -> bytes:
        value = match.group(0)
        if not any(65 <= byte <= 90 for byte in value) or not any(
            48 <= byte <= 57 for byte in value
        ):
            return value
        return b"X" * len(value)

    return _SERIAL_BYTES_RE.sub(replace, redacted)


def app_writes_watched(
    connected: bool, subscription_results: dict[str, int]
) -> bool:
    """Return true only when both official-app write paths are subscribed."""
    return bool(
        connected
        and subscription_results.get("app_set") == 0
        and subscription_results.get("app_set_reply") == 0
    )


def stream_health(
    *,
    connected: bool,
    last_report: str | None,
    fresh_seconds: int | float,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Describe transport and report freshness as separate facts."""
    age_s: float | None = None
    if last_report:
        try:
            reported = datetime.fromisoformat(last_report)
            if reported.tzinfo is None:
                reported = reported.replace(tzinfo=UTC)
            age_s = max(0.0, ((now or datetime.now(UTC)) - reported).total_seconds())
        except (TypeError, ValueError):
            age_s = None
    return {
        "connected": connected,
        "last_report": last_report,
        "age_s": round(age_s, 3) if age_s is not None else None,
        "fresh": age_s is not None and age_s <= fresh_seconds,
        "fresh_seconds": fresh_seconds,
    }


def sanitize_diagnostics_export(
    value: Any, *, identifiers: Iterable[str]
) -> Any:
    """Apply a final recursive privacy guard to keys and values."""
    known = tuple(sorted({item for item in identifiers if item}, key=len, reverse=True))
    aliases: dict[str, str] = {}

    def alias(identifier: str) -> str:
        if identifier not in aliases:
            aliases[identifier] = f"<redacted_identifier_{len(aliases) + 1}>"
        return aliases[identifier]

    def mask_text(text: str, *, key: str | None, is_key: bool = False) -> str:
        if key in _PRESANITIZED_KEYS:
            return text
        masked = text
        for identifier in known:
            replacement = alias(identifier) if is_key else "X" * len(identifier)
            masked = masked.replace(identifier, replacement)

        def replace(match: re.Match[str]) -> str:
            candidate = match.group(0)
            if not any(char.isalpha() for char in candidate) or not any(
                char.isdigit() for char in candidate
            ):
                return candidate
            return alias(candidate) if is_key else "X" * len(candidate)

        return _SERIAL_TEXT_RE.sub(replace, masked)

    def visit(item: Any, *, key: str | None = None) -> Any:
        if isinstance(item, dict):
            result: dict[Any, Any] = {}
            for raw_key, raw_value in item.items():
                safe_key = (
                    mask_text(raw_key, key=None, is_key=True)
                    if isinstance(raw_key, str)
                    else raw_key
                )
                result[safe_key] = visit(raw_value, key=str(raw_key))
            return result
        if isinstance(item, list):
            return [visit(child, key=key) for child in item]
        if isinstance(item, tuple):
            return [visit(child, key=key) for child in item]
        if isinstance(item, str):
            return mask_text(item, key=key)
        if isinstance(item, bytes):
            return f"<bytes_omitted:{len(item)}>"
        return item

    return visit(value)
