"""Validated, serial-scoped staging for Smart charging configuration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, NamedTuple

# A charging deadline further ahead than this is not a plan, it is a mistyped
# year. The bound is a chosen guard rather than an observed device limit: the
# protocol carries the deadline as a varint and no upper limit has been read
# off the charger. It is deliberately generous, because rejecting a deadline a
# user meant costs more than accepting an odd one.
SMART_READY_BY_MAX_HORIZON_SECONDS = 366 * 24 * 60 * 60

STAGED_SMART_KEYS = frozenset(
    {
        "ready_by_timestamp",
        "smart_target_type",
        "smart_charge_target_wh",
        "smart_target_distance_km",
    }
)


class SmartStagingError(ValueError):
    """A staged Smart value is invalid."""


class SmartDeadlineError(SmartStagingError):
    """A stored Smart deadline cannot be activated as it stands.

    Distinct from the other staging errors because the user can act on it and
    the message reaches them translated. The deadline itself is carried so the
    message can name the time that was refused, which is the difference between
    "that did not work" and knowing which value to change.
    """

    def __init__(self, message: str, *, translation_key: str, ready_by: int) -> None:
        super().__init__(message)
        self.translation_key = translation_key
        self.ready_by = ready_by

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Render the refused deadline, falling back to the raw seconds."""
        try:
            stamp = datetime.fromtimestamp(self.ready_by, UTC)
        except (OSError, OverflowError, ValueError):
            # Out-of-range values are exactly what this error reports, so
            # formatting one must not raise on top of it.
            return {"ready_by": str(self.ready_by)}
        return {"ready_by": stamp.strftime("%Y-%m-%d %H:%M UTC")}


def _validated_value(key: str, value: Any) -> int | str:
    """Validate one user-owned staged value without coercing its type."""
    if key == "ready_by_timestamp":
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SmartStagingError("Smart ready-by time must be a valid timestamp")
        return value
    if key == "smart_target_type":
        if value not in ("energy", "distance"):
            raise SmartStagingError("Smart target type must be energy or distance")
        return value
    if key == "smart_charge_target_wh":
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 1_000 <= value <= 100_000
            or value % 1_000
        ):
            raise SmartStagingError(
                "Smart energy target must be 1 to 100 whole kWh"
            )
        return value
    if key == "smart_target_distance_km":
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 10 <= value <= 600
        ):
            raise SmartStagingError(
                "Smart distance target must be 10 to 600 whole km"
            )
        return value
    raise SmartStagingError(f"Unsupported staged Smart setting: {key}")


class DeviceReportResult(NamedTuple):
    """What a device report changed, and what could not be used from it."""

    changed: bool
    skipped: tuple[str, ...]


