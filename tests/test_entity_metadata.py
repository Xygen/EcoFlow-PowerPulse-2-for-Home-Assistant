import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _qualified_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _metadata_value(node: ast.expr) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    return _qualified_name(node)


def _descriptions(path: str, constructor: str) -> dict[str, dict[str, object]]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    descriptions: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _qualified_name(node.func) != constructor:
            continue
        keywords = {item.arg: item.value for item in node.keywords if item.arg}
        key = keywords.get("key")
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        descriptions[key.value] = {
            name: _metadata_value(value) for name, value in keywords.items()
        }
    return descriptions


def test_smart_distance_sensor_uses_native_distance_metadata() -> None:
    descriptions = _descriptions(
        "custom_components/ecoflow_powerpulse2/const.py",
        "PowerPulse2SensorDescription",
    )
    smart_distance = descriptions["smart_target_distance_km"]
    assert smart_distance["device_class"] == "SensorDeviceClass.DISTANCE"
    assert smart_distance["native_unit_of_measurement"] == "UnitOfLength.KILOMETERS"
    assert "state_class" not in smart_distance


def test_number_controls_use_native_device_classes_and_units() -> None:
    descriptions = _descriptions(
        "custom_components/ecoflow_powerpulse2/number.py", "NumberEntityDescription"
    )
    for key in (
        "maximum_output_current_control",
        "solar_minimum_current_control",
        "custom_current_control",
    ):
        assert descriptions[key]["device_class"] == "NumberDeviceClass.CURRENT"
        assert (
            descriptions[key]["native_unit_of_measurement"]
            == "UnitOfElectricCurrent.AMPERE"
        )
    assert (
        descriptions["smart_energy_target_control"]["device_class"]
        == "NumberDeviceClass.ENERGY"
    )
    assert (
        descriptions["smart_energy_target_control"]["native_unit_of_measurement"]
        == "UnitOfEnergy.KILO_WATT_HOUR"
    )
    assert (
        descriptions["smart_distance_target_control"]["device_class"]
        == "NumberDeviceClass.DISTANCE"
    )
    assert (
        descriptions["smart_distance_target_control"]["native_unit_of_measurement"]
        == "UnitOfLength.KILOMETERS"
    )


def test_screen_and_indicator_controls_are_configuration_entities() -> None:
    numbers = _descriptions(
        "custom_components/ecoflow_powerpulse2/number.py", "NumberEntityDescription"
    )
    switches = _descriptions(
        "custom_components/ecoflow_powerpulse2/switch.py", "SwitchEntityDescription"
    )
    for description in (
        numbers["screen_brightness_control"],
        numbers["indicator_brightness_control"],
        switches["screen_control"],
        switches["indicator_control"],
    ):
        assert description["entity_category"] == "EntityCategory.CONFIG"
    assert (
        numbers["screen_brightness_control"]["native_unit_of_measurement"]
        == "PERCENTAGE"
    )
    assert (
        numbers["indicator_brightness_control"]["native_unit_of_measurement"]
        == "PERCENTAGE"
    )


def test_canonical_setting_sensors_declare_their_observation_keys() -> None:
    descriptions = _descriptions(
        "custom_components/ecoflow_powerpulse2/const.py",
        "PowerPulse2SensorDescription",
    )
    expected = {
        "work_mode": "work_mode",
        "ready_by_timestamp": "ready_by_timestamp",
        "smart_charge_target_wh": "smart_charge_target_wh",
        "smart_target_type": "smart_target_type",
        "smart_target_distance_km": "smart_target_distance_km",
        "current_limit_raw": "current_limit_raw",
        "user_current_set_a": "user_current_set_raw",
        "solar_minimum_current_a": "solar_current_min_raw",
        "phase_mode": "phase_mode",
        "screen_brightness_pct": "screen_brightness_pct",
        "indicator_brightness_pct": "indicator_brightness_pct",
    }

    for key, observation_key in expected.items():
        assert descriptions[key]["setting_observation_key"] == observation_key


def test_smart_energy_target_is_canonical_not_diagnostic() -> None:
    descriptions = _descriptions(
        "custom_components/ecoflow_powerpulse2/const.py",
        "PowerPulse2SensorDescription",
    )
    smart_target = descriptions["smart_charge_target_wh"]

    assert "diagnostic" not in smart_target
    assert "entity_registry_enabled_default" not in smart_target


def test_setting_entity_roles_match_the_classification_matrix() -> None:
    sensors = _descriptions(
        "custom_components/ecoflow_powerpulse2/const.py",
        "PowerPulse2SensorDescription",
    )
    for key in (
        "current_limit_raw",
        "user_current_set_a",
        "solar_minimum_current_a",
        "phase_mode",
        "screen_brightness_pct",
        "indicator_brightness_pct",
    ):
        assert sensors[key]["diagnostic"] is True

    binary_sensors = _descriptions(
        "custom_components/ecoflow_powerpulse2/binary_sensor.py",
        "BinarySensorEntityDescription",
    )
    assert "entity_category" not in binary_sensors["continuous_charging"]
    for key in (
        "plug_and_play",
        "battery_discharge_disabled",
        "screen_enabled",
        "indicator_enabled",
    ):
        assert binary_sensors[key]["entity_category"] == "EntityCategory.DIAGNOSTIC"

    numbers = _descriptions(
        "custom_components/ecoflow_powerpulse2/number.py", "NumberEntityDescription"
    )
    for key in (
        "maximum_output_current_control",
        "solar_minimum_current_control",
        "custom_current_control",
        "screen_brightness_control",
        "indicator_brightness_control",
    ):
        assert numbers[key]["entity_category"] == "EntityCategory.CONFIG"
    assert "entity_category" not in numbers["smart_energy_target_control"]
    assert "entity_category" not in numbers["smart_distance_target_control"]

    switches = _descriptions(
        "custom_components/ecoflow_powerpulse2/switch.py", "SwitchEntityDescription"
    )
    assert "entity_category" not in switches["continuous_charging_control"]
    for key in (
        "battery_discharge_control",
        "plug_and_play_control",
        "screen_control",
        "indicator_control",
    ):
        assert switches[key]["entity_category"] == "EntityCategory.CONFIG"

    select_source = (
        ROOT / "custom_components/ecoflow_powerpulse2/select.py"
    ).read_text(encoding="utf-8")
    assert "_attr_entity_category = EntityCategory.CONFIG" in select_source
