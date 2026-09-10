import ast
import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.ecoflow_powerpulse2.stream_recovery import recovery_reason
from custom_components.ecoflow_powerpulse2.stream_timeline import StreamTimeline


def record(timeline, now=0, serial="C376-private-serial", **changes):
    values = dict(role="powerpulse", event="recovery_check", reason="cooldown",
                  connected=True, settings_age=400, heartbeat_age=500,
                  cooldown_remaining=100, settings_fresh=False, heartbeat_fresh=False)
    values.update(changes)
    timeline.record(serial, now=now, **values)


def test_periodic_sampling_transitions_and_retention_are_explicit():
    timeline = StreamTimeline(limit=3)
    record(timeline)
    record(timeline, now=299)
    assert len(timeline.snapshot()["events"]) == 1
    record(timeline, now=300)
    record(timeline, now=301, reason="due")
    record(timeline, now=302, event="mqtt_connection", reason="disconnected")
    snapshot = timeline.snapshot()
    assert len(snapshot["events"]) == 3
    assert snapshot["dropped_events"] == 1
    assert snapshot["retention"] == "current_runtime_only"
    assert "C376-private-serial" not in json.dumps(snapshot)
    snapshot["events"][0]["reason"] = "changed by caller"
    assert timeline.snapshot()["events"][0]["reason"] == "cooldown"


def test_sources_do_not_collide_and_freshness_change_is_not_suppressed():
    timeline = StreamTimeline()
    record(timeline, serial="same-prefix-1")
    record(timeline, serial="same-prefix-2")
    record(timeline, now=1, serial="same-prefix-1", heartbeat_fresh=True)
    events = timeline.snapshot()["events"]
    assert [event["source"] for event in events] == ["source_1", "source_2", "source_1"]
    assert StreamTimeline().snapshot()["events"] == []


def coordinator_harness():
    """Execute production methods with isolated HA boundaries, not HA fixtures."""
    tree = ast.parse(Path("custom_components/ecoflow_powerpulse2/coordinator.py").read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    names = {"_async_maybe_recover_direct_stream", "_record_stream_event",
             "_schedule_mqtt_status", "direct_stream_active", "heartbeat_stream_active"}
    methods = [node for node in cls.body if getattr(node, "name", None) in names]
    module = ast.Module(body=methods, type_ignores=[])
    namespace = dict(time=SimpleNamespace(monotonic=lambda: 1000),
                     recovery_reason=recovery_reason, HomeAssistantError=RuntimeError,
                     _AUTOMATIC_RECOVERY_STALE_SECONDS=300,
                     _AUTOMATIC_RECOVERY_COOLDOWN_SECONDS=1800,
                     _DIRECT_SETTINGS_FRESH_SECONDS=10, _HEARTBEAT_STREAM_FRESH_SECONDS=90,
                     _LOGGER=logging.getLogger(__name__))
    exec(compile(module, "coordinator.py", "exec"), namespace)
    harness = type("Harness", (), {name: namespace[name] for name in names})()
    harness.devices = {"private-device": {}}
    harness.mqtt_clients = {"private-device": SimpleNamespace(is_connected=lambda: True)}
    harness._last_direct_settings_at = {"private-device": 600}
    harness._last_heartbeat_at = {"private-device": 600}
    harness._last_automatic_reconnect_at = {}
    harness._stream_timeline = StreamTimeline()
    harness._shutting_down = False
    harness._async_reconnect_direct_stream = AsyncMock()
    return harness


def test_recovery_path_records_attempt_then_cooldown_without_extra_reconnect():
    harness = coordinator_harness()
    asyncio.run(harness._async_maybe_recover_direct_stream("private-device"))
    asyncio.run(harness._async_maybe_recover_direct_stream("private-device"))
    harness._async_reconnect_direct_stream.assert_awaited_once_with(
        "private-device", method="automatic_wss_reconnect")
    events = harness._stream_timeline.snapshot()["events"]
    assert [e["reason"] for e in events] == ["due", "started", "returned", "cooldown"]
    assert events[0]["heartbeat_age_s"] == 400
    assert events[-1]["cooldown_remaining_s"] == 1800


def test_disconnected_and_never_started_streams_do_not_reconnect():
    harness = coordinator_harness()
    harness.mqtt_clients["private-device"].is_connected = lambda: False
    asyncio.run(harness._async_maybe_recover_direct_stream("private-device"))
    harness.mqtt_clients["private-device"].is_connected = lambda: True
    harness._last_heartbeat_at.clear()
    asyncio.run(harness._async_maybe_recover_direct_stream("private-device"))
    harness._async_reconnect_direct_stream.assert_not_awaited()
    assert [e["reason"] for e in harness._stream_timeline.snapshot()["events"]] == [
        "disconnected", "streams_not_started"]


def test_connection_callback_is_queued_and_retains_transition_not_current_state():
    harness = coordinator_harness()
    queued = []
    harness.hass = SimpleNamespace(loop=SimpleNamespace(
        call_soon_threadsafe=lambda *args: queued.append(args)))
    harness._schedule_mqtt_status("private-device", "disconnected", 7)
    assert harness._stream_timeline.snapshot()["events"] == []
    callback, *args = queued.pop()
    callback(*args)
    event = harness._stream_timeline.snapshot()["events"][0]
    assert event["connected"] is False
    assert event["reason_code"] == 7
    assert "private-device" not in json.dumps(event)


def test_recovery_error_is_recorded_and_cooldown_retained():
    harness = coordinator_harness()
    harness._async_reconnect_direct_stream.side_effect = RuntimeError("secret details")
    asyncio.run(harness._async_maybe_recover_direct_stream("private-device"))
    snapshot = harness._stream_timeline.snapshot()
    assert snapshot["events"][-1]["reason"] == "error"
    assert "secret details" not in json.dumps(snapshot)
    assert harness._last_automatic_reconnect_at["private-device"] == 1000
