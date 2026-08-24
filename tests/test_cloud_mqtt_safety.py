from __future__ import annotations

from custom_components.ecoflow_powerpulse2.ecoflow.cloud_mqtt import EcoFlowMQTTClient


class _UnexpectedPublisher:
    def __init__(self) -> None:
        self.subscriptions: list[tuple[str, int]] = []

    def subscribe(self, topic: str, qos: int) -> None:
        self.subscriptions.append((topic, qos))

    def publish(self, *args, **kwargs):
        raise AssertionError("listen-only client reached the Paho publish method")


class _ExplicitPublisher(_UnexpectedPublisher):
    def __init__(self) -> None:
        super().__init__()
        self.published: list[tuple[str, bytes, int]] = []

    def publish(self, topic: str, payload: bytes, qos: int):
        self.published.append((topic, payload, qos))
        return type("Result", (), {"rc": 0})()

    def is_connected(self) -> bool:
        return True


def _client() -> EcoFlowMQTTClient:
    return EcoFlowMQTTClient(
        certificate_account="account-secret",
        certificate_password="password-secret",
        device_sn="C376-secret",
        message_handler=lambda topic, payload: None,
        user_id="user-secret",
        listen_only=True,
    )


def test_listen_only_publish_never_reaches_paho() -> None:
    client = _client()
    client.client = _UnexpectedPublisher()
    client.connected = True

    assert not client.publish(
        "/app/user-secret/C376-secret/thing/property/set",
        b"must-not-leave",
    )


def test_explicit_control_is_the_only_listen_only_publish_escape_hatch() -> None:
    client = _client()
    publisher = _ExplicitPublisher()
    client.client = publisher
    client.connected = True

    assert client.send_explicit_control(b"validated-control")
    assert publisher.published == [
        (
            "/app/user-secret/C376-secret/thing/property/set",
            b"validated-control",
            1,
        )
    ]


def test_listen_only_connect_only_subscribes() -> None:
    client = _client()
    paho_client = _UnexpectedPublisher()

    client._on_connect(paho_client, None, None, 0)  # noqa: SLF001

    assert client.connected
    assert len(paho_client.subscriptions) == 11
    assert any(topic.endswith("/thing/property/set") for topic, _ in paho_client.subscriptions)
    assert any(topic.endswith("/set") and "/open/" in topic for topic, _ in paho_client.subscriptions)
    assert any(topic.endswith("/app/device/property/C376-secret/set") for topic, _ in paho_client.subscriptions)
    assert set(client.subscription_results) == {
        "app_get_reply",
        "app_set",
        "app_set_reply",
        "device_property",
        "device_property_children",
        "device_property_set",
        "open_device_children",
        "open_set",
        "open_set_reply",
        "quota",
        "app_device_all",
    }


def test_mqtt_topic_log_masking() -> None:
    client = _client()

    assert client._masked_topic(  # noqa: SLF001 - explicit privacy regression test
        "/open/account-secret/C376-secret/user-secret/quota"
    ) == "/open/<account>/<device>/<user>/quota"

    assert client.diagnostic_topic(
        "/app/user-secret/C376-secret/thing/property/custom"
    ) == "/app/<user>/<device>/thing/property/custom"
