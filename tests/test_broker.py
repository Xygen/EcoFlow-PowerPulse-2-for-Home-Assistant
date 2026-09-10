"""Decision tests for the broker address named by a credential response."""

from __future__ import annotations

import pytest

from custom_components.ecoflow_powerpulse2.ecoflow.broker import (
    BrokerAddress,
    broker_from_credentials,
)
from custom_components.ecoflow_powerpulse2.ecoflow.const import (
    MQTT_HOST,
    MQTT_PORT_TCP,
    MQTT_PORT_WSS,
    MQTT_WSS_PATH,
)

DEFAULT_WSS = BrokerAddress(MQTT_HOST, MQTT_PORT_WSS, MQTT_WSS_PATH)


@pytest.mark.parametrize("credentials", [None, {}, {"url": None}, {"url": ""}])
def test_missing_address_keeps_the_built_in_default(credentials: dict | None) -> None:
    """The constants were correct for every account before this existed."""
    assert broker_from_credentials(credentials, wss_mode=True) == DEFAULT_WSS


def test_named_address_is_adopted() -> None:
    broker = broker_from_credentials(
        {"url": "mqtt-a.ecoflow.com", "port": 8084, "path": "/mqtt", "protocol": "wss"},
        wss_mode=True,
    )
    assert broker == BrokerAddress("mqtt-a.ecoflow.com", 8084, "/mqtt")


@pytest.mark.parametrize(
    "url",
    [
        "wss://mqtt-a.ecoflow.com/mqtt",
        "mqtts://mqtt-a.ecoflow.com",
        "mqtt-a.ecoflow.com:8084",
        "  mqtt-a.ecoflow.com  ",
    ],
)
def test_host_is_extracted_from_the_spellings_the_service_uses(url: str) -> None:
    assert broker_from_credentials({"url": url}, wss_mode=True).host == "mqtt-a.ecoflow.com"


def test_userinfo_is_never_carried_into_the_address() -> None:
    """The resolved address is exported in a diagnostics download."""
    broker = broker_from_credentials(
        {"url": "wss://account:secret@mqtt-a.ecoflow.com/mqtt"}, wss_mode=True
    )
    assert broker.host == "mqtt-a.ecoflow.com"
    assert "secret" not in str(broker)
    assert "account" not in str(broker)


@pytest.mark.parametrize("url", ["localhost", "not a host", "/mqtt", 42, ["host"]])
def test_unusable_host_falls_back_rather_than_being_dialled(url: object) -> None:
    assert broker_from_credentials({"url": url}, wss_mode=True).host == MQTT_HOST


@pytest.mark.parametrize("port", [0, -1, 70000, "abc", None, 1.5e9])
def test_unusable_port_falls_back_to_the_default(port: object) -> None:
    broker = broker_from_credentials({"url": "mqtt-a.ecoflow.com", "port": port}, wss_mode=True)
    assert broker.port == MQTT_PORT_WSS


def test_port_quoted_for_plaintext_is_not_dialled_over_tls() -> None:
    """Every connection here calls tls_set, so such a port cannot work.

    Adopting it would reproduce the silent failure this module removes: the
    socket opens, nothing answers, and the retry loop starts.
    """
    broker = broker_from_credentials(
        {"url": "mqtt-a.ecoflow.com", "port": 1883, "protocol": "mqtt"}, wss_mode=False
    )
    assert broker.port == MQTT_PORT_TCP


def test_port_quoted_for_the_other_transport_is_not_adopted() -> None:
    broker = broker_from_credentials(
        {"url": "mqtt-a.ecoflow.com", "port": 8883, "protocol": "mqtts"}, wss_mode=True
    )
    assert broker.port == MQTT_PORT_WSS


@pytest.mark.parametrize("protocol", [None, "", "   ", 7])
def test_port_is_taken_at_its_word_when_no_protocol_is_named(protocol: object) -> None:
    broker = broker_from_credentials(
        {"url": "mqtt-a.ecoflow.com", "port": 8084, "protocol": protocol}, wss_mode=True
    )
    assert broker.port == 8084


@pytest.mark.parametrize(
    ("path", "expected"), [("mqtt", "/mqtt"), ("/ws", "/ws"), ("", MQTT_WSS_PATH), (5, MQTT_WSS_PATH)]
)
def test_websocket_path_is_normalised(path: object, expected: str) -> None:
    broker = broker_from_credentials({"url": "mqtt-a.ecoflow.com", "path": path}, wss_mode=True)
    assert broker.path == expected


def test_plain_transport_defaults_to_its_own_port() -> None:
    assert broker_from_credentials(None, wss_mode=False).port == MQTT_PORT_TCP


def test_address_prints_as_public_infrastructure_only() -> None:
    assert str(BrokerAddress("mqtt-a.ecoflow.com", 8084, "/mqtt")) == "mqtt-a.ecoflow.com:8084"
