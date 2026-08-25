"""Read-only binary sensors for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerPulse2Coordinator
from .entity import PowerPulse2Entity

SETTING_BINARY_SENSORS = (
    BinarySensorEntityDescription(
        key="continuous_charging",
        translation_key="continuous_charging",
    ),
    BinarySensorEntityDescription(
        key="plug_and_play",
        translation_key="plug_and_play",
    ),
    BinarySensorEntityDescription(
        key="battery_discharge_disabled",
        translation_key="battery_discharge_disabled",
    ),
    BinarySensorEntityDescription(
        key="screen_enabled",
        translation_key="screen_enabled",
    ),
    BinarySensorEntityDescription(
        key="indicator_enabled",
        translation_key="indicator_enabled",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    async_add_entities(
        PowerPulse2ChargingSensor(coordinator, serial)
        for serial in coordinator.devices
    )
    async_add_entities(
        PowerPulse2DirectStreamSensor(coordinator, serial)
        for serial in coordinator.devices
    )
    async_add_entities(
        PowerPulse2SettingBinarySensor(coordinator, serial, description)
        for serial in coordinator.devices
        for description in SETTING_BINARY_SENSORS
    )


class PowerPulse2ChargingSensor(PowerPulse2Entity, BinarySensorEntity):
    """Whether the charger reports an active charging session."""

    _attr_translation_key = "charging"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "charging")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and "charging_status" in self.coordinator.data.get(
            self.serial, {}
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get(self.serial, {}).get("charging_status") == "charging"


class PowerPulse2DirectStreamSensor(PowerPulse2Entity, BinarySensorEntity):
    """Whether the direct C376 settings stream is currently fresh."""

    _attr_translation_key = "direct_data_stream"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "direct_data_stream")

    @property
    def available(self) -> bool:
        return self.coordinator.direct_stream_available(self.serial)

    @property
    def is_on(self) -> bool:
        return self.coordinator.direct_stream_active(self.serial)

    @property
    def extra_state_attributes(self) -> dict:
        return self.coordinator.direct_stream_diagnostics(self.serial)


class PowerPulse2SettingBinarySensor(PowerPulse2Entity, BinarySensorEntity):
    """A boolean setting observed in the CP307 parameter report."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: PowerPulse2Coordinator,
        serial: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.entity_description.key in self.coordinator.data.get(
            self.serial, {}
        )

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get(self.serial, {}).get(
                self.entity_description.key
            )
        )
