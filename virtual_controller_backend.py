"""Persist and validate ViGEm virtual gamepad bindings on Windows/Linux."""

from __future__ import annotations

import json
import logging
from typing import Dict

from app_paths import config_file

logger = logging.getLogger(__name__)

CONFIG_PATH = config_file("VirtualControllerMappings.json")

DEFAULT_VIRTUAL_MAPS: Dict[str, Dict[str, str]] = {
    "GBAController": {
        "up": "XUSB_GAMEPAD_DPAD_UP",
        "down": "XUSB_GAMEPAD_DPAD_DOWN",
        "left": "XUSB_GAMEPAD_DPAD_LEFT",
        "right": "XUSB_GAMEPAD_DPAD_RIGHT",
        "a": "XUSB_GAMEPAD_A",
        "b": "XUSB_GAMEPAD_B",
        "l": "XUSB_GAMEPAD_X",
        "r": "XUSB_GAMEPAD_Y",
        "select": "XUSB_GAMEPAD_BACK",
        "start": "XUSB_GAMEPAD_START",
    },
    "XboxController": {
        "updpad": "XUSB_GAMEPAD_DPAD_UP",
        "downdpad": "XUSB_GAMEPAD_DPAD_DOWN",
        "leftdpad": "XUSB_GAMEPAD_DPAD_LEFT",
        "rightdpad": "XUSB_GAMEPAD_DPAD_RIGHT",
        "a": "XUSB_GAMEPAD_A",
        "b": "XUSB_GAMEPAD_B",
        "x": "XUSB_GAMEPAD_X",
        "y": "XUSB_GAMEPAD_Y",
        "back": "XUSB_GAMEPAD_BACK",
        "start": "XUSB_GAMEPAD_START",
        "home": "XUSB_GAMEPAD_GUIDE",
        "lb": "XUSB_GAMEPAD_LEFT_SHOULDER",
        "rb": "XUSB_GAMEPAD_RIGHT_SHOULDER",
        "lstick": "left_joystick_float",
        "rstick": "right_joystick_float",
        "lt": "left_trigger_float",
        "rt": "right_trigger_float",
    },
    "PlayStationController": {
        "up": "DS4_BUTTON_DPAD_NORTH",
        "down": "DS4_BUTTON_DPAD_SOUTH",
        "left": "DS4_BUTTON_DPAD_WEST",
        "right": "DS4_BUTTON_DPAD_EAST",
        "x": "DS4_BUTTON_CROSS",
        "sq": "DS4_BUTTON_SQUARE",
        "cir": "DS4_BUTTON_CIRCLE",
        "tri": "DS4_BUTTON_TRIANGLE",
        "select": "DS4_BUTTON_OPTIONS",
        "start": "DS4_BUTTON_SHARE",
        "l1": "DS4_BUTTON_SHOULDER_LEFT",
        "r1": "DS4_BUTTON_SHOULDER_RIGHT",
        "l2": "DS4_BUTTON_TRIGGER_LEFT",
        "r2": "DS4_BUTTON_TRIGGER_RIGHT",
        "lstick": "left_joystick_float",
        "rstick": "right_joystick_float",
    },
}

ANALOG_VIRTUAL_METHODS = frozenset({
    "left_joystick_float",
    "right_joystick_float",
    "left_trigger_float",
    "right_trigger_float",
})

XBOX_VIRTUAL_INPUTS: tuple[str, ...] = tuple(sorted((
    "XUSB_GAMEPAD_A",
    "XUSB_GAMEPAD_B",
    "XUSB_GAMEPAD_BACK",
    "XUSB_GAMEPAD_DPAD_DOWN",
    "XUSB_GAMEPAD_DPAD_LEFT",
    "XUSB_GAMEPAD_DPAD_RIGHT",
    "XUSB_GAMEPAD_DPAD_UP",
    "XUSB_GAMEPAD_GUIDE",
    "XUSB_GAMEPAD_LEFT_SHOULDER",
    "XUSB_GAMEPAD_LEFT_THUMB",
    "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "XUSB_GAMEPAD_RIGHT_THUMB",
    "XUSB_GAMEPAD_START",
    "XUSB_GAMEPAD_X",
    "XUSB_GAMEPAD_Y",
    *ANALOG_VIRTUAL_METHODS,
)))

GBA_VIRTUAL_INPUTS: tuple[str, ...] = tuple(sorted(
    name for name in XBOX_VIRTUAL_INPUTS if name not in ANALOG_VIRTUAL_METHODS
))

