"""Broker address named by an MQTT credential response.

Both credential endpoints answer with the broker the account is supposed to
use: ``url``, ``port``, ``protocol`` and ``path``. This integration read only
the account and the password out of that answer and connected to a
compile-time constant instead, which works for exactly as long as every
account lives in the region that constant points at.

The failure mode when it does not is silent by construction: the socket opens,
the broker closes it without a CONNACK, and paho reports a plain disconnect.
Nothing in that sequence names a region. It matters most right after a
credential refresh, because a renewed certificate can name a different server,
and adopting the credentials while keeping the old address is the one
combination that cannot work.

The decision rules follow the fix recorded as issue #184 in ecoflow-energy-ha,
which this repository already credits in `NOTICE`. Values are validated rather
than trusted: anything missing or malformed falls back to the constants, which
is the behaviour that was correct for this account before this module existed.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from .const import MQTT_HOST, MQTT_PORT_TCP, MQTT_PORT_WSS, MQTT_WSS_PATH

_URL_PREFIXES = ("wss://", "ws://", "mqtts://", "mqtt://", "ssl://", "tcp://")
_ENCRYPTED_WEBSOCKET = ("wss", "websockets")
_ENCRYPTED_SOCKET = ("mqtts", "ssl", "tls")
_PLAINTEXT = ("ws", "websocket", "mqtt", "tcp")


class BrokerAddress(NamedTuple):
    """Where to reach the broker for one set of credentials."""

    host: str
    port: int
    path: str

    def __str__(self) -> str:
        """Return ``host:port``, which is safe to log and to export.

        A hostname and a port are public infrastructure. The certificate
        account arrives in the same response and is not.
        """
        return f"{self.host}:{self.port}"


def broker_from_credentials(
    credentials: dict[str, Any] | None, *, wss_mode: bool
) -> BrokerAddress:
    """Return the broker named by a credential response.

    ``wss_mode`` decides which default port applies and is also what the
    caller already used to pick a transport, so the response's own
    ``protocol`` never overrides it: the transport choice belongs to the
    connection, not to the answer.
    """
    default_port = MQTT_PORT_WSS if wss_mode else MQTT_PORT_TCP
    if not credentials:
        return BrokerAddress(MQTT_HOST, default_port, MQTT_WSS_PATH)

    host = _clean_host(credentials.get("url")) or MQTT_HOST
    path = _clean_path(credentials.get("path")) or MQTT_WSS_PATH
    # A port belongs to the protocol it was quoted for. Dialling a port taken
    # from a plaintext answer over an encrypted socket would be a worse
    # address than the default, and would reproduce exactly the silent failure
    # this module exists to remove.
    if _protocol_matches(credentials.get("protocol"), wss_mode=wss_mode):
        port = _clean_port(credentials.get("port")) or default_port
    else:
        port = default_port
    return BrokerAddress(host, port, path)


def _protocol_matches(value: Any, *, wss_mode: bool) -> bool:
    """Return whether the named protocol is the one this client speaks.

    Encryption counts as part of the answer, not only the transport. Every
    connection here calls ``tls_set`` unconditionally, so a port quoted for a
    plaintext protocol is one this client cannot use. An answer that names no
    protocol is taken at its word, which is how this behaved before.
    """
    if not isinstance(value, str) or not value.strip():
        return True
    protocol = value.strip().lower().rstrip(":/")
    if protocol in _ENCRYPTED_WEBSOCKET:
        return wss_mode
    if protocol in _ENCRYPTED_SOCKET:
        return not wss_mode
    return protocol not in _PLAINTEXT


def _clean_host(value: Any) -> str:
    """Return a bare hostname, or an empty string if the value is not one."""
    if not isinstance(value, str):
        return ""
    host = value.strip()
    # Some responses spell the broker as a URL rather than a hostname.
    for prefix in _URL_PREFIXES:
        if host.lower().startswith(prefix):
            host = host[len(prefix) :]
            break
    host = host.split("/", 1)[0]
    # Userinfo would be account data, and the resolved address is exported in
    # a diagnostics download that people attach to public issues.
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    if not host or " " in host or "." not in host:
        return ""
    return host


def _clean_port(value: Any) -> int:
    """Return a usable TCP port, or 0 if the value is not one."""
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 0
    return port if 0 < port <= 65535 else 0


def _clean_path(value: Any) -> str:
    """Return a websocket path, or an empty string if the value is not one."""
    if not isinstance(value, str):
        return ""
    path = value.strip()
    if not path:
        return ""
    return path if path.startswith("/") else f"/{path}"
