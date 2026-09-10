"""The MQTT client dials the broker its credentials name, and reports refusals."""

from __future__ import annotations

import pytest

from custom_components.ecoflow_powerpulse2.ecoflow import cloud_mqtt
from custom_components.ecoflow_powerpulse2.ecoflow.broker import BrokerAddress
from custom_components.ecoflow_powerpulse2.ecoflow.cloud_mqtt import EcoFlowMQTTClient
from custom_components.ecoflow_powerpulse2.ecoflow.const import (
    MQTT_HOST,
    MQTT_PORT_WSS,
    MQTT_WSS_PATH,
)


class _Paho:
    """Records what the client asks of paho without touching a socket."""

    def __init__(self) -> None:
        self.connects: list[tuple[str, int, int]] = []
        self.ws_paths: list[str] = []
        self.credentials: list[tuple[str, str]] = []

    def connect(self, host: str, port: int, keepalive: int) -> None:
        self.connects.append((host, port, keepalive))

    def username_pw_set(self, account: str, password: str) -> None:
        self.credentials.append((account, password))

    def ws_set_options(self, path: str) -> None:
        self.ws_paths.append(path)

    def tls_set(self, **_kwargs: object) -> None:
        pass

    def is_connected(self) -> bool:
        return False

    def loop_start(self) -> None:
        pass

    def loop_stop(self) -> None:
        pass

    def disconnect(self) -> None:
        pass


def _client(**kwargs: object) -> EcoFlowMQTTClient:
    return EcoFlowMQTTClient(
        certificate_account="account",
        certificate_password="password",
        device_sn="C376-test",
        message_handler=lambda topic, payload: None,
        user_id="42",
        listen_only=True,
        **kwargs,
    )


def test_default_address_is_the_built_in_one() -> None:
    client = _client()
    client.client = _Paho()
    client.connect()
    assert client.client.connects[0][:2] == (MQTT_HOST, MQTT_PORT_WSS)


def test_adopted_address_is_the_one_dialled() -> None:
    """A renewed certificate can be issued for a different server.

    Keeping the previous address while adopting the credentials fails without
    a CONNACK and without any message naming a cause.
    """
    client = _client()
    moved = client.update_broker(BrokerAddress("mqtt-a.ecoflow.com", 443, "/ws"))
    assert moved is True
    client.client = _Paho()
    client.connect()
    assert client.client.connects[0][:2] == ("mqtt-a.ecoflow.com", 443)


def test_readopting_the_same_address_reports_no_change() -> None:
    """The caller rebuilds the session on a change; an unchanged address must
    not cost a healthy connection its data."""
    client = _client()
    assert client.update_broker(BrokerAddress(MQTT_HOST, MQTT_PORT_WSS, MQTT_WSS_PATH)) is False


@pytest.fixture
def recorded_paho(monkeypatch):
    """Make the client build a recorder instead of a real paho client."""
    built: list[_Paho] = []

    def factory(*_args: object, **_kwargs: object) -> _Paho:
        built.append(_Paho())
        return built[-1]

    monkeypatch.setattr(cloud_mqtt.mqtt, "Client", factory)
    return built


def test_adopted_websocket_path_reaches_the_new_client(recorded_paho) -> None:
    client = _client()
    client.update_broker(BrokerAddress("mqtt-a.ecoflow.com", 443, "/ws"))
    assert client.create_client() is True
    assert recorded_paho[-1].ws_paths == ["/ws"]


def test_default_websocket_path_is_used_when_none_was_named(recorded_paho) -> None:
    client = _client()
    assert client.create_client() is True
    assert recorded_paho[-1].ws_paths == [MQTT_WSS_PATH]


def test_force_reconnect_dials_the_adopted_address(recorded_paho) -> None:
    client = _client()
    client.update_broker(BrokerAddress("mqtt-a.ecoflow.com", 443, "/ws"))
    assert client.create_client() is True
    assert client.force_reconnect() is True
    assert recorded_paho[-1].connects[-1][:2] == ("mqtt-a.ecoflow.com", 443)
    assert recorded_paho[-1].ws_paths == ["/ws"]


@pytest.mark.parametrize("reason_code", [4, 5, 134, 135])
def test_a_refused_certificate_reaches_the_handler(reason_code: int) -> None:
    """This detection always existed; nothing consumed it until now."""
    seen: list[bool] = []
    client = _client(auth_error_handler=lambda: seen.append(True))
    client._on_connect(None, None, None, reason_code)
    assert seen == [True]
    assert client.connected is False


@pytest.mark.parametrize("reason_code", [1, 2, 3])
def test_a_non_credential_refusal_does_not_ask_for_a_certificate(
    reason_code: int,
) -> None:
    seen: list[bool] = []
    client = _client(auth_error_handler=lambda: seen.append(True))
    client._on_connect(None, None, None, reason_code)
    assert seen == []


def test_updated_credentials_reach_the_live_client() -> None:
    client = _client()
    recorder = _Paho()
    client.client = recorder
    client.update_credentials("new-account", "new-password")
    assert client.cert_account == "new-account"
    assert recorder.credentials == [("new-account", "new-password")]