PLAYSTATION_ANALOG_METHODS = frozenset({
    "left_joystick_float",
    "right_joystick_float",
})

PLAYSTATION_VIRTUAL_INPUTS: tuple[str, ...] = tuple(sorted((
    "DS4_BUTTON_CIRCLE",
    "DS4_BUTTON_CROSS",
    "DS4_BUTTON_DPAD_EAST",
    "DS4_BUTTON_DPAD_NORTH",
    "DS4_BUTTON_DPAD_NORTHEAST",
    "DS4_BUTTON_DPAD_NORTHWEST",
    "DS4_BUTTON_DPAD_SOUTH",
    "DS4_BUTTON_DPAD_SOUTHEAST",
    "DS4_BUTTON_DPAD_SOUTHWEST",
    "DS4_BUTTON_DPAD_WEST",
    "DS4_BUTTON_OPTIONS",
    "DS4_BUTTON_SHARE",
    "DS4_BUTTON_SHOULDER_LEFT",
    "DS4_BUTTON_SHOULDER_RIGHT",
    "DS4_BUTTON_SQUARE",
    "DS4_BUTTON_THUMB_LEFT",
    "DS4_BUTTON_THUMB_RIGHT",
    "DS4_BUTTON_TRIANGLE",
    "DS4_BUTTON_TRIGGER_LEFT",
    "DS4_BUTTON_TRIGGER_RIGHT",
    *PLAYSTATION_ANALOG_METHODS,
)))

XBOX_VIRTUAL_INPUTS_SET = frozenset(XBOX_VIRTUAL_INPUTS)
GBA_VIRTUAL_INPUTS_SET = frozenset(GBA_VIRTUAL_INPUTS)
PLAYSTATION_VIRTUAL_INPUTS_SET = frozenset(PLAYSTATION_VIRTUAL_INPUTS)


def default_map_for(controller_name: str) -> Dict[str, str]:
    defaults = DEFAULT_VIRTUAL_MAPS.get(controller_name, {})
    return {key: value for key, value in defaults.items()}


def virtual_input_options_for(controller_label: str) -> list[str]:
    if controller_label == "PlayStation":
        return list(PLAYSTATION_VIRTUAL_INPUTS)
    if controller_label == "GBA":
        return list(GBA_VIRTUAL_INPUTS)
    return list(XBOX_VIRTUAL_INPUTS)


def valid_virtual_inputs_for_controller_name(controller_name: str) -> frozenset[str]:
    if controller_name == "PlayStationController":
        return PLAYSTATION_VIRTUAL_INPUTS_SET
    if controller_name == "GBAController":
        return GBA_VIRTUAL_INPUTS_SET
    return XBOX_VIRTUAL_INPUTS_SET


def is_valid_virtual_input(controller_name: str, virtual_input: str) -> bool:
    return virtual_input.strip() in valid_virtual_inputs_for_controller_name(controller_name)


def load_virtual_maps() -> Dict[str, Dict[str, str]]:
    maps = {
        name: mapping.copy()
        for name, mapping in DEFAULT_VIRTUAL_MAPS.items()
    }
    if not CONFIG_PATH.is_file():
        return maps

    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            overrides = json.load(config_file)
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("Could not read VirtualControllerMappings.json: %s", error)
        return maps

    if not isinstance(overrides, dict):
        return maps

    for controller_name, mapping in overrides.items():
        if controller_name in maps and isinstance(mapping, dict):
            maps[controller_name].update(mapping)
    return maps


def read_virtual_mappings_file() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("Could not read VirtualControllerMappings.json: %s", error)
        return {}


def write_virtual_mapping(controller_name: str, input_name: str, virtual_input: str) -> bool:
    cleaned = virtual_input.strip()
    if not is_valid_virtual_input(controller_name, cleaned):
        return False

    data = read_virtual_mappings_file()
    controller_map = data.get(controller_name)
    if not isinstance(controller_map, dict):
        controller_map = {}
    controller_map[input_name] = cleaned
    data[controller_name] = controller_map
    _write_virtual_mappings_file(data)
    return True


def reset_virtual_mappings(controller_name: str) -> None:
    data = read_virtual_mappings_file()
    if controller_name in data:
        del data[controller_name]
        _write_virtual_mappings_file(data)


def _write_virtual_mappings_file(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file, indent=4)
        config_file.write("\n")
