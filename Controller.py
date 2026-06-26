import logging
import platform
import time

IS_MAC = platform.system() == "Darwin"

if IS_MAC:
    from keyboard_backend import KeyboardBackend, load_keyboard_maps

    _KEYBOARD_MAPS = load_keyboard_maps()
else:
    import vgamepad as vg


class Controller:
    def __init__(self):
        self.disabledInputs = []
        self.analog = False
        self.use_keyboard = IS_MAC
        self.controller = None

    def _init_backend(self, controller_class_name, key_map_name):
        if self.use_keyboard:
            key_map = _KEYBOARD_MAPS.get(key_map_name, {})
            self.controller = KeyboardBackend(key_map_name, key_map)
            logging.info(
                "Using keyboard input on macOS for %s (%d mapped keys). "
                "Edit KeyboardMappings.json to match your emulator bindings.",
                controller_class_name,
                len(key_map),
            )
            return

        if key_map_name == "PlayStationController":
            self.controller = vg.VDS4Gamepad()
        else:
            self.controller = vg.VX360Gamepad()

    def pressButton(self, input, timeLength, repeatAmount=None, isAnalog=False):
        if input in self.disabledInputs:
            return

        waitAmount = 0.1
        repeat_count = int(repeatAmount) if repeatAmount is not None else 1

        for iteration in range(repeat_count):
            if iteration > 0:
                time.sleep(waitAmount)
            self._execute_input(input, timeLength)

    def _execute_input(self, input, timeLength):
        if self.use_keyboard:
            self.controller.press_input(input, timeLength)
            return

        if isinstance(self.controller, vg.VDS4Gamepad):
            self.executePlayStation(input, timeLength)
        else:
            self.executeXbox(input, timeLength)

    def executeXbox(self, input, timeLength, isAnalog=False):
        button = getattr(vg.XUSB_BUTTON, self.inputs[input])
        self.controller.press_button(button=button)
        self.controller.update()
        time.sleep(timeLength)
        self.controller.release_button(button=button)
        self.controller.update()

    def executePlayStation(self, input, timeLength, isAnalog=False):
        if input in ("up", "down", "left", "right"):
            extension = vg.DS4_DPAD_DIRECTIONS
        else:
            extension = vg.DS4_BUTTONS
        button = getattr(extension, self.inputs[input])
        self.controller.press_button(button=button)
        self.controller.update()
        time.sleep(timeLength)
        self.controller.release_button(button=button)
        self.controller.update()

    def getRegexStr(self):
        regexStr = "|".join(self.inputs.keys())
        logging.debug("regexStr = %s", regexStr)
        return regexStr

    def disableInput(self, input):
        if input not in self.disabledInputs:
            self.disabledInputs.append(input)
        elif input in self.disabledInputs:
            self.disabledInputs.remove(input)

    def getInputs(self):
        return self.inputs

    def getButtonsForUiDict(self):
        return self.buttonsForUiDict

    def isAnalog(self):
        return self.analog

    def reload_keyboard_mappings(self):
        if not self.use_keyboard:
            return
        global _KEYBOARD_MAPS
        _KEYBOARD_MAPS = load_keyboard_maps()
        class_name = type(self).__name__
        key_map = _KEYBOARD_MAPS.get(class_name, {})
        self.controller = KeyboardBackend(class_name, key_map)


class GBAController(Controller):
    def __init__(self):
        super().__init__()
        self._init_backend("GBAController", "GBAController")
        self.inputs = {
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
        }
        self.buttonsForUiDict = {
            "upButton": "up",
            "downButton": "down",
            "leftButton": "left",
            "rightButton": "right",
            "aButton": "a",
            "bButton": "b",
            "lButton": "l",
            "rButton": "r",
            "selectButton": "select",
            "startButton": "start",
        }


class XboxController(Controller):
    def __init__(self):
        super().__init__()
        self._init_backend("XboxController", "XboxController")
        self.inputs = {
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
        }
        self.analog = True
        self.buttonsForUiDict = {
            "aButton_2": "a",
            "bButton_2": "b",
            "startButton_2": "start",
            "upDpadButton": "updpad",
            "downDpadButton": "downdpad",
            "leftDpadButton": "leftdpad",
            "rightDpadButton": "rightdpad",
            "rStickButton": "rstick",
            "lStickButton": "lstick",
            "lbButton": "lb",
            "rbButton": "rb",
            "xButton": "x",
            "yButton": "y",
            "ltButton": "lt",
            "rtButton": "rt",
            "backButton": "back",
            "homeButton": "home",
        }


class PlayStationController(Controller):
    def __init__(self):
        super().__init__()
        self._init_backend("PlayStationController", "PlayStationController")
        self.inputs = {
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
        }
        self.analog = True
        self.buttonsForUiDict = {
            "upButton_2": "up",
            "leftButton_2": "left",
            "rightButton_2": "right",
            "downButton_2": "down",
            "xButton_2": "x",
            "selectButton_2": "select",
            "startButton_3": "start",
            "cirButton": "cir",
            "triButton": "tri",
            "sqButton": "sq",
            "r1Button": "r1",
            "r2Button": "r2",
            "l1Button": "l1",
            "l2Button": "l2",
            "lStickButton_2": "lstick",
            "rStickButton_2": "rstick",
        }
