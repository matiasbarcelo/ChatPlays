import vgamepad as vg
import time

class Controller():
    def __init__(self):
        self.controller = vg.VX360Gamepad() #controller setup
        self.disabledInputs = []
    
    def pressButton(self, input, timePeriod):
        self.controller.press_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.controller.update()
        time.sleep(timePeriod)
        self.controller.release_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.controller.update()

    def disableInput(self, input):
        if input not in self.disabledInputs:
            self.disabledInputs.append(input)
        elif input in self.disabledInputs:
            self.disabledInputs.remove(input)

    def getInputs(self):
        return self.inputs
    
class GBAController(Controller):
    def __init__(self): 
        super().__init__()
        self.inputs = {'up': 'XUSB_GAMEPAD_DPAD_UP', 
                        'down': 'XUSB_GAMEPAD_DPAD_DOWN', 
                        'left': 'XUSB_GAMEPAD_DPAD_LEFT', 
                        'right': 'XUSB_GAMEPAD_DPAD_RIGHT', 
                        'a': 'XUSB_GAMEPAD_A',
                        'b': 'XUSB_GAMEPAD_B', 
                        'l': 'XUSB_GAMEPAD_X', 
                        'r': 'XUSB_GAMEPAD_Y',
                        'select': 'XUSB_GAMEPAD_BACK',
                        'start': 'XUSB_GAMEPAD_START'}