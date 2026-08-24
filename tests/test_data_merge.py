from __future__ import annotations

import asyncio

import pytest

from custom_components.ecoflow_powerpulse2.data_merge import merge_snapshot_after_read


@pytest.mark.asyncio
async def test_merge_uses_mqtt_values_received_during_http_poll() -> None:
    latest: dict[str, float] = {}
    poll_started = asyncio.Event()
    finish_poll = asyncio.Event()

    async def read_snapshot() -> dict[str, float]:
        poll_started.set()
        await finish_poll.wait()
        return {"charging_power_w": 222.0}

    merge_task = asyncio.create_task(
        merge_snapshot_after_read(read_snapshot, lambda: latest)
    )
    await poll_started.wait()

    latest.update({"charging_power_w": 111.0, "phase_voltage_v": 230.4})
    finish_poll.set()

    assert await merge_task == {
        "charging_power_w": 222.0,
        "phase_voltage_v": 230.4,
    }


@pytest.mark.asyncio
async def test_merge_can_prefer_selected_recent_mqtt_values() -> None:
    latest = {"charging_power_w": 111.0, "solar_current_min_raw": 70}

    async def read_snapshot() -> dict[str, float]:
        return {"charging_power_w": 222.0, "solar_current_min_raw": 60}

    result = await merge_snapshot_after_read(
        read_snapshot,
        lambda: latest,
        lambda: {"solar_current_min_raw"},
    )

    assert result == {
        "charging_power_w": 222.0,
        "solar_current_min_raw": 70,
    }
