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
        self.voteList = {}

        # This is a Qt item, this serves the purpose of not letting SetupTestDriver.democracyThread run up the vote infinitely
        self.lastDemocracyItem = None
        self.lastDemocracyWinner = 'None'

        """
        These are fields only exist as workarounds for SetupTestDriver.py. Once a solution is found these should be eliminated ideally.
        
        self.countdownIndex only exists because I couldn't figure out how to program a countdown without
        QTimer and QTimer.timeout().

        self.anarchyThreadStatus only exists because I couldn't figure out how to pause
        and resume the anarchy thread in SetupTestDriver.
        """
        self.countdownIndex = 0
        self.anarchyThreadStatus = True
        self.democracyThreadStatus = False

        self.democracyTime = 15
        self.tapTime = 0.3
        self.pressTime = 0.5
        self.holdTime = 1
        self.defaultTimeLength = self.pressTime
    
    """
    Right now the way it works is that SetupTestDriver.handleReturnPressed(input) checks to see if the command is an input on the controller.
    If so, it is added as an item to SetupTestUi.listWidget, and either SetupTestDriver.anarchyThread or SetupTestDriver.democracyThread
    will SetupTestDriver.program.setupTest.metaCommand(command) although command is really just an input for now.
    
    The goal is to make a "command" object which intakes text, figures out how to cut up the text, and makes sequences of "input" objects.
    "Input" objects contain field

    Finish this
    """

    def metaCommand(self, command):
        if self.government == 'anarchy':
            print(self.defaultTimeLength)
            self.controller.pressButton(command, self.defaultTimeLength)
        elif self.government == 'democracy':
            if command not in self.voteList.keys():
                 self.voteList[command] = 1
            else:
                self.voteList[command] += 1
    
    def reduceSetupCount(self):
        self.countdown -= 1

    def reduceDemocracyCount(self):
        self.democracyTime -= 1

    def increaseIndexCount(self):
        self.countdownIndex += 1

    def resetIndexCount(self):
        self.countdownIndex = 0
    
    def resetVoteList(self):
        self.voteList = {}

    # set functions

    def setMetaMode(self, mode):
        return mode
    
    def setMetaGov(self, gov):
        self.government = gov

    def setCountdown(self, time):
        self.countdown = time

    def setAnarchyThreadStatus(self, bool):
        self.anarchyThreadStatus = bool
    
    def setDemocracyThreadStatus(self, bool):
        self.democracyThreadStatus = bool
    
    def setLastDemocracyItem(self, QtItem):
        self.lastDemocracyItem = QtItem

    def setLastDemocracyWinner(self, command):
        self.lastDemocracyWinner = command

    def setDefaultTimeLength(self, timeLength):
        if timeLength == 'tap':
            self.defaultTimeLength = self.tapTime
            
        elif timeLength == 'press':
            self.defaultTimeLength = self.pressTime

        elif timeLength == 'hold':
            self.defaultTimeLength = self.holdTime
    
    def setTapTime(self, time):
        self.tapTime = time
    
    def setPressTime(self, time):
        self.pressTime = time
    
    def setHoldTime(self, time):
        self.holdTime = time
    
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
    
    def getDefualtTimeLength(self):
        return self.defaultTimeLength
    
    def getDefualtTimeLengthStr(self):
        if self.defaultTimeLength == self.tapTime:
            return 'tap'
        elif self.defaultTimeLength == self.pressTime:
            return 'press'
        elif self.defaultTimeLength == self.holdTime:
            return 'hold'

    def getTapTime(self):
        return self.tapTime
    
    def getPressTime(self):
        return self.pressTime
    
    def getHoldTime(self):
        return self.holdTime
    
    def getAnarchyThreadStatus(self):
        return self.anarchyThreadStatus
    
    def getDemocracyThreadStatus(self):
        return self.democracyThreadStatus
    
    def getVoteList(self):
        return self.voteList

    def getLastDemocracyItem(self):
        return self.lastDemocracyItem

    def getMetaDemTime(self):
        return self.democracyTime