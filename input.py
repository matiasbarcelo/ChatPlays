import Controller

import re

import logging



logger = logging.getLogger()

logger.setLevel(logging.DEBUG)



WAIT_INPUT = "wait"





def normalize_chat_text(text: str) -> str:

    return text.strip().lower().replace(" ", "")





def split_input_sequence(text: str) -> list[str]:

    parts = []

    current = []

    depth = 0

    for char in text:

        if char == "(":

            depth += 1

            current.append(char)

        elif char == ")":

            depth -= 1

            current.append(char)

        elif char == "," and depth == 0:

            part = "".join(current).strip()

            if part:

                parts.append(part)

            current = []

        else:

            current.append(char)

    part = "".join(current).strip()

    if part:

        parts.append(part)

    return parts





class InputSequence:

    def __init__(self, string, valueClass=None):

        normalized = normalize_chat_text(string)

        self.stringRecieved = normalized

        parts = split_input_sequence(normalized)
        if len(parts) > 1 and not valueClass.getAllowInputSequences():
            raise ValueError(f"Input sequences are not allowed: {string!r}")
        max_length = valueClass.getMaxInputSequenceLength()
        if len(parts) > max_length:
            raise ValueError(
                f"Input sequence length {len(parts)} exceeds max of {max_length}: {string!r}"
            )

        self.inputs = [Input(part, valueClass) for part in parts]



    def getInputs(self):

        return self.inputs



    def getStringRecieved(self):

        return self.stringRecieved





class Input():

    def __init__(self, string, valueClass = None):

        self.input = None

        self.timeLength = None

        self.durationSeconds = None

        self.repeatAmount = None

        self.isValid = None

        normalized = normalize_chat_text(string)

        self.stringRecieved = normalized



        self.decipherString(normalized, valueClass)



    def decipherString(self, string, valueClass):

        controller = valueClass.getController()

        maxTimeLength = valueClass.getMaxTimeLength()



        # Regular expression for joystick float

        joystickFloatVals = r'(?P<analogFloatVal>\((?P<xFloatVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?,(?P<yFloatVal>(-?1(\.0{0,2})?)|(-?0?(\.\d{0,2})?))?\))'



        # # Regular expression for int joystick val up to 255

        joystickIntVals = r'(?P<analogIntVal>\((?P<xIntVal>[0-2]?[0-4]?[0-9]|25[0-5])?,(?P<yIntVal>[0-2]?[0-9]?[0-9]|25[0-5])?\))'



        joystickVals = r'(?P<analogVal>' + joystickFloatVals + '|' + joystickIntVals + ')?'



        timeLengthStr = r'(?P<timeLengthStr>tap|press|hold|t|p|h)'

        timeLengthTest = rf'(?:{timeLengthStr})?'

        durationSeconds = r'(?:\((?P<durationSeconds>\d+(?:\.\d+)?)\))?'

        repeatAmountTest = r'(?P<repeatAmount>[1-9])?$'

        input_names = sorted(controller.getInputs().keys(), key=len, reverse=True)

        inputs = r'(?P<input>' + "|".join(re.escape(name) for name in [WAIT_INPUT, *input_names]) + ')'



        regexExpression = timeLengthTest + durationSeconds + joystickVals + inputs + repeatAmountTest



        fullTest = re.compile(regexExpression)

        logging.debug(f'regexExpression {regexExpression}')

        

        test = fullTest.match(string)

        if test is None:

            raise ValueError(f"Input string did not match controller pattern: {string!r}")



        time_length_raw = test.group('timeLengthStr')

        time_length_map = {

            'tap': 't',

            'press': 'p',

            'hold': 'h',

            't': 't',

            'p': 'p',

            'h': 'h',

        }

        self.input = test.group('input')

        self.repeatAmount = test.group('repeatAmount')

        self.timeLength = time_length_map.get(time_length_raw) if time_length_raw else None

        if time_length_raw and not valueClass.getAllowTimingPrefixes():

            raise ValueError(f"Tap, press, and hold prefixes are not allowed: {string!r}")

        if time_length_raw:
            timing_mode = {
                'tap': 'tap',
                't': 'tap',
                'press': 'press',
                'p': 'press',
                'hold': 'hold',
                'h': 'hold',
            }[time_length_raw]
            if not valueClass.isTimingModeEnabled(timing_mode):
                raise ValueError(f"{timing_mode.capitalize()} timing is not enabled: {string!r}")

        if self.repeatAmount and not valueClass.getAllowInputRepeat():

            raise ValueError(f"Input repeat is not allowed: {string!r}")

        if self.isWait() and self.repeatAmount:

            raise ValueError(f"Wait cannot be repeated: {string!r}")



        duration_raw = test.group('durationSeconds')

        if time_length_raw and duration_raw is not None:

            raise ValueError(

                f"Custom duration cannot be combined with tap, press, or hold prefixes: {string!r}"

            )

        if duration_raw is not None:

            if not valueClass.getAllowCustomInputDuration():

                raise ValueError(f"Custom input duration is not allowed: {string!r}")

            duration_value = float(duration_raw)

            if duration_value <= 0:

                raise ValueError(f"Input duration must be greater than 0: {string!r}")

            if duration_value > maxTimeLength:

                raise ValueError(

                    f"Input duration {duration_value} exceeds max of {maxTimeLength}: {string!r}"

                )

            self.durationSeconds = duration_value

        else:

            self.durationSeconds = None



        logging.debug(

            ' Input obj groupdict = %s, timeLength = %s, input = %s, repeatAmount = %s, durationSeconds = %s',

            test.groupdict(),

            self.timeLength,

            self.input,

            self.repeatAmount,

            self.durationSeconds,

        )

        

        return

        

    def getInput(self):

        return self.input

    

    def getStringRecieved(self):

        return self.stringRecieved

    

    def getTimeLength(self):

        return self.timeLength

    

    def getDurationSeconds(self):

        return self.durationSeconds

    

    def getRepeatAmount(self):

        return self.repeatAmount

    

    def getRepeatAmountInt(self):

        return int(self.repeatAmount)



    def isWait(self):

        return self.input == WAIT_INPUT



if __name__ == '__main__':

    from SetupTestClass import SetupTestClass

    testSetup = SetupTestClass()

    testStr = 'hhome9'

    testObject = Input(testStr, testSetup)


