"""Read-only refresh helpers for confirmed official-app setting changes."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

_SETTINGS_COMMAND = (241, 102)


class ConfirmedSettingsReplyGate:
    """Match one PowerOcean settings reply to a previously observed request."""

    def __init__(self, *, max_pending: int = 32) -> None:
        self._max_pending = max_pending
        self._pending: OrderedDict[tuple[str, str, int], None] = OrderedDict()

    def observe(self, frame: dict[str, Any]) -> bool:
        """Return true once for a matching 241/102 request/reply sequence."""
        channel = str(frame.get("channel", ""))
        if channel not in {"observed_set", "set_reply"}:
            return False
        if frame.get("source_role") != "powerocean_observer":
            return False

        matched = False
        for key in self._matching_keys(frame):
            if channel == "observed_set":
                self._pending[key] = None
                self._pending.move_to_end(key)
                while len(self._pending) > self._max_pending:
                    self._pending.popitem(last=False)
            elif key in self._pending:
                self._pending.pop(key)
                matched = True
        return matched

    @staticmethod
    def _matching_keys(frame: dict[str, Any]) -> list[tuple[str, str, int]]:
        headers = frame.get("protocol_headers")
        if not isinstance(headers, list):
            return []

        source_role = str(frame.get("source_role", ""))
        device_prefix = str(frame.get("device_prefix", ""))
        keys: list[tuple[str, str, int]] = []
        for header in headers:
            if not isinstance(header, dict):
                continue
            if (header.get("cmd_func"), header.get("cmd_id")) != _SETTINGS_COMMAND:
                continue
            sequence = header.get("sequence")
            if isinstance(sequence, int):
                keys.append((source_role, device_prefix, sequence))
        return keys


class DelayedRefreshCoalescer:
    """Run one delayed refresh and coalesce requests received before it starts."""

    def __init__(
        self,
        refresh: Callable[[], Awaitable[None]],
        *,
        delay_seconds: float,
    ) -> None:
        self._refresh = refresh
        self._delay_seconds = delay_seconds
        self._pending = False
        self._closed = False
        self._task: asyncio.Task[None] | None = None

    @property
    def active(self) -> bool:
        """Return whether a delayed or running refresh task exists."""
        return self._task is not None and not self._task.done()

    @property
    def pending(self) -> bool:
        """Return whether another refresh was requested during the current one."""
        return self._pending

    def request(self) -> bool:
        """Schedule or coalesce a refresh; return true when a task was created."""
        if self._closed:
            return False
        self._pending = True
        if self.active:
            return False
        self._task = asyncio.create_task(self._run())
        return True

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._delay_seconds)
                # Requests received before the refresh starts are represented by
                # the state fetched now. Only a request received while the HTTP
                # refresh is running requires one further bounded pass.
                self._pending = False
                await self._refresh()
                if not self._pending:
                    return
        finally:
            self._task = None

    async def async_close(self) -> None:
        """Cancel any delayed work and reject new refresh requests."""
        self._closed = True
        self._pending = False
        task = self._task
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
