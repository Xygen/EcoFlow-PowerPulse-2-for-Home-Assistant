from __future__ import annotations

from datetime import UTC, datetime

from custom_components.ecoflow_powerpulse2.diagnostic_support import (
    app_writes_watched,
    redact_serial_shaped_bytes,
    sanitize_diagnostics_export,
    stream_health,
)


def test_app_write_watch_requires_connection_and_both_subscriptions() -> None:
    accepted = {"app_set": 0, "app_set_reply": 0}
    assert app_writes_watched(True, accepted)
    assert not app_writes_watched(False, accepted)
    assert not app_writes_watched(True, {"app_set": 0})
    assert not app_writes_watched(True, {"app_set": 0, "app_set_reply": 1})


def test_stream_health_separates_connection_from_freshness() -> None:
    health = stream_health(
        connected=True,
        last_report="2026-08-31T10:00:00+00:00",
        fresh_seconds=10,
        now=datetime(2026, 8, 31, 10, 1, tzinfo=UTC),
    )
    assert health == {
        "connected": True,
        "last_report": "2026-08-31T10:00:00+00:00",
        "age_s": 60.0,
        "fresh": False,
        "fresh_seconds": 10,
    }


def test_recursive_privacy_guard_masks_values_and_distinct_dict_keys() -> None:
    export = {
        "C376KNOWN123": "C376KNOWN123",
        "C376UNKNOWN9": ["prefix C376UNKNOWN9 suffix"],
        "nested": {"owner": "user-42"},
        "redacted_hex": "433337364b4e4f574e313233",
        "runtime_fingerprint": "C376KNOWN123",
    }
    sanitized = sanitize_diagnostics_export(
        export, identifiers={"C376KNOWN123", "user-42"}
    )

    keys = list(sanitized)
    assert keys[0] != keys[1]
    assert sanitized[keys[0]] == "X" * len("C376KNOWN123")
    assert sanitized[keys[1]][0] == f"prefix {'X' * len('C376UNKNOWN9')} suffix"
    assert sanitized["nested"]["owner"] == "X" * len("user-42")
    assert sanitized["redacted_hex"] == "433337364b4e4f574e313233"
    assert sanitized["runtime_fingerprint"] == "C376KNOWN123"
    assert "C376KNOWN123" not in repr(
        {key: value for key, value in sanitized.items() if key != "runtime_fingerprint"}
    )


def test_byte_redaction_is_length_preserving_for_unknown_serial_shape() -> None:
    payload = b"before C376UNKNOWN9 after C376KNOWN123"
    redacted = redact_serial_shaped_bytes(payload, {"C376KNOWN123"})

    assert len(redacted) == len(payload)
    assert b"C376UNKNOWN9" not in redacted
    assert b"C376KNOWN123" not in redacted
    assert redacted.startswith(b"before ")
