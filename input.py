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
    def __init__(self, string, valueClass = None):
        self.input = None
        self.timeLength = None
        self.repeatAmount = None
        self.isValid = None
        self.stringRecieved = string

        self.decipherString(string, valueClass)

    def decipherString(self, string, valueClass):
        controller = valueClass.getController()
        maxTimeLength = valueClass.getMaxTimeLength()
        maxRepeatAmount = valueClass.getMaxRepeatAmount()

        # Regular expression for joystick float
        joystickFloatVals = r'(?P<analogFloatVal>\((?P<xFloatVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?,(?P<yFloatVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?\))'

        # # Regular expression for int joystick val up to 255
        joystickIntVals = r'(?P<analogIntVal>\((?P<xIntVal>[0-2]?[0-4]?[0-9]|25[0-5])?,(?P<yIntVal>[0-2]?[0-9]?[0-9]|25[0-5])?\))'

        joystickVals = r'(?P<analogVal>' + joystickFloatVals + '|' + joystickIntVals + ')?'

        timeLengthStr = r'(?P<timeLengthStr>[tph])'
        timeLengthFloat = r'(?P<timeLengthFloat>[{firstDigit}][0-{secondDigit}])'.format(
            firstDigit=maxTimeLength // 10, secondDigit=maxTimeLength % 10
        )
        timeLengthTest = rf'(?:{timeLengthStr}{timeLengthFloat}?)?'
        repeatAmountTest = r'(?P<repeatAmount>[1-9]$)?'
        inputs = r'(?P<input>' + controller.getRegexStr() + ')'

        regexExpression = timeLengthTest + joystickVals + inputs + repeatAmountTest

        fullTest = re.compile(regexExpression)
        logging.debug(f'regexExpression {regexExpression}')
        
        test = fullTest.match(string)
        if test is None:
            raise ValueError(f"Input string did not match controller pattern: {string!r}")

        self.input = test.group('input')
        self.repeatAmount = test.group('repeatAmount')
        self.timeLength = test.group('timeLengthStr')
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
    from SetupTestClass import SetupTestClass
    testSetup = SetupTestClass()
    testStr = 'hhome9'
    testObject = Input(testStr, testSetup)