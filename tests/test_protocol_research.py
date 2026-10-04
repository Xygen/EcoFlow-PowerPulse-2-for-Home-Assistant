"""Real transport payloads, direct evidence, safety and research diagnostics."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from test_coordinator_transactions import SERIAL, HAError
from test_coordinator_transactions import harness as transaction_harness


@pytest.fixture
def harness(monkeypatch):
    return transaction_harness.__wrapped__(monkeypatch)


def prepare(harness, **overrides):
    """An actual settings report carries companions as well as the target."""
    c = harness.coordinator
    c.hass.loop = asyncio.get_running_loop()
    harness.report_values = {
        "work_mode": "solar", "switch_bits_raw": 16, "continuous_charging": True,
        "solar_current_min_raw": 70, "user_current_set_raw": 100,
        "phase_mode": "three_phase", "phase_specified_raw": 2,
    }
    harness.report_values.update(overrides)


async def solar(harness, current=7, mode="solar", **kwargs):
    return await harness.coordinator.async_protocol_test_solar_minimum_field_only(
        SERIAL, current, mode, confirm_protocol_test=True, **kwargs,
    )


async def custom(harness, current=10, mode="solar"):
    return await harness.coordinator.async_protocol_test_custom_current_field_only(
        SERIAL, current, mode, confirm_protocol_test=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,continuous", [("solar", False), ("fast", False), ("fast", True)])
async def test_solar_exact_field_only_and_invariants(harness, mode, continuous):
    flags = 16 if continuous else 0
    harness.observe(work_mode=mode, continuous_charging=continuous, switch_bits_raw=flags)
    prepare(harness, work_mode=mode, continuous_charging=continuous, switch_bits_raw=flags)
    record = await solar(harness, mode=mode, expected_continuous_charging=continuous)
    assert harness.sent == [{4: 70}]
    assert 1 not in harness.sent[0] and 2 not in harness.sent[0]
    assert record["result"] == "confirmed"
    assert record["readback_source"] == "direct_fast_settings_241_44"
    assert all(record["invariants"].values())


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["solar", "fast"])
async def test_custom_exact_field_only_keeps_mode(harness, mode):
    harness.observe(work_mode=mode)
    prepare(harness, work_mode=mode)
    record = await custom(harness, mode=mode)
    assert harness.sent == [{6: 100}]
    assert 2 not in harness.sent[0]
    assert record["after"]["work_mode"] == mode


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", [solar, custom])
@pytest.mark.parametrize("failure", ["charging", "stale", "wrong_mode", "same", "disconnect",
                                     "missing_settings", "shutdown", "no_descriptor", "ambiguous_route"])
async def test_idle_research_rejects_without_publish(harness, operation, failure):
    prepare(harness)
    c = harness.coordinator
    if failure == "charging":
        harness.heartbeat("charging")
    elif failure == "stale":
        harness.heartbeat("plugged_in", age=91)
    elif failure == "wrong_mode":
        harness.observe(work_mode="fast")
    elif failure == "same":
        harness.observe(solar_current_min_raw=70, user_current_set_raw=100)
    elif failure == "disconnect":
        harness.connected = False
    elif failure == "missing_settings":
        harness.expire_settings()
    elif failure == "shutdown":
        c._shutting_down = True
    elif failure == "no_descriptor":
        c._accessory_descriptors.clear()
    elif failure == "ambiguous_route":
        c.observer_devices["another-parent"] = {}
    with pytest.raises(HAError):
        await operation(harness)
    assert harness.sent == []
    assert c.protocol_research_transactions[-1]["result"] == "validation_failed"


@pytest.mark.asyncio
async def test_solar_expected_continuous_is_rechecked(harness):
    prepare(harness)
    with pytest.raises(HAError, match="Continuous"):
        await solar(harness, expected_continuous_charging=False)
    assert not harness.sent


@pytest.mark.asyncio
@pytest.mark.parametrize("operation,overrides", [
    (solar, {"work_mode": "fast"}), (solar, {"switch_bits_raw": 0}),
    (solar, {"continuous_charging": False}), (custom, {"work_mode": "custom"}),
])
async def test_changed_companion_is_not_optimistic_success(harness, operation, overrides):
    prepare(harness, **overrides)
    with pytest.raises(HAError, match="companion"):
        await operation(harness)
    assert harness.coordinator.protocol_research_transactions[-1]["result"] == "unexpected_companion_change"
    assert len(harness.sent) == 1  # No speculative rollback.


@pytest.mark.asyncio
@pytest.mark.parametrize("source,values", [
    ("provider_parent_accessory", None), ("direct_settings_2_34", None),
    ("direct_fast_settings_241_44", {"solar_current_min_raw": 70}),
    ("direct_fast_settings_241_44", {"solar_current_min_raw": 60}),
])
async def test_only_new_direct_target_and_companions_confirm(harness, monkeypatch, source, values):
    prepare(harness)
    import custom_components.ecoflow_powerpulse2.protocol_research as research
    monkeypatch.setattr(research, "READBACK_SECONDS", 0.08)
    harness.report_source = source
    if values is not None:
        harness.report_values = values
    with pytest.raises(HAError, match="newer direct"):
        await solar(harness)
    record = harness.coordinator.protocol_research_transactions[-1]
    assert record["set_reply_received"]
    assert record["result"] in ("direct_readback_timeout", "device_rejected")


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["mode", "charging", "continuous"])
async def test_queued_research_rechecks_inside_shared_lock(harness, change):
    prepare(harness)
    changes = {
        "mode": lambda: harness.observe(work_mode="fast"),
        "charging": lambda: harness.heartbeat("charging"),
        "continuous": lambda: harness.observe(continuous_charging=False),
    }
    operation = solar(harness, expected_continuous_charging=True) if change == "continuous" else custom(harness)
    with pytest.raises(HAError):
        await harness.queued(operation, changes[change])
    assert not harness.sent
    assert harness.coordinator.protocol_research_transactions[-1]["result"] == "state_changed_before_dispatch"


@pytest.mark.asyncio
@pytest.mark.parametrize("confirmed", [False, None, "true", 1])
async def test_confirmation_is_explicit_boolean(harness, confirmed):
    prepare(harness)
    with pytest.raises(HAError, match="confirm_protocol_test"):
        await harness.coordinator.async_protocol_test_custom_current_field_only(
            SERIAL, 10, "solar", confirm_protocol_test=confirmed,
        )
    assert not harness.sent


@pytest.mark.asyncio
@pytest.mark.parametrize("current", [5, 17, 6.5, True, "7", float("nan")])
async def test_invalid_current_cannot_publish(harness, current):
    prepare(harness)
    with pytest.raises(HAError):
        await custom(harness, current=current)
    assert not harness.sent


@pytest.mark.asyncio
async def test_normal_phase_control_and_research_allow_charging(harness, monkeypatch):
    prepare(harness)
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    harness.heartbeat("charging")
    import custom_components.ecoflow_powerpulse2.protocol_research as research
    monkeypatch.setattr(research, "PHASE_OBSERVATION_SECONDS", 0.05)
    c = harness.coordinator
    assert c.phase_control_available(SERIAL)
    await c.async_set_phase_mode(SERIAL, "three_phase")
    assert harness.sent == [{5: 2}]
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    record = await c.async_protocol_test_phase_while_charging(
        SERIAL, "three_phase", confirm_protocol_test=True,
    )
    assert harness.sent == [{5: 2}, {5: 2}]
    assert record["after"]["phase_specified_raw"] == 2
    assert record["physical_phase_observation"]["result"] == "insufficient_fresh_telemetry"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["plugged_in", "paused", "unknown", "unplugged", "charge_complete",
                                     "standby", "stale", "missing_phase", "same", "stale_phase"])
async def test_phase_research_requires_actual_charging_and_transition(harness, failure):
    prepare(harness)
    c = harness.coordinator
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    harness.heartbeat("charging")
    if failure == "stale":
        harness.heartbeat("charging", age=91)
    elif failure == "missing_phase":
        c._phase_readbacks = harness.module.PhaseReadbackTracker()
    elif failure == "same":
        harness.observe(phase_specified_raw=2, phase_mode="three_phase")
    elif failure == "stale_phase":
        c._phase_readbacks.record(SERIAL, "direct_241_44", {"phase_specified_raw": 1},
                                 observed_monotonic=harness.now() - 11)
    else:
        harness.heartbeat(failure)
    with pytest.raises(HAError):
        await c.async_protocol_test_phase_while_charging(SERIAL, "three_phase", confirm_protocol_test=True)
    assert not harness.sent


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["changed", "unchanged", "insufficient_fresh_telemetry"])
async def test_phase_physical_observation_uses_new_push_telemetry(harness, monkeypatch, outcome):
    prepare(harness)
    c = harness.coordinator
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    harness.heartbeat("charging")
    c.data[SERIAL]["direct_active_phase_raw"] = 1
    import custom_components.ecoflow_powerpulse2.protocol_research as research
    monkeypatch.setattr(research, "PHASE_OBSERVATION_SECONDS", 0.3)
    if outcome != "insufficient_fresh_telemetry":
        def push():
            harness.heartbeat("charging")
            c.data[SERIAL]["direct_active_phase_raw"] = 2 if outcome == "changed" else 1
        asyncio.get_running_loop().call_later(0.07, push)
    record = await c.async_protocol_test_phase_while_charging(SERIAL, "three_phase", confirm_protocol_test=True)
    assert record["physical_phase_observation"]["result"] == outcome
    assert harness.sent == [{5: 2}]


@pytest.mark.asyncio
async def test_phase_session_end_is_not_reported_as_physical_switch(harness, monkeypatch):
    prepare(harness)
    c = harness.coordinator
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    harness.heartbeat("charging")
    c.data[SERIAL]["direct_active_phase_raw"] = 1
    import custom_components.ecoflow_powerpulse2.protocol_research as research
    monkeypatch.setattr(research, "PHASE_OBSERVATION_SECONDS", 0.3)
    def stopped():
        harness.heartbeat("plugged_in")
        c.data[SERIAL]["direct_active_phase_raw"] = 0
    asyncio.get_running_loop().call_later(0.07, stopped)
    record = await c.async_protocol_test_phase_while_charging(SERIAL, "three_phase", confirm_protocol_test=True)
    assert record["physical_phase_observation"]["result"] == "insufficient_fresh_telemetry"
    assert record["physical_phase_observation"]["session_ended"]
    assert record["after"]["charging_status"] == "plugged_in"


@pytest.mark.asyncio
async def test_queued_phase_rechecks_active_session(harness):
    prepare(harness)
    c = harness.coordinator
    harness.observe(phase_specified_raw=1, phase_mode="one_phase")
    harness.heartbeat("charging")
    with pytest.raises(HAError, match="actively charging"):
        await harness.queued(
            c.async_protocol_test_phase_while_charging(SERIAL, "three_phase", confirm_protocol_test=True),
            lambda: harness.heartbeat("paused"),
        )
    assert not harness.sent
    assert c.protocol_research_transactions[-1]["result"] == "state_changed_before_dispatch"


@pytest.mark.asyncio
async def test_stale_direct_settings_cannot_publish(harness):
    prepare(harness)
    c = harness.coordinator
    harness.expire_settings()
    c._record_setting_observations(
        SERIAL, "direct_fast_settings_241_44", {"user_current_set_raw": 60},
        observed_monotonic=harness.now() - 91,
    )
    with pytest.raises(HAError, match="fresh direct"):
        await custom(harness)
    assert not harness.sent


@pytest.mark.asyncio
async def test_research_never_uses_provider_bundle_noop(harness):
    prepare(harness)
    c = harness.coordinator
    # Earlier provider echo equals the requested target. Direct device evidence
    # still proves a transition is required; research must send the partial frame.
    c._record_setting_observations(
        SERIAL, "provider_parent_accessory", {"user_current_set_raw": 100},
        observed_monotonic=harness.now() - 1,
    )
    record = await custom(harness)
    assert record["result"] == "confirmed"
    assert harness.sent == [{6: 100}]


@pytest.mark.asyncio
async def test_precommand_target_readback_is_never_confirmation(harness, monkeypatch):
    prepare(harness)
    c = harness.coordinator
    import custom_components.ecoflow_powerpulse2.protocol_research as research
    monkeypatch.setattr(research, "READBACK_SECONDS", 0)
    record = {"action": "custom_current_field_only", "expected_key": "user_current_set_raw",
              "expected_value": 100, "before": {}, "after": {}}
    harness.observe(user_current_set_raw=100)
    with pytest.raises(HAError, match="newer direct"):
        await c._async_confirm_protocol_research(SERIAL, harness.now() + 1, record)
    assert record["result"] == "direct_readback_timeout"


@pytest.mark.asyncio
async def test_history_is_bounded_detached_private_and_records_fields(harness):
    prepare(harness)
    await custom(harness)
    c = harness.coordinator
    record = c.protocol_research_transactions[-1]
    assert record["published_fields"] == {"6": 100}
    assert record["set_reply_received"]
    assert SERIAL not in json.dumps(record)
    for _ in range(25):
        with pytest.raises(HAError):
            await custom(harness)
    history = c.protocol_research_transactions
    assert len(history) == 20
    history[0]["result"] = "modified"
    assert c.protocol_research_transactions[0]["result"] != "modified"


@pytest.mark.asyncio
async def test_publish_exception_cleans_waiter_and_records_failure(harness, monkeypatch):
    prepare(harness)
    def failed(*args):
        raise RuntimeError("secret-account-value")
    monkeypatch.setattr(harness.coordinator.hass, "async_add_executor_job", failed)
    with pytest.raises(HAError):
        await custom(harness)
    c = harness.coordinator
    assert not c._reply_waiters
    assert c.protocol_research_transactions[-1]["result"] == "publish_failed"
    assert "secret-account-value" not in json.dumps(c.protocol_research_transactions)


@pytest.mark.asyncio
async def test_reply_timeout_records_delivery_failure(harness):
    prepare(harness)
    harness.reply = False
    with pytest.raises(HAError, match="SET reply"):
        await custom(harness)
    c = harness.coordinator
    assert not c._reply_waiters
    assert c.protocol_research_transactions[-1]["result"] == "set_reply_timeout"


@pytest.fixture
def services(harness, monkeypatch):
    """Real voluptuous schemas with registry/HA boundary doubles."""
    import importlib.util
    import sys
    from enum import Enum
    from pathlib import Path

    class State(Enum):
        LOADED = "loaded"
        NOT_LOADED = "not_loaded"

    monkeypatch.setattr(sys.modules["homeassistant.config_entries"], "ConfigEntryState", State, raising=False)
    core = sys.modules["homeassistant.core"]
    monkeypatch.setattr(core, "ServiceCall", object, raising=False)
    monkeypatch.setattr(core, "SupportsResponse", SimpleNamespace(OPTIONAL="optional"), raising=False)
    entry = SimpleNamespace(entry_id="test", state=State.LOADED, runtime_data=harness.coordinator)
    device = SimpleNamespace(identifiers={("ecoflow_powerpulse2", SERIAL)}, config_entries={"test"})
    registry = SimpleNamespace(async_get=lambda device_id: device if device_id == "device" else None)
    monkeypatch.setattr(sys.modules["homeassistant.helpers"], "device_registry",
                        SimpleNamespace(async_get=lambda hass: registry), raising=False)
    registered = {}
    def register(domain, action, handler, **kwargs):
        registered[action] = (handler, kwargs)
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda domain: [entry]),
                           services=SimpleNamespace(async_register=register))
    name = "custom_components.ecoflow_powerpulse2._research_test_services"
    path = Path(__file__).parents[1] / "custom_components/ecoflow_powerpulse2/services.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    module.async_register_protocol_actions(hass)
    return SimpleNamespace(module=module, registered=registered, entry=entry, device=device,
                           hass=hass, state=State)


@pytest.mark.asyncio
async def test_services_registered_globally_and_schema_dispatches_one_write(harness, services):
    prepare(harness)
    assert len(services.registered) == 3
    handler, options = services.registered["protocol_test_custom_current_field_only"]
    data = options["schema"]({"device_id": "device", "current": 10, "expected_work_mode": "solar",
                              "confirm_protocol_test": True})
    record = await handler(SimpleNamespace(data=data))
    assert record["result"] == "confirmed"
    assert options["supports_response"] == "optional"
    assert harness.sent == [{6: 100}]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["missing_confirmation", "false_confirmation", "unknown", "wrong_device",
                                     "unloaded", "missing_coordinator", "not_member", "ambiguous", "duplicate_owner"])
async def test_service_resolution_and_confirmation_fail_closed(harness, services, failure):
    prepare(harness)
    handler, options = services.registered["protocol_test_custom_current_field_only"]
    data = {"device_id": "device", "current": 10, "expected_work_mode": "solar", "confirm_protocol_test": True}
    if failure == "missing_confirmation":
        data.pop("confirm_protocol_test")
    elif failure == "false_confirmation":
        data["confirm_protocol_test"] = False
    elif failure == "unknown":
        data["device_id"] = "unknown"
    elif failure == "wrong_device":
        services.device.identifiers = {("other", SERIAL)}
    elif failure == "unloaded":
        services.entry.state = services.state.NOT_LOADED
    elif failure == "missing_coordinator":
        services.entry.runtime_data = None
    elif failure == "not_member":
        harness.coordinator.devices.clear()
    elif failure == "ambiguous":
        services.device.identifiers.add(("ecoflow_powerpulse2", "another"))
    elif failure == "duplicate_owner":
        other = SimpleNamespace(entry_id="second", state=services.state.LOADED,
                                runtime_data=harness.coordinator)
        services.hass.config_entries.async_entries = lambda domain: [services.entry, other]
    with pytest.raises(HAError):
        await handler(SimpleNamespace(data=options["schema"](data)))
    assert not harness.sent


@pytest.mark.parametrize("extra", [{"current": 6.2}, {"current": True}, {"current": "7"},
                                  {"confirm_protocol_test": "true"}, {"raw": 100},
                                  {"device_id": ["device", "other"]}, {"expected_work_mode": "custom"}])
def test_schema_rejects_unsafe_or_generic_inputs(services, extra):
    import voluptuous as vol
    _, options = services.registered["protocol_test_custom_current_field_only"]
    data = {"device_id": "device", "current": 10, "expected_work_mode": "solar", "confirm_protocol_test": True}
    data.update(extra)
    with pytest.raises(vol.Invalid):
        options["schema"](data)
