from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from custom_components.ecoflow_powerpulse2.smart_staging import (
    SMART_READY_BY_MAX_HORIZON_SECONDS,
    SmartDeadlineError,
    SmartStaging,
    SmartStagingError,
    validate_smart_activation,
    validate_smart_bundle,
)

ROOT = Path(__file__).parents[1]


def test_staged_energy_bundle_survives_reload_without_distance() -> None:
    staging = SmartStaging()

    assert staging.update(
        "C376-a",
        {
            "ready_by_timestamp": 1_788_000_000,
            "smart_target_type": "energy",
            "smart_charge_target_wh": 30_000,
        },
    )
    assert not staging.update("C376-a", {"smart_charge_target_wh": 30_000})
    validate_smart_bundle(staging.values("C376-a"))

    restored = SmartStaging()
    restored.load(staging.export())

    assert restored.values("C376-a") == staging.values("C376-a")
    assert restored.value("C376-a", "smart_target_distance_km") is None


def test_staged_distance_bundle_does_not_require_energy_target() -> None:
    staging = SmartStaging()
    staging.update(
        "C376-a",
        {
            "ready_by_timestamp": 1_788_000_000,
            "smart_target_type": "distance",
            "smart_target_distance_km": 200,
        },
    )

    validate_smart_bundle(staging.values("C376-a"))
    assert staging.value("C376-a", "smart_charge_target_wh") is None


def test_target_type_can_be_staged_before_its_target() -> None:
    staging = SmartStaging()
    staging.update("C376-a", {"smart_target_type": "energy"})

    with pytest.raises(SmartStagingError, match="ready-by time"):
        validate_smart_bundle(staging.values("C376-a"))

    staging.update("C376-a", {"ready_by_timestamp": 1_788_000_000})
    with pytest.raises(SmartStagingError, match="energy target"):
        validate_smart_bundle(staging.values("C376-a"))


def test_staging_is_isolated_per_serial() -> None:
    staging = SmartStaging()
    staging.update("C376-a", {"smart_charge_target_wh": 30_000})
    staging.update("C376-b", {"smart_target_distance_km": 200})

    assert staging.values("C376-a") == {"smart_charge_target_wh": 30_000}
    assert staging.values("C376-b") == {"smart_target_distance_km": 200}


def test_load_isolates_malformed_devices_and_fields() -> None:
    staging = SmartStaging()
    staging.load(
        {
            "devices": {
                "C376-good": {
                    "ready_by_timestamp": 1_788_000_000,
                    "smart_target_type": "energy",
                    "smart_charge_target_wh": 30_000,
                    "smart_target_distance_km": True,
                    "vehicle_consumption_raw": 150,
                },
                "C376-bad": "not-a-mapping",
                "C376-partial": {
                    "smart_target_type": "invalid",
                    "smart_target_distance_km": 300,
                },
            }
        }
    )

    assert staging.values("C376-good") == {
        "ready_by_timestamp": 1_788_000_000,
        "smart_target_type": "energy",
        "smart_charge_target_wh": 30_000,
    }
    assert staging.values("C376-bad") == {}
    assert staging.values("C376-partial") == {"smart_target_distance_km": 300}
    assert "vehicle_consumption_raw" not in str(staging.export())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ready_by_timestamp", True),
        ("smart_target_type", "automatic"),
        ("smart_charge_target_wh", 30_500),
        ("smart_charge_target_wh", 101_000),
        ("smart_target_distance_km", 9),
        ("smart_target_distance_km", 601),
        ("vehicle_consumption_raw", 150),
    ],
)
def test_invalid_user_owned_stage_values_are_rejected(key: str, value: object) -> None:
    staging = SmartStaging()

    with pytest.raises(SmartStagingError):
        staging.update("C376-a", {key: value})

    assert staging.values("C376-a") == {}


def test_observation_code_does_not_read_staged_smart_values() -> None:
    sensor_source = (
        ROOT / "custom_components/ecoflow_powerpulse2/sensor.py"
    ).read_text(encoding="utf-8")
    coordinator_source = (
        ROOT / "custom_components/ecoflow_powerpulse2/coordinator.py"
    ).read_text(encoding="utf-8")

    assert "staged_smart_setting" not in sensor_source
    assert "setting_observation_value" in sensor_source
    assert "Smart distance target requires vehicle consumption" not in coordinator_source
    assert 'calculated = 0 if target_type == "distance" else None' in coordinator_source
    assert "await self._async_update_smart_staging(serial, overrides)" in coordinator_source


# Central European winter and summer time, written as the fixed offsets they
# are. A named zone would pull in the IANA database and make these tests depend
# on a data package and on the EU not changing its mind about daylight saving.
# The offsets are what a local wall-clock time actually resolves to, which is
# the only part of the transition this rule can be affected by.
CET = timezone(timedelta(hours=1))
CEST = timezone(timedelta(hours=2))
NOW = 1_800_000_000  # 2027-01-15 08:00 UTC, a fixed clock for these tests.


