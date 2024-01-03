from PyQt5 import QtCore, QtGui, QtWidgets
from SetupTestUi import Ui_test_stup_window
from threading import Thread, Event
from ChatPlays import ChatPlays

"""
This is the driver for the setup and test window of ChatPlays. The intent of this window is to allow a user to test out and setup ChatPlays on their device, even while the program is running.

The reason there is a seperate driver for the UI is so I don't need to reprogram the UI each time I regenerate the UI using the pyQt5 designer.

My main issue as of 1/2/24 is that I'm having a hard time pausing and resuming a thread, because apparently that's not the way they are meant to be used.
"""

class Driver(Ui_test_stup_window):
    def __init__(self):
        # perhaps once I connect this setup window to the main window, self.program won't be here, but rather on the main window.
        self.program = ChatPlays()
        self.anarchyThread = Thread(target=self.executeCommand, daemon = True)
        self.timer = QtCore.QTimer()

    def actualize(self):
        self.Setup_or_Test_comboBox.currentTextChanged.connect(lambda: self.program.setupTest.setMetaMode(self.Setup_or_Test_comboBox.currentText().lower()))
        self.Setup_or_Test_comboBox.currentTextChanged.connect(lambda: self.switchButtonsMode())

        self.Test_Mode_comboBox.currentTextChanged.connect(lambda: self.program.setupTest.setMetaGov(self.Test_Mode_comboBox.currentText().lower()))
        self.Countdown_spinBox.valueChanged.connect(lambda: self.program.setupTest.setCountdown(self.Countdown_spinBox.value()))
        self.Dem_timer_spinBox.valueChanged.connect(lambda: self.program.setDemTime(self.program.setupTest.setMetaDemTime(self.Dem_timer_spinBox.value())))

        self.General_Setup_pushButton.clicked.connect(lambda: self.generalSetup(False))

        self.lineEdit.returnPressed.connect(lambda: self.handleReturnPressed(self.lineEdit.text()))

        self.actualizeButtonsForSetup()
    
    def actualizeButtonsForSetup(self):
        inputs = self.program.setupTest.controller.getInputs()
        for buttonName in inputs:
            button = getattr(self, f'{buttonName}Button')
            button.clicked.connect(lambda _, name=buttonName: self.generalSetup(True, name))

    # remember that this actualizes buttons for test mode not setup mode
    def actualizeButtonsForTest(self):
        inputs = self.program.setupTest.controller.getInputs()
        for buttonName in inputs:
            button = getattr(self, f'{buttonName}Button')
            button.clicked.connect(lambda _, name=buttonName: self.handleReturnPressed(name))

    def switchButtonsMode(self):
        self.disconnectButtons()
        setupOrTest = self.program.setupTest.getMetaMode()
        if setupOrTest == 'test':
            self.program.setupTest.setMetaMode('setup')
            self.actualizeButtonsForSetup()
        else:
            self.program.setupTest.setMetaMode('test')
            self.actualizeButtonsForTest()


    def disconnectButtons(self):
        inputs = self.program.setupTest.controller.getInputs()
        for buttonName in inputs:
            button = getattr(self, f'{buttonName}Button')
            button.clicked.disconnect()

    def handleReturnPressed(self, text):
        text = text.lower()
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        if (text == 'clear'):
            self.listWidget.clear()
            self.lineEdit.clear()
        elif text in inputs:
            self.listWidget.addItem(text)
            self.lineEdit.clear()
        else:
            self.lineEdit.clear()

    """ 
    When the General_Setup_pushButton or when a UI controller button is pressed in setup metaMode, generalSetup() starts a QTimer which uses timerStep() each second (1000 ms).
    isSingleInput argument is to determine the countdown should be for just one input or the entire setup. True if just single input, false otherwise.
    Button is passed if just for a single input. Something to note is that while the setup is in anarchy mode, the anarchy thread will need to be stopped and reset.
    """
            
    def generalSetup(self, isSingleInput, button = None):
        mode = self.program.setupTest.getMetaGov()
        if mode == 'anarchy':
            # I need to somehow stop the anarchy thread from running here
            self.program.setupTest.setAnarchyThreadStatus(False)
        if not self.timer.isActive():
            self.timer.timeout.connect(lambda: self.timerStep(isSingleInput, button))
            self.timer.start(1000)

    def timerStep(self, isSingleInput, button = None):
        countDownNum = self.program.setupTest.getCountdown()
        if countDownNum >= 0:
            self.listWidget.addItem(str(countDownNum))
            self.program.setupTest.reduceCount()
            self.listWidget.scrollToBottom()
        else:
            if isSingleInput:
                self.singleInputExecution(button)
            else:
                self.notSingleInputExecution()
    
    def singleInputExecution(self, button):
        self.listWidget.addItem(button)
        self.program.setupTest.metaCommand(button)
        self.program.setupTest.setCountdown(self.Countdown_spinBox.value())
        self.timer.stop()
        self.timer.timeout.disconnect()
        self.listWidget.clear()
        # I need to continue the anarchy thread running here if the setup metaGov is set to anarchy
        mode = self.program.setupTest.getMetaGov()
        if mode == 'anarchy':
            self.program.setupTest.setAnarchyThreadStatus(True)

    def notSingleInputExecution(self):
        index = self.program.setupTest.getCountdownIndex()
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        if (index < len(inputs)) and (index != len(inputs) - 1):
                self.listWidget.addItem(inputs[index])
                self.program.setupTest.setCountdown(self.Countdown_spinBox.value())
                self.program.setupTest.increaseIndexCount()
                self.program.setupTest.metaCommand(inputs[index])
                self.listWidget.scrollToBottom()
        else:
            self.listWidget.addItem(inputs[index])
            self.program.setupTest.resetIndexCount()
            self.program.setupTest.setCountdown(self.Countdown_spinBox.value())
            self.timer.stop()
            self.timer.timeout.disconnect()
            self.listWidget.clear()
            # I need to continue the anarchy thread running here if the setup metaGov is set to anarchy
            mode = self.program.setupTest.getMetaGov()
            if mode == 'anarchy':
                self.program.setupTest.setAnarchyThreadStatus(True)

    """
    The function never stops executing. I'm having a hard time with threading and events(), frankly I don't understand why they couldn't just pause individual threads and resume them like anything else.
    If I could just pause self.anarchyThread while self.generalSetup() is going on, that would be fantastic; but, it isn't that simple. Once a thread executes its function, it cannot be called again.
    The workaround I came up with, which is meant to be temporary but as LeBlanc's law states: "Later means never." The except block in executeCommand method is there because TypeError is raised when the 
    'command' variable is initiated as NoneType.
    """

    def executeCommand(self):
        while True:
            try:
                status = self.program.setupTest.getAnarchyThreadStatus()
                if not status:
                    continue

                command = self.listWidget.item(0).text()
                if command != None:
                    print("worked")
                    self.program.setupTest.metaCommand(command)
                    self.listWidget.takeItem(0)
            
            except:
                continue

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    test_stup_window = QtWidgets.QMainWindow()
    ui = Driver()
    ui.setupUi(test_stup_window)
    ui.actualize()
    # This next line doesn't feel right
    ui.anarchyThread.start()
    test_stup_window.show()
    sys.exit(app.exec_())