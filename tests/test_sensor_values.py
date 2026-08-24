from __future__ import annotations

from datetime import UTC, datetime

from custom_components.ecoflow_powerpulse2.presentation import (
    as_timestamp,
    format_duration,
    tenths_to_float,
)


def test_format_duration() -> None:
    assert format_duration(0) == "0 s"
    assert format_duration(42) == "42 s"
    assert format_duration(720) == "12 min"
    assert format_duration(725) == "12 min 05 s"
    assert format_duration(4_080) == "1 h 08 min"
    assert format_duration(183_600) == "2 d 03 h"


def test_as_timestamp() -> None:
    assert as_timestamp(1_787_528_301) == datetime(2026, 8, 23, 23, 38, 21, tzinfo=UTC)
    assert as_timestamp(0) is None


def test_tenths_to_float() -> None:
    assert tenths_to_float(160) == 16.0
    assert tenths_to_float(65) == 6.5
    assert tenths_to_float(None) is None
