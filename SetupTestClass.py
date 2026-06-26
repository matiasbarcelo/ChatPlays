import Controller
import logging
from input import Input
import json

class SetupTestClass():
    
    def __init__(self):
        settings_path = 'setupTestSettings.json'
        try:
            with open(settings_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        self.controller = Controller.GBAController()
        self.maxRepeatAmount = data.get('maxRepeatAmount', 9)
        self.maxTimeLength = data.get('maxTimeLength', 15)
        
        self.metaMode = data.get('metaMode', 'setup')
        self.government = data.get('government', 'anarchy')
        self.testTime = data.get('testTime', 5)
        self.countdown = data.get('countdown', 5)
        self.voteList = {}

        # This is a Qt item, this serves the purpose of not letting SetupTestDriver.democracyThread run up the vote infinitely
        self.lastDemocracyItem = data.get('lastDemocracyItem', None)
        self.lastDemocracyWinner = data.get('lastDemocracyWinner', 'None')

        """
        These are fields only exist as workarounds for SetupTestDriver.py. Once a solution is found these should be eliminated ideally.
        
        self.countdownIndex only exists because I couldn't figure out how to program a countdown without
        QTimer and QTimer.timeout().

        self.anarchyThreadStatus only exists because I couldn't figure out how to pause
        and resume the anarchy thread in SetupTestDriver.
        """
        self.countdownIndex = data.get('countdownIndex', 0)
        self.anarchyThreadStatus = data.get('anarchyThreadStatus', True)
        self.democracyThreadStatus = data.get('democracyThreadStatus', False)

        self.democracyTime = data.get('democracyTime', 15)
        self.tapTime = data.get('tapTime', 0.3)
        self.pressTime = data.get('pressTime', 0.5)
        self.holdTime = data.get('holdTime', 1)
        self.defaultTimeLength = data.get('defaultTimeLength', self.pressTime)
    
    """
    Right now the way it works is that SetupTestDriver.handleReturnPressed(input) checks to see if the command is an input on the controller.
    If so, it is added as an item to SetupTestUi.listWidget, and either SetupTestDriver.anarchyThread or SetupTestDriver.democracyThread
    will SetupTestDriver.program.setupTest.metaCommand(command) although command is really just an input for now.
    
    The goal is to make a "command" object which intakes text, figures out how to cut up the text, and makes sequences of "input" objects.
    "Input" objects contain field

    Finish this
    """

    def changeController(self, controller):
        del self.controller
        if controller == 'GBA':
            self.controller = Controller.GBAController() 
        elif controller == 'Xbox 360':
            self.controller = Controller.XboxController()
        elif controller == 'PlayStation':
            self.controller = Controller.PlayStationController()

    def metaCommand(self, inputObj):
        logging.debug(f' metaCommand() recieved {inputObj}')

        if inputObj.getTimeLength() and inputObj.getRepeatAmount():
            logging.debug(
                f' metaCommand() fired, timeLength = {inputObj.getTimeLength()} repeatAmount = {inputObj.getRepeatAmount()}'
            )
            self.controller.pressButton(
                inputObj.getInput(),
                self.getTimeLengthForStr(inputObj.getTimeLength()),
                inputObj.getRepeatAmount(),
            )
        elif inputObj.getTimeLength():
            testForTimeLength = self.getTimeLengthForStr(inputObj.getTimeLength())
            logging.debug(
                f' metaCommand() fired, timeLength = {inputObj.getTimeLength()} repeatAmount = None, testForTimeLength = {testForTimeLength}'
            )
            self.controller.pressButton(
                inputObj.getInput(),
                self.getTimeLengthForStr(inputObj.getTimeLength()),
            )
        elif inputObj.getRepeatAmount():
            logging.debug(
                f' metaCommand() fired, timeLength = default repeatAmount = {inputObj.getRepeatAmount()}'
            )
            self.controller.pressButton(
                inputObj.getInput(),
                self.getDefualtTimeLength(),
                inputObj.getRepeatAmount(),
            )
        else:
            logging.debug(f' metaCommand() fired, timeLength = default repeatAmount = None')
            self.controller.pressButton(inputObj.getInput(), self.defaultTimeLength)


    def adjustVoteList(self, text):
        if text not in self.voteList.keys():
                self.voteList[text] = 1
        else:
            self.voteList[text] += 1
    
    def save_to_json(self, filename):
        # Collect the field values into a dictionary
        data = {
            "controller": self.controller,
            "metaMode": self.metaMode,
            "government": self.government,
            "testTime": self.testTime,
            "countdown": self.countdown,
            "anarchyThreadStatus": self.anarchyThreadStatus,
            "democracyThreadStatus": self.democracyThreadStatus,
            "democracyTime": self.democracyTime,
            "tapTime": self.tapTime,
            "pressTime": self.pressTime,
            "holdTime": self.holdTime,
            "defaultTimeLengthStr": self.getDefualtTimeLengthStr()
        }

        # Write the data to a JSON file
        with open(filename, "w") as f:
            json.dump(data, f)

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
        self.metaMode = mode
    
    def setMetaGov(self, gov):
        self.government = gov

    def setCountdown(self, time):
        self.countdown = time

    def setAnarchyThreadStatus(self, bool):
        self.anarchyThreadStatus = bool
    
    def setDemocracyThreadStatus(self, bool):
        self.democracyThreadStatus = bool
    
    def setLastDemocracyItem(self, item):
        self.lastDemocracyItem = item

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

    def setMaxRepeatAmount(self, n):
        self.maxRepeatAmount = n

    # get functions

    def getMetaMode(self):
        return self.metaMode
    
    def getMetaGov(self):
        return self.government

    def getCountdown(self):
        return self.countdown
    
    def getController(self):
        return self.controller
    
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
        
    def getTimeLengthForStr(self, timeLength):
        if timeLength == 't':
            return self.getTapTime()
            
        elif timeLength == 'p':
            return self.getPressTime()

        elif timeLength == 'h':
            return self.getHoldTime()

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
    
    def getMaxRepeatAmount(self):
        return self.maxRepeatAmount
    
    def getMaxTimeLength(self):
        return self.maxTimeLength
    
if __name__ == '__main__':
    test = SetupTestClass()
    inputObj = Input('a', test.getController())
    test.metaCommand(inputObj)