class SmartStaging:
    """Hold validated Smart configuration drafts independently per serial."""

    def __init__(self) -> None:
        self._devices: dict[str, dict[str, int | str]] = {}

    def load(self, stored: Any) -> None:
        """Load valid fields while isolating malformed devices and values."""
        self._devices = {}
        if not isinstance(stored, Mapping):
            return
        devices = stored.get("devices")
        if not isinstance(devices, Mapping):
            return
        for serial, values in devices.items():
            if not isinstance(serial, str) or not serial or not isinstance(values, Mapping):
                continue
            validated: dict[str, int | str] = {}
            for key in STAGED_SMART_KEYS:
                if key not in values:
                    continue
                try:
                    validated[key] = _validated_value(key, values[key])
                except SmartStagingError:
                    continue
            if validated:
                self._devices[serial] = validated

    def update(self, serial: str, changes: Mapping[str, Any]) -> bool:
        """Apply validated user changes and report whether state changed.

        All or nothing, because a user submitting one bad value should be told
        so rather than have part of their edit applied. Device reports need the
        opposite and use `update_from_device`.
        """
        self._require_serial(serial)
        validated = {
            key: _validated_value(key, value) for key, value in changes.items()
        }
        return self._apply(serial, validated)

    def update_from_device(
        self, serial: str, report: Mapping[str, Any]
    ) -> DeviceReportResult:
        """Stage what a device report does carry, skipping what it cannot.

        A device report is not user input and the two cannot share a rule. The
        charger legitimately reports an energy target of zero while a distance
        target is selected — the protocol carries the calculated energy in that
        field instead — and zero is not a target a user may enter. Refusing the
        whole report on that basis would discard the ready-by time, the target
        type and the distance reported alongside it, and the draft would quietly
        stop tracking the device.

        So each field is judged on its own, exactly as `load` already judges a
        stored record. A field that cannot be used leaves the stored draft as it
        was, which is the right outcome for the unused half of a target pair:
        the user's own energy figure survives a distance-target session.
        """
        self._require_serial(serial)
        validated: dict[str, int | str] = {}
        skipped: list[str] = []
        for key, value in report.items():
            try:
                validated[key] = _validated_value(key, value)
            except SmartStagingError:
                skipped.append(key)
        return DeviceReportResult(
            self._apply(serial, validated), tuple(skipped)
        )

    @staticmethod
    def _require_serial(serial: str) -> None:
        if not isinstance(serial, str) or not serial:
            raise SmartStagingError("Smart staging requires a device serial")

    def _apply(self, serial: str, validated: dict[str, int | str]) -> bool:
        """Merge already-validated values, reporting whether anything moved."""
        current = dict(self._devices.get(serial, {}))
        updated = dict(current)
        updated.update(validated)
        if updated == current:
            return False
        self._devices[serial] = updated
        return True

    def values(self, serial: str) -> dict[str, int | str]:
        """Return a copy of one serial's staged draft."""
        return dict(self._devices.get(serial, {}))

    def value(self, serial: str, key: str) -> int | str | None:
        """Return one staged value without falling back to device state."""
        return self._devices.get(serial, {}).get(key)

    def export(self) -> dict[str, dict[str, dict[str, int | str]]]:
        """Return the versioned Store payload body without sensitive context."""
        return {
            "devices": {
                serial: dict(values) for serial, values in self._devices.items()
            }
        }


def validate_smart_bundle(values: Mapping[str, Any]) -> None:
    """Require the selected target's complete user-owned activation bundle."""
    ready_by = values.get("ready_by_timestamp")
    if not isinstance(ready_by, int) or isinstance(ready_by, bool) or ready_by <= 0:
        raise SmartStagingError("Smart mode requires a ready-by time")

    target_type = values.get("smart_target_type")
    if target_type not in ("energy", "distance"):
        raise SmartStagingError("Smart mode requires a target type")

    if target_type == "energy":
        try:
            _validated_value("smart_charge_target_wh", values.get("smart_charge_target_wh"))
        except SmartStagingError as exc:
            raise SmartStagingError("Smart mode requires an energy target") from exc
    else:
        try:
            _validated_value(
                "smart_target_distance_km", values.get("smart_target_distance_km")
            )
        except SmartStagingError as exc:
            raise SmartStagingError("Smart mode requires a distance target") from exc


def validate_smart_activation(values: Mapping[str, Any], *, now: int) -> None:
    """Require a complete bundle whose deadline is still ahead of `now`.

    Storing a deadline and publishing one are different acts. A draft whose
    time has passed stays stored and stays editable, because the user may only
    want to change the hour; what must not happen is that draft becoming a new
    charging plan. So this rule lives here, on the publish path, and not in
    `_validated_value`, which `load()` also runs.

    The deadline is never moved forward on the user's behalf. Guessing which
    day they meant would silently schedule a charge they did not ask for.

    Timestamps are absolute seconds, so this comparison is free of any
    timezone or daylight-saving question. Those belong where a local wall-clock
    time is converted into a timestamp, which is the datetime entity.
    """
    validate_smart_bundle(values)
    ready_by = values["ready_by_timestamp"]
    if ready_by <= now:
        raise SmartDeadlineError(
            "Smart ready-by time has already passed",
            translation_key="smart_ready_by_expired",
            ready_by=ready_by,
        )
    if ready_by - now > SMART_READY_BY_MAX_HORIZON_SECONDS:
        raise SmartDeadlineError(
            "Smart ready-by time is too far ahead",
            translation_key="smart_ready_by_too_far_ahead",
            ready_by=ready_by,
        )
