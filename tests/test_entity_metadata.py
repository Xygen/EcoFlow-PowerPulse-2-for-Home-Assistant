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


def _descriptions(path: str, constructor: str) -> dict[str, dict[str, str | None]]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    descriptions: dict[str, dict[str, str | None]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _qualified_name(node.func) != constructor:
            continue
        keywords = {item.arg: item.value for item in node.keywords if item.arg}
        key = keywords.get("key")
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        descriptions[key.value] = {
            name: _qualified_name(value) for name, value in keywords.items()
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
