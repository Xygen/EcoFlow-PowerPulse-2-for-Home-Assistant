"""Execute real coordinator transactions with HA and network boundary doubles.

These tests import the complete coordinator, use real asyncio locks, observation
trackers and payload builders, and replace only the unavailable HA shell and I/O.
They are not a Home Assistant runtime or vehicle validation.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from custom_components.ecoflow_powerpulse2.ecoflow.proto_encoding import iter_protobuf_fields

PACKAGE = "custom_components.ecoflow_powerpulse2"
SERIAL = "C376-test"
PARENT = "HJ31-test"


class HAError(Exception):
    pass


class AuthFailed(Exception):
    """Stand-in for ConfigEntryAuthFailed.

    Kept distinct from HAError so a refused credential stays
    distinguishable from an ordinary failed update.
    """


class CoordinatorShell:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.data = {}
        self.last_update_success = True

    def async_update_listeners(self):
        pass


class StoreDouble:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args):
        self.saved = None

    async def async_save(self, value):
        self.saved = value


def bytes_field(payload, number):
    return next(value for key, wire, value in iter_protobuf_fields(payload) if key == number and wire == 2)


@pytest.fixture
def harness(monkeypatch):
    """Load the real module without installing HA into the Windows test venv."""
    def module(name, **attributes):
        result = ModuleType(name)
        result.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    module("homeassistant")
    module("homeassistant.config_entries", ConfigEntry=object)
    module("homeassistant.core", HomeAssistant=object, callback=lambda function: function)
    module("homeassistant.helpers.event", async_track_time_interval=lambda *args: lambda: None)
    module(
        "homeassistant.exceptions",
        ConfigEntryAuthFailed=AuthFailed,
        HomeAssistantError=HAError,
    )
    module("homeassistant.helpers")
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.helpers.storage", Store=StoreDouble)
    module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=CoordinatorShell, UpdateFailed=HAError)
    module(PACKAGE + ".api", PowerPulse2ApiClient=lambda *args: SimpleNamespace())
    module(
        PACKAGE + ".const", CONF_EMAIL="email", CONF_PASSWORD="password",
        DOMAIN="ecoflow_powerpulse2", CREDENTIAL_MAX_AGE_SECONDS=72_000,
        CREDENTIAL_REFRESH_INTERVAL_SECONDS=300, SESSION_RENEWAL_INTERVAL_SECONDS=300,
        SETTINGS_REFRESH_DELAY_SECONDS=20, UPDATE_INTERVAL_SECONDS=30,
    )
    name = PACKAGE + "._transaction_test_coordinator"
    path = Path(__file__).parents[1] / "custom_components/ecoflow_powerpulse2/coordinator.py"
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, loaded)
    spec.loader.exec_module(loaded)
    return Harness(loaded)


class Harness:
    def __init__(self, module):
        self.module = module
        self.now = module.time.monotonic
        self.sent = []
        self.connected = True
        self.reply = True
        self.readback = True
        self.coordinator = module.PowerPulse2Coordinator(
            SimpleNamespace(async_add_executor_job=self.execute),
            SimpleNamespace(data={"email": "test", "password": "test"}, entry_id="test"),
        )
        c = self.coordinator
        c.devices = {SERIAL: {}}
        c.observer_devices = {PARENT: {}}
        c.mqtt_clients = {
            SERIAL: SimpleNamespace(is_connected=lambda: True),
            PARENT: SimpleNamespace(is_connected=lambda: self.connected, send_explicit_control=self.publish),
        }
        c._accessory_descriptors[SERIAL] = b"opaque-accessory"
        c.data[SERIAL] = {}
        self.observe(
            work_mode="solar", switch_bits_raw=16, continuous_charging=True,
            solar_current_min_raw=60, user_current_set_raw=60,
            screen_enabled=True, indicator_enabled=True,
            screen_brightness_pct=100, indicator_brightness_pct=25,
            output_current_max_raw=160,
        )
        self.heartbeat("plugged_in")

    async def execute(self, callback, *args):
        return callback(*args)

    def heartbeat(self, status, age=0):
        c = self.coordinator
        c.data[SERIAL].update(direct_charging_status=status, charging_status=status)
        c._last_heartbeat_at[SERIAL] = self.now() - age

    def observe(self, **values):
        c = self.coordinator
        c.data[SERIAL].update(values)
        c._record_setting_observations(SERIAL, "direct_fast_settings_241_44", values)
        c._last_direct_settings_at[SERIAL] = self.now()

    def expire_settings(self):
        c = self.coordinator
        c._setting_observations = self.module.SettingObservationTracker(self.module._SETTING_SOURCE_FRESH_SECONDS)

    def publish(self, payload):
        header = bytes_field(payload, 1)
        fields = {key: value for key, wire, value in iter_protobuf_fields(header) if wire == 0}
        command, sequence = fields[9], fields[14]
        body = bytes_field(header, 1)
        values = {}
        if command == 102:
            settings = dict((key, value) for key, _, value in iter_protobuf_fields(bytes_field(body, 4)))
            self.sent.append(settings)
            if 1 in settings:
                flags = settings[1]
                values.update(switch_bits_raw=flags, plug_and_play=bool(flags & 2),
                              battery_discharge_disabled=bool(flags & 1), continuous_charging=bool(flags & 16))
            if 2 in settings:
                values["work_mode"] = {1: "fast", 2: "solar", 3: "custom", 4: "smart"}[settings[2]]
            for field, key in ((3, "output_current_max_raw"), (4, "solar_current_min_raw"),
                               (6, "user_current_set_raw")):
                if field in settings:
                    values[key] = settings[field]
            if 21 in settings:
                display = settings[21]
                values.update(indicator_enabled=bool(display[0]), screen_enabled=bool(display[1]),
                              indicator_brightness_pct=display[2], screen_brightness_pct=display[3])
            if 7 in settings:
                smart = dict((key, value) for key, _, value in iter_protobuf_fields(settings[7]))
                values.update(ready_by_timestamp=smart[1],
                              smart_target_type="energy" if smart[2] == 1 else "distance",
                              smart_charge_target_wh=smart[3], smart_target_distance_km=smart[4])
        else:
            self.sent.append({"action": command})

        def receive():
            if self.readback:
                if command == 102:
                    self.observe(**values)
                else:
                    self.heartbeat("charging")
            if self.reply:
                waiter = self.coordinator._reply_waiters.get((PARENT, 241, command, sequence))
                if waiter is not None and not waiter.done():
                    waiter.set_result(None)

        # Windows monotonic clocks can give adjacent callbacks the same tick.
        asyncio.get_running_loop().call_later(0.02, receive)
        return True

    async def queued(self, operation, change):
        self.coordinator.hass.loop = asyncio.get_running_loop()
        await self.coordinator._control_lock.acquire()
        task = asyncio.create_task(operation)
        try:
            await asyncio.sleep(0)
            assert not task.done(), "Operation must actually wait on the shared lock"
            change()
        finally:
            self.coordinator._control_lock.release()
        return await task


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["charging", "stale", "disconnect", "shutdown", "removed"])
async def test_queued_current_write_rechecks_dispatch_prerequisites(harness, change):
    c = harness.coordinator

    def invalidate():
        if change == "charging":
            harness.heartbeat("charging")
            c.data[SERIAL]["charging_status"] = "plugged_in"  # Provider cannot bypass Direct.
        elif change == "stale":
            harness.heartbeat("plugged_in", age=91)
        elif change == "disconnect":
            harness.connected = False
        elif change == "shutdown":
            c._shutting_down = True
        else:
            c.devices.clear()

    with pytest.raises(HAError):
        await harness.queued(c.async_set_maximum_output_current(SERIAL, 6), invalidate)
    assert harness.sent == []
    assert not c._reply_waiters


@pytest.mark.asyncio
@pytest.mark.parametrize("action,status", [("start", "plugged_in"), ("stop", "charging")])
async def test_queued_charge_action_rechecks_heartbeat_age(harness, action, status):
    harness.heartbeat(status)
    c = harness.coordinator
    with pytest.raises(HAError, match="heartbeat"):
        await harness.queued(c._async_set_charging(SERIAL, action), lambda: harness.heartbeat(status, age=91))
    assert harness.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", ["mode", "disabled", "stale"])
async def test_queued_solar_current_rechecks_mode_and_enablement(harness, condition):
    c = harness.coordinator

    def invalidate():
        if condition == "mode":
            harness.observe(work_mode="fast")
        elif condition == "disabled":
            harness.observe(continuous_charging=False)
        else:
            harness.expire_settings()

    with pytest.raises(HAError):
        await harness.queued(c.async_set_solar_minimum_current(SERIAL, 7), invalidate)
    assert harness.sent == []


@pytest.mark.asyncio
async def test_queued_custom_current_does_not_restore_old_mode(harness):
    c = harness.coordinator
    harness.observe(work_mode="custom")
    with pytest.raises(HAError):
        await harness.queued(c.async_set_custom_current(SERIAL, 7), lambda: harness.observe(work_mode="solar"))
    assert harness.sent == []


@pytest.mark.asyncio
async def test_flags_are_built_after_lock_and_preserve_fresh_companions(harness):
    c = harness.coordinator
    await harness.queued(c.async_set_plug_and_play(SERIAL, True), lambda: harness.observe(switch_bits_raw=17))
    assert harness.sent == [{1: 19}]
    assert c._control_readback_counts["direct"] == 1


@pytest.mark.asyncio
async def test_expired_flags_cannot_be_reused_from_merged_cache(harness):
    c = harness.coordinator
    with pytest.raises(HAError, match="readback"):
        await harness.queued(c.async_set_plug_and_play(SERIAL, True), harness.expire_settings)
    assert harness.sent == []


@pytest.mark.asyncio
async def test_mode_bundle_uses_latest_companion_values(harness):
    c = harness.coordinator
    harness.observe(work_mode="fast")
    await harness.queued(
        c.async_set_work_mode(SERIAL, "solar"),
        lambda: harness.observe(switch_bits_raw=18, solar_current_min_raw=70),
    )
    assert harness.sent == [{1: 18, 2: 2, 4: 70}]


@pytest.mark.asyncio
async def test_display_companions_are_refreshed_after_waiting(harness):
    c = harness.coordinator
    await harness.queued(
        c.async_set_screen_brightness(SERIAL, 50),
        lambda: harness.observe(indicator_enabled=False, indicator_brightness_pct=75),
    )
    assert harness.sent == [{21: bytes((0, 1, 75, 50, 0, 0))}]


@pytest.mark.asyncio
async def test_brightness_rejects_screen_disabled_while_waiting(harness):
    c = harness.coordinator
    with pytest.raises(HAError):
        await harness.queued(c.async_set_screen_brightness(SERIAL, 50), lambda: harness.observe(screen_enabled=False))
    assert harness.sent == []


@pytest.mark.asyncio
async def test_concurrent_flag_writes_do_not_lose_the_first_update(harness):
    c = harness.coordinator
    c.hass.loop = asyncio.get_running_loop()
    await asyncio.gather(
        c.async_set_plug_and_play(SERIAL, True),
        c.async_set_battery_discharge_disabled(SERIAL, True),
    )
    assert harness.sent == [{1: 18}, {1: 19}]


@pytest.mark.asyncio
async def test_concurrent_display_writes_preserve_each_other(harness):
    c = harness.coordinator
    c.hass.loop = asyncio.get_running_loop()
    await asyncio.gather(c.async_set_screen_brightness(SERIAL, 50), c.async_set_indicator_brightness(SERIAL, 75))
    assert harness.sent == [{21: bytes((1, 1, 25, 50, 0, 0))}, {21: bytes((1, 1, 75, 50, 0, 0))}]


@pytest.mark.asyncio
async def test_local_smart_edit_cannot_turn_into_a_queued_device_write(harness):
    c = harness.coordinator
    with pytest.raises(HAError, match="mode changed"):
        await harness.queued(c.async_set_smart_energy_target(SERIAL, 20), lambda: harness.observe(work_mode="smart"))
    assert harness.sent == []
    assert c._smart_staging.value(SERIAL, "smart_charge_target_wh") is None


@pytest.mark.asyncio
async def test_local_smart_edit_still_persists_without_device_evidence(harness):
    c = harness.coordinator
    harness.expire_settings()
    harness.connected = False
    await c.async_set_smart_energy_target(SERIAL, 20)
    assert c._smart_staging.value(SERIAL, "smart_charge_target_wh") == 20000
    assert harness.sent == []


@pytest.mark.asyncio
async def test_valid_start_still_requires_reply_and_fresh_readback(harness):
    c = harness.coordinator
    c.hass.loop = asyncio.get_running_loop()
    await c.async_start_charging(SERIAL)
    assert harness.sent == [{"action": 100}]
    assert c.data[SERIAL]["direct_charging_status"] == "charging"


def test_sensitive_availability_uses_direct_not_merged_provider_status(harness):
    c = harness.coordinator
    harness.heartbeat("charging")
    c.data[SERIAL]["charging_status"] = "plugged_in"
    assert not c.charging_sensitive_control_available(SERIAL, "output_current_max_raw")
    assert c.charging_sensitive_control_available(SERIAL, "plug_and_play")


@pytest.mark.asyncio
async def test_active_smart_edit_preserves_latest_ready_time(harness):
    c = harness.coordinator
    harness.observe(work_mode="smart", ready_by_timestamp=2000000000,
                    smart_target_type="energy", smart_charge_target_wh=10000)
    await harness.queued(c.async_set_smart_energy_target(SERIAL, 20),
                         lambda: harness.observe(ready_by_timestamp=2000003600))
    smart = dict((key, value) for key, _, value in iter_protobuf_fields(harness.sent[0][7]))
    assert smart == {1: 2000003600, 2: 1, 3: 20000, 4: 0}


@pytest.mark.asyncio
async def test_active_smart_edit_rejects_mode_change(harness):
    c = harness.coordinator
    harness.observe(work_mode="smart", ready_by_timestamp=2000000000,
                    smart_target_type="energy", smart_charge_target_wh=10000)
    with pytest.raises(HAError):
        await harness.queued(c.async_set_smart_energy_target(SERIAL, 20),
                             lambda: harness.observe(work_mode="fast"))
    assert harness.sent == []


@pytest.mark.asyncio
async def test_unlocked_flag_can_still_change_during_charging(harness):
    harness.heartbeat("charging")
    await harness.queued(harness.coordinator.async_set_plug_and_play(SERIAL, True), lambda: None)
    assert harness.sent == [{1: 18}]


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["direct_settings_2_34", "provider_parent_accessory"])
@pytest.mark.parametrize("key,value", [("work_mode", "fast"), ("continuous_charging", False),
                                       ("switch_bits_raw", 17)])
async def test_newer_conflicting_source_blocks_queued_solar_write(harness, source, key, value):
    c = harness.coordinator
    # Distinct timestamps avoid depending on the Windows clock resolution.
    c._setting_observations.record_snapshot(
        serial=SERIAL, source=source, values={key: value}, keys={key},
        observed_at="2026-09-09T20:00:00+00:00", observed_monotonic=harness.now() + 0.01,
    )
    with pytest.raises(HAError):
        await harness.queued(c.async_set_solar_minimum_current(SERIAL, 7), lambda: None)
    assert harness.sent == []
