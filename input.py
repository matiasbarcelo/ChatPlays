import Controller
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class InputSequence():
    def __init_(self, string):
        self.stringRecieved = string
        self.listOfStringRecievedParsed = self.stringRecieved.split(',')
        
        
class Input():
    def __init__(self, string, controller):
        self.input = None
        self.timeLength = None
        self.repeatAmount = None
        self.isValid = None
        self.stringRecieved = string

        self.decipherString(string, controller)

    def decipherString(self, string, controller):

        additionForSpecialChars = r''

        specialChars = ['t','p','h']
    
        # Regular expression for joystick float
        joystickFloatVals = r'(?P<analogFloatVal>\((?P<xVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?,(?P<yVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?\))?'

        # # Regular expression for the normal joystick up to 255
        # joystickVals = r'\((?P<xVal>[0-255])?,(?P<yVal>[0-255])?\)'
            
        # if controller.isAnalog():
        #     self.analogTester

        timeLengthTest = additionForSpecialChars + r'(?P<timeLength>^[tph])?'
        repeatAmountTest = r'(?P<repeatAmount>[1-9]$)?'
        inputs = r'(?P<input>' + controller.getRegexStr() + ')'

        if controller.isAnalog():
            regexExpression = timeLengthTest + joystickFloatVals + inputs + repeatAmountTest

        else:
            regexExpression = timeLengthTest + inputs + repeatAmountTest

        fullTest = re.compile(regexExpression)
        logging.debug(f'regexExpression {regexExpression}')
        
        test = fullTest.match(string)
        
        self.input = test.group('input')
        self.repeatAmount = test.group('repeatAmount')
        self.timeLength = test.group('timeLength')
        logging.debug(f' Input obj groupdict = {test.groupdict()}, timeLength = {self.timeLength}, input = {self.input}, repeatAmount = {self.repeatAmount}')
        
        return
        
    def getInput(self):
        return self.input
    
    def getStringRecieved(self):
        return self.stringRecieved
    
    def getTimeLength(self):
        return self.timeLength
    
    def getRepeatAmount(self):
        return self.repeatAmount
    
    def getRepeatAmountInt(self):
        return int(self.repeatAmount)

if __name__ == '__main__':
    testController = Controller.XboxController()
    testStr = 't(.69,-0.59)lstick'
    testObject = Input(testStr, testController)