def _bundle(ready_by: int) -> dict[str, int | str]:
    return {
        "ready_by_timestamp": ready_by,
        "smart_target_type": "energy",
        "smart_charge_target_wh": 30_000,
    }


def test_an_expired_draft_still_stores_and_survives_a_reload() -> None:
    """Keeping the draft is the point: only the hour usually needs changing."""
    staging = SmartStaging()
    assert staging.update("C376-a", _bundle(NOW - 86_400))

    restored = SmartStaging()
    restored.load(staging.export())

    assert restored.value("C376-a", "ready_by_timestamp") == NOW - 86_400
    # The bundle rule alone still accepts it; only activation adds the deadline.
    validate_smart_bundle(restored.values("C376-a"))


def test_activation_refuses_a_deadline_that_has_passed() -> None:
    with pytest.raises(SmartDeadlineError) as error:
        validate_smart_activation(_bundle(NOW - 1), now=NOW)
    assert error.value.translation_key == "smart_ready_by_expired"


def test_activation_refuses_a_deadline_at_exactly_now() -> None:
    """A deadline reached is a deadline gone; the publish would be too late."""
    with pytest.raises(SmartDeadlineError):
        validate_smart_activation(_bundle(NOW), now=NOW)


def test_activation_accepts_a_deadline_one_second_ahead() -> None:
    validate_smart_activation(_bundle(NOW + 1), now=NOW)


def test_activation_accepts_the_last_deadline_inside_the_horizon() -> None:
    validate_smart_activation(
        _bundle(NOW + SMART_READY_BY_MAX_HORIZON_SECONDS), now=NOW
    )


def test_activation_refuses_a_deadline_beyond_the_horizon() -> None:
    with pytest.raises(SmartDeadlineError) as error:
        validate_smart_activation(
            _bundle(NOW + SMART_READY_BY_MAX_HORIZON_SECONDS + 1), now=NOW
        )
    assert error.value.translation_key == "smart_ready_by_too_far_ahead"


def test_an_unformattable_timestamp_is_reported_rather_than_raising() -> None:
    """The error that reports an out-of-range value must not fail on it."""
    with pytest.raises(SmartDeadlineError) as error:
        validate_smart_activation(_bundle(10**18), now=NOW)
    assert error.value.translation_placeholders == {"ready_by": str(10**18)}


def test_the_expired_message_names_the_refused_time() -> None:
    """Naming the time is the difference between a refusal and a usable one."""
    refused = datetime(2026, 9, 1, 6, 30, tzinfo=UTC)

    with pytest.raises(SmartDeadlineError) as error:
        validate_smart_activation(_bundle(int(refused.timestamp())), now=NOW)

    assert error.value.translation_placeholders == {"ready_by": "2026-09-01 06:30 UTC"}


def test_an_incomplete_bundle_is_still_reported_as_incomplete() -> None:
    """The deadline rule must not mask a missing target."""
    with pytest.raises(SmartStagingError, match="target type"):
        validate_smart_activation({"ready_by_timestamp": NOW + 3_600}, now=NOW)


def test_the_same_instant_written_two_ways_gives_one_verdict() -> None:
    """Local time is a way of writing an instant, not a different instant."""
    as_utc = datetime(2027, 1, 15, 9, 0, tzinfo=UTC)
    as_local = datetime(2027, 1, 15, 10, 0, tzinfo=CET)

    assert int(as_utc.timestamp()) == int(as_local.timestamp())
    validate_smart_activation(_bundle(int(as_local.timestamp())), now=NOW)


def test_a_deadline_across_the_spring_forward_night_uses_absolute_time() -> None:
    """Ten hours on the wall clock, nine in fact. The rule counts the nine.

    Set on the Saturday evening for the Sunday morning, across the night the
    clocks go forward. A deadline compared on wall-clock arithmetic would be an
    hour out; compared on timestamps it is simply correct.
    """
    evening = datetime(2027, 3, 27, 22, 0, tzinfo=CET)
    morning = datetime(2027, 3, 28, 8, 0, tzinfo=CEST)
    now = int(evening.timestamp())
    ready_by = int(morning.timestamp())

    assert morning.hour - evening.hour + 24 == 10  # ten hours on the clock face
    assert ready_by - now == 9 * 3_600  # nine hours of real time
    validate_smart_activation(_bundle(ready_by), now=now)


def test_the_repeated_autumn_hour_is_two_different_deadlines() -> None:
    """02:30 happens twice that night, and only the second one is still ahead.

    The hour before the clocks go back and the hour after carry the same wall
    time and different offsets. Between them, one of the two deadlines has
    passed and the other has not, which a wall-clock comparison cannot express
    at all.
    """
    first = datetime(2027, 10, 31, 2, 30, tzinfo=CEST)
    second = datetime(2027, 10, 31, 2, 30, tzinfo=CET)
    assert int(second.timestamp()) - int(first.timestamp()) == 3_600

    between = int(first.timestamp()) + 1_800
    with pytest.raises(SmartDeadlineError):
        validate_smart_activation(_bundle(int(first.timestamp())), now=between)
    validate_smart_activation(_bundle(int(second.timestamp())), now=between)
