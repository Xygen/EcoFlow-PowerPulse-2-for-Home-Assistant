from __future__ import annotations

from datetime import UTC, datetime

from custom_components.ecoflow_powerpulse2.presentation import (
    as_timestamp,
    tenths_to_float,
    watt_hours_to_kwh,
)


def test_as_timestamp() -> None:
    assert as_timestamp(1_787_528_301) == datetime(2026, 8, 23, 23, 38, 21, tzinfo=UTC)
    assert as_timestamp(0) is None


def test_tenths_to_float() -> None:
    assert tenths_to_float(160) == 16.0
    assert tenths_to_float(65) == 6.5
    assert tenths_to_float(None) is None


def test_watt_hours_to_kwh() -> None:
    assert watt_hours_to_kwh(1815) == 1.815
    assert watt_hours_to_kwh(451) == 0.451
    assert watt_hours_to_kwh(1_364_918) == 1364.918
    assert watt_hours_to_kwh(None) is None
    assert watt_hours_to_kwh(-1) is None
