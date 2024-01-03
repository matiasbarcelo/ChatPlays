import time
from Controller import GBAController
from threading import Thread

class SetupTestClass():
    
    def __init__(self):
        
        self.controller = GBAController()
        
        self.metaMode = 'setup'
        self.government = 'anarchy'
        self.testTime = 5
        self.countdown = 5

        """
        These are fields only exist as workarounds for SetupTestDriver.py. Once a solution is found these should be eliminated ideally.
        
        self.countdownIndex only exists because I couldn't figure out how to program a countdown without
        QTimer and QTimer.timeout().

        self.anarchyThreadStatus only exists because I couldn't figure out how to pause
        and resume the anarchy thread in SetupTestDriver.
        """
        self.countdownIndex = 0
        self.anarchyThreadStatus = True

        self.democracyTime = 10
        self.tapTime = 0.3
        self.pressTime = 0.5
        self.holdTime = 1
    
    def metaCommand(self, input):
        self.controller.pressButton(input, self.pressTime)
    
    def reduceCount(self):
        self.countdown -= 1

    def increaseIndexCount(self):
        self.countdownIndex += 1

    def resetIndexCount(self):
        self.countdownIndex = 0

    # set functions

    def setMetaMode(self, mode):
        return mode
    
    def setMetaGov(self, gov):
        self.government = gov

    def setCountdown(self, time):
        self.countdown = time

    def setAnarchyThreadStatus(self, bool):
        self.anarchyThreadStatus = bool
    
    def setMetaDemTime(self, time):
        self.democracyTime = time

    # get functions

    def getMetaMode(self):
        return self.metaMode
    
    def getMetaGov(self):
        return self.government

    def getCountdown(self):
        return self.countdown
    
    def getCountdownIndex(self): 
        return self.countdownIndex
    
    def getAnarchyThreadStatus(self):
        return self.anarchyThreadStatus
    
    def getMetaDemTime(self):
        return self.democracyTime