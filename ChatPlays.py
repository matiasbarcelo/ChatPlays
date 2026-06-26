from Twitch_Connection import Twitch
from Controller import GBAController
from SetupTestClass import SetupTestClass

class ChatPlays():
    def __init__(self):
        
        # main program

        # mayble like a PlatformDetails class?
        self.platform = 'twitch'
        self.userProfile = 'user'
        self.emulator = 'gba'

        self.controller = GBAController()
        self.setupTest = SetupTestClass()
        
        # Possible ProgramDetails or ProgramSettings class for what remains
        self.status = False # False if the program is off, True if program is on
        self.mode = 'normal'
        self.government = 'anarchy'
        
        # other settings
        self.democracyTime = 10
        self.tapTime = 0.3
        self.pressTime = 0.5
        self.holdTime = 1

    # set functions

    def setPlatform(self, platform):
        self.platform = platform

    def setUser(self, userName):
        self.userProfile = userName

    def setEmulator(self, emulator):
        self.emulator = emulator

    def setStatus(self):
        self.status = not self.status

    def setMode(self, mode):
        self.mode= mode

    def setGov(self, gov):
        self.government= gov
    
    def setDemTime(self, time):
        self.democracyTime = time

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

    def getStatus(self):
        return self.status

    def getMode(self):
        return self.mode
    
    def getGov(self):
        return self.government
    
    def getDemTime(self):
        return self.democracyTime

    def getPressTime(self):
        return self.pressTime
    
    def getTapTime(self):
        return self.tapTime

    def getHoldTime(self):
        return self.holdTime