from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from custom_components.ecoflow_powerpulse2 import (
    _enable_new_canonical_sensor_defaults,
)


class _Registry:
    def __init__(self, disabled_by: object) -> None:
        self.entry = SimpleNamespace(disabled_by=disabled_by)
        self.updates: list[tuple[str, object]] = []

    def async_get_entity_id(self, platform: str, domain: str, unique_id: str) -> str:
        assert (platform, domain, unique_id) == (
            "sensor",
            "ecoflow_powerpulse2",
            "C376-test_smart_charge_target_wh",
        )
        return "sensor.powerpulse_2_smart_charge_target"

    def async_get(self, entity_id: str) -> object:
        assert entity_id == "sensor.powerpulse_2_smart_charge_target"
        return self.entry

    def async_update_entity(self, entity_id: str, *, disabled_by: object) -> None:
        self.updates.append((entity_id, disabled_by))


def _install_entity_registry_stub(monkeypatch, registry: _Registry) -> object:
    integration_disabler = object()
    entity_registry = ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.async_get = lambda hass: registry  # type: ignore[attr-defined]
    entity_registry.RegistryEntryDisabler = SimpleNamespace(  # type: ignore[attr-defined]
        INTEGRATION=integration_disabler
    )
    helpers = ModuleType("homeassistant.helpers")
    helpers.entity_registry = entity_registry  # type: ignore[attr-defined]
    homeassistant = ModuleType("homeassistant")
    homeassistant.helpers = helpers  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.entity_registry", entity_registry
    )
    return integration_disabler


def test_migration_enables_only_integration_disabled_canonical_sensor(
    monkeypatch,
) -> None:
    registry = _Registry(disabled_by=None)
    integration_disabler = _install_entity_registry_stub(monkeypatch, registry)
    registry.entry.disabled_by = integration_disabler

    _enable_new_canonical_sensor_defaults(
        object(), ["C376-test"], "ecoflow_powerpulse2"
    )

    assert registry.updates == [
        ("sensor.powerpulse_2_smart_charge_target", None)
    ]


def test_migration_preserves_user_disabled_canonical_sensor(monkeypatch) -> None:
    user_disabler = object()
    registry = _Registry(disabled_by=user_disabler)
    _install_entity_registry_stub(monkeypatch, registry)

    _enable_new_canonical_sensor_defaults(
        object(), ["C376-test"], "ecoflow_powerpulse2"
    )

    assert registry.updates == []
