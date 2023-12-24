from Twitch_Connection import Twitch
import vgamepad as vg
import time
from threading import Thread
from queue import Queue

class ChatPlays():
    def __init__(self):
        #vController setup
        self.vController = vg.VX360Gamepad()

        # main program
        self.platform = 'twitch'
        self.userProfile = 'user'
        self.emulator = 'gba'
        self.inputs = {'up': 'XUSB_GAMEPAD_DPAD_UP', 
                       'down': 'XUSB_GAMEPAD_DPAD_DOWN', 
                       'left': 'XUSB_GAMEPAD_DPAD_LEFT', 
                       'right': 'XUSB_GAMEPAD_DPAD_RIGHT', 
                       'a': 'XUSB_GAMEPAD_A',
                       'b': 'XUSB_GAMEPAD_B', 
                       'l': 'XUSB_GAMEPAD_X', 
                       'r': 'XUSB_GAMEPAD_Y', 
                       'start': 'XUSB_GAMEPAD_START', 
                       'select': 'XUSB_GAMEPAD_BACK'}
        self.disabledInputs = []
        self.programStatus = False
        self.progMode = 'normal'
        self.progGov = 'anarchy'
        
        # test and setup
        # meta mode is either for setting up or testing
        self.testQueue = Queue()
        self.testThread = None
        self.metaMode = 'setup'
        self.testGov = 'anarchy'
        self.testTime = 5
        self.setupCountdown = 5
        self.demTime = 10
        
        # other settings
        self.tapTime = 0.3
        self.pressTime = 0.5
        self.holdTime = 1

    # def start(self):
    #     while self.programStatus:

    def addTestQueue(self, input):
        self.testQueue.put(input)

    def executeTestQueue(self, widget):
        while(not self.testQueue.empty()):
            topItem = widget.item(0)
            self.vControllerExecute(self.testQueue.get(), self.pressTime)
            widget.removeItemWidget(topItem)

    def vControllerExecute(self, input, timePeriod):
        self.vController.press_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.vController.update()
        time.sleep(timePeriod)
        self.vController.release_button(button=getattr(vg.XUSB_BUTTON, self.inputs[input]))
        self.vController.update()

    def metaCommand(self, input):    
        if self.metaMode == 'setup':
            time.sleep(self.setupCountdown)
            self.vControllerExecute(input, self.pressTime)
        elif self.metaMode == 'test':
            self.vControllerExecute(input, self.pressTime)

    
    def generalSetup(self):
        for input in self.inputs:
            time.sleep(self.setupCountdown)
            self.vControllerExecute(input, self.pressTime)

    def disableInput(self, input):
        if input not in self.disabledInputs:
            self.disabledInputs.append(input)
        elif input in self.disabledInputs:
            self.disabledInputs.remove(input)

    # set functions

    def setPlatform(self, platform):
        self.platform = platform

    def setUser(self, userName):
        self.userProfile = userName

    def setEmulator(self, emulator):
        self.emulator = emulator

    def setInputs(self, inputs):
        self.inputs = inputs

    def setStatus(self):
        self.programStatus = not self.programStatus

    def setMode(self, mode):
        self.progMode= mode

    def setMetaMode(self, mode):
        self.metaMode = mode

    def setGov(self, gov):
        self.progGov= gov
    
    def setDemTime(self, time):
        self.demTime = time

    def setPressTime(self,time):
        self.pressTime = time
    
    def setTapTime(self,time):
        self.tapTime = time

    def setHoldTime(self, time):
        self.holdTime = time
    
    # get functions

    def getPlatform(self):
        return self.platform

    def getUser(self):
        return self.userProfile

    def getEmulator(self):
        return self.emulator

    def getInputs(self):
        return self.inputs

    def getStatus(self):
        return self.programStatus

    def getMode(self):
        return self.progMode
    
    def getGov(self):
        return self.progGov
    
    def getDemTime(self):
        return self.demTime

    def getPressTime(self):
        return self.pressTime
    
    def getTapTime(self):
        return self.tapTime

    def getHoldTime(self):
        return self.holdTime