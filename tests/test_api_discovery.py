from __future__ import annotations

from custom_components.ecoflow_powerpulse2.discovery import classify_device_records


def test_classifies_powerpulse_and_powerocean_serial_keyed_devices() -> None:
    chargers, observers = classify_device_records(
        {
            "bound": {
                "C376-CHARGER": {
                    "deviceName": "Garage wallbox",
                    "productType": 123,
                },
                "HJ31-PARENT": {
                    "productName": "PowerOcean",
                    "productType": 456,
                },
                "HW52-PLUG": {"productName": "Smart Plug"},
            },
            "share": {},
        }
    )

    assert set(chargers) == {"C376-CHARGER"}
    assert chargers["C376-CHARGER"]["name"] == "Garage wallbox"
    assert chargers["C376-CHARGER"]["product_type"] == "123"
    assert set(observers) == {"HJ31-PARENT"}
    assert observers["HJ31-PARENT"]["name"] == "PowerOcean"
    assert observers["HJ31-PARENT"]["product_type"] == "456"


def test_classifies_list_based_account_device_response() -> None:
    chargers, observers = classify_device_records(
        {
            "bound": {
                "group": [
                    {"sn": "C376-LIST", "productName": "PowerPulse 2"},
                    {"sn": "J32D-LIST", "productName": "PowerOcean"},
                ]
            }
        }
    )

    assert set(chargers) == {"C376-LIST"}
    assert set(observers) == {"J32D-LIST"}
