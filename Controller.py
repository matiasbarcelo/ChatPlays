import vgamepad as vg
import time
import logging

class Controller():
    def __init__(self):
        self.disabledInputs = []
        self.analog = False

    def pressButton(self, input, timeLength, repeatAmount = None, isAnalog = False):
        waitAmount = 0.1
        if isinstance(self.controller, vg.VX360Gamepad):
            logging.debug(f' \'Xbox\' type controller detected, input = {input}, timeLength = {timeLength}, repeatAmount = {repeatAmount}, waitAmount = {waitAmount}')
            if repeatAmount != None:
                logging.debug(f' pressButton() sees that this is a repeat input')
                repeatAmountInt = int(repeatAmount)
                self.executeXbox(input, timeLength)
                logging.debug(f' iteration 1 complete, repeatAmountInt = {repeatAmountInt}')
                for i in range(repeatAmountInt-1):
                    time.sleep(waitAmount)
                    self.executeXbox(input, timeLength)
                    logging.debug(f' iteration {i+2} complete')
            else:
                self.executeXbox(input, timeLength)
                logging.debug(f' Xbox type execution went through')

        elif isinstance(self.controller, vg.VDS4Gamepad):
            logging.debug(f' \'PlayStation\' type controller detected, input = {input}, timeLength = {timeLength}, repeatAmount = {repeatAmount}, waitAmount = {waitAmount}')
            if repeatAmount != None:
                logging.debug(f' pressButton() sees that this is a repeat input')
                repeatAmountInt = int(repeatAmount)
                self.executePlayStation(input, timeLength)
                logging.debug(f' iteration 1 complete, repeatAmountInt = {repeatAmountInt}')
                for i in range(repeatAmountInt-1):
                    time.sleep(waitAmount)
                    self.executeXbox(input, timeLength)
                    logging.debug(f' iteration {i+2} complete')
            else:
                self.executePlayStation(input, timeLength)
                logging.debug(f'Playstation type execution went through')

    def executeXbox(self, input, timeLength, isAnalog = False):
        self.controller.press_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.controller.update()
        time.sleep(timeLength)
        self.controller.release_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.controller.update()

    def executePlayStation(self, input, timeLength, isAnalog = False):
        if input == 'up' or input == 'down' or input == 'left' or input == 'right':
            extension = vg.DS4_DPAD_DIRECTIONS
        else:
            extension = vg.DS4_BUTTONS
        self.controller.press_button(button=getattr(extension, self.inputs[input]))
        self.controller.update()
        time.sleep(timeLength)
        self.controller.release_button(button=getattr(extension, self.inputs[input]))
        self.controller.update()

    def getRegexStr(self):
        regexStr = ''
        for input in self.inputs.keys():
            regexStr += f'{input}|'
        regexStr = regexStr[:-1] # this is to remove the last '|'
        logging.debug(f'regexStr = {regexStr}')
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
    
class GBAController(Controller):
    def __init__(self): 
        super().__init__()
        self.controller = vg.VX360Gamepad() # this uses the 360 controller to work
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
        self.buttonsForUiDict = {'upButton' : 'up', 'downButton' : 'down', 'leftButton' : 'left', 'rightButton' : 'right', 'aButton' : 'a', 'bButton' : 'b', 'lButton' : 'l', 'rButton' : 'r',
                             'selectButton' : 'select', 'startButton' : 'start'}
        
class XboxController(Controller):
    def __init__(self):
        super().__init__()
        self.controller = vg.VX360Gamepad() # this uses the 360 controller to work
        self.inputs = {'updpad': 'XUSB_GAMEPAD_DPAD_UP', 
                        'downdpad': 'XUSB_GAMEPAD_DPAD_DOWN', 
                        'leftdpad': 'XUSB_GAMEPAD_DPAD_LEFT', 
                        'rightdpad': 'XUSB_GAMEPAD_DPAD_RIGHT',
                        'a': 'XUSB_GAMEPAD_A',
                        'b': 'XUSB_GAMEPAD_B', 
                        'x': 'XUSB_GAMEPAD_X', 
                        'y': 'XUSB_GAMEPAD_Y',
                        'back': 'XUSB_GAMEPAD_BACK',
                        'start': 'XUSB_GAMEPAD_START',
                        'home': 'XUSB_GAMEPAD_GUIDE',
                        'lb': 'XUSB_GAMEPAD_LEFT_SHOULDER',
                        'rb':'XUSB_GAMEPAD_RIGHT_SHOULDER',
                        'lstick': 'left_joystick_float',
                        'rstick': 'right_joystick_float',
                        'lt':'left_trigger_float',
                        'rt':'right_trigger_float'}
        self.analog = ['lstick', 'rstick', 'lt', 'rt']
        self.buttonsForUiDict = {'aButton_2' : 'a', 'bButton_2' : 'b', 'startButton_2':'start', 'upDpadButton': 'updpad', 'downDpadButton':'downdpad', 'leftDpadButton':'leftdpad',
                             'rightDpadButton':'rightdpad', 'rStickButton':'rstick', 'lStickButton':'lstick', 'lbButton':'lb', 'rbButton':'rb', 'xButton':'x', 'yButton':'y',
                             'ltButton':'lt', 'rtButton':'rt', 'backButton':'back', 'homeButton':'home'}
        self.analog = True
        
class PlayStationController(Controller):
    def __init__(self):
        super().__init__()
        self.controller = vg.VDS4Gamepad()
        self.inputs = {'up': 'DS4_BUTTON_DPAD_NORTH',
                        'down': 'DS4_BUTTON_DPAD_SOUTH', 
                        'left': 'DS4_BUTTON_DPAD_WEST',
                        'right': 'DS4_BUTTON_DPAD_EAST',
                        'x': 'DS4_BUTTON_CROSS',
                        'sq': 'DS4_BUTTON_SQUARE',
                        'cir': 'DS4_BUTTON_CIRCLE', 
                        'tri': 'DS4_BUTTON_TRIANGLE',
                        'select': 'DS4_BUTTON_OPTIONS',
                        'start': 'DS4_BUTTON_SHARE',
                        'l1': 'DS4_BUTTON_SHOULDER_LEFT',
                        'r1':'DS4_BUTTON_SHOULDER_RIGHT',
                        'l2':'DS4_BUTTON_TRIGGER_LEFT',
                        'r2':'DS4_BUTTON_TRIGGER_RIGHT',
                        'lstick': 'left_joystick_float',
                        'rstick': 'right_joystick_float'}
        self.analog = ['lstick', 'rstick']
        self.buttonsForUiDict = {'upButton_2' : 'up', 'leftButton_2': 'left', 'rightButton_2': 'right', 'downButton_2': 'down', 'xButton_2' : 'x', 'selectButton_2':'select',
                             'startButton_3':'start', 'cirButton':'cir', 'triButton':'tri', 'sqButton':'sq', 'r1Button':'r1', 'r2Button':'r2', 'l1Button':'l1',
                             'l2Button':'l2', 'lStickButton_2':'lstick', 'rStickButton_2':'rstick'}
        self.analog = True