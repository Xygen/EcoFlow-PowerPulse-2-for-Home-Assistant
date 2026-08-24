from __future__ import annotations

import asyncio

import pytest

from custom_components.ecoflow_powerpulse2.passive_refresh import (
    ConfirmedSettingsReplyGate,
    DelayedRefreshCoalescer,
)


def _command_frame(
    channel: str,
    *,
    sequence: int,
    cmd_func: int = 241,
    cmd_id: int = 102,
    source_role: str = "powerocean_observer",
    device_prefix: str = "HJ31",
) -> dict:
    return {
        "channel": channel,
        "source_role": source_role,
        "device_prefix": device_prefix,
        "protocol_headers": [
            {"cmd_func": cmd_func, "cmd_id": cmd_id, "sequence": sequence}
        ],
    }


def test_settings_reply_gate_requires_matching_request_and_source() -> None:
    gate = ConfirmedSettingsReplyGate()

    assert not gate.observe(_command_frame("set_reply", sequence=1))
    assert not gate.observe(_command_frame("observed_set", sequence=2))
    assert not gate.observe(
        _command_frame("set_reply", sequence=2, device_prefix="J32D")
    )
    assert gate.observe(_command_frame("set_reply", sequence=2))
    assert not gate.observe(_command_frame("set_reply", sequence=2))


def test_settings_reply_gate_ignores_other_commands_and_direct_devices() -> None:
    gate = ConfirmedSettingsReplyGate()

    assert not gate.observe(
        _command_frame("observed_set", sequence=3, cmd_func=96, cmd_id=97)
    )
    assert not gate.observe(
        _command_frame("set_reply", sequence=3, cmd_func=96, cmd_id=97)
    )
    assert not gate.observe(
        _command_frame("observed_set", sequence=4, source_role="powerpulse")
    )
    assert not gate.observe(
        _command_frame("set_reply", sequence=4, source_role="powerpulse")
    )


@pytest.mark.asyncio
async def test_delayed_refresh_coalesces_requests_before_refresh() -> None:
    refresh_count = 0
    refreshed = asyncio.Event()

    async def refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1
        refreshed.set()

    coalescer = DelayedRefreshCoalescer(refresh, delay_seconds=0)
    assert coalescer.request()
    assert not coalescer.request()
    await asyncio.wait_for(refreshed.wait(), timeout=1)
    await asyncio.sleep(0)

    assert refresh_count == 1
    await coalescer.async_close()


@pytest.mark.asyncio
async def test_delayed_refresh_runs_again_for_request_during_http_read() -> None:
    refresh_count = 0
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_completed = asyncio.Event()

    async def refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1
        if refresh_count == 1:
            first_started.set()
            await release_first.wait()
        else:
            second_completed.set()

    coalescer = DelayedRefreshCoalescer(refresh, delay_seconds=0)
    assert coalescer.request()
    await asyncio.wait_for(first_started.wait(), timeout=1)
    assert not coalescer.request()
    release_first.set()
    await asyncio.wait_for(second_completed.wait(), timeout=1)

    assert refresh_count == 2
    await coalescer.async_close()
