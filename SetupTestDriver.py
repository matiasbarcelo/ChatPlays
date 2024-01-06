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
        self.anarchyThread = Thread(target=self.executeAnarchyThread, daemon = True)
        self.democracyThread = Thread(target=self.executeDemocracyThread, daemon = True)
        self.setupTimer = QtCore.QTimer()
        self.democracyTimer = QtCore.QTimer()

    def actualize(self):
        self.Setup_or_Test_comboBox.currentTextChanged.connect(lambda: self.program.setupTest.setMetaMode(self.Setup_or_Test_comboBox.currentText().lower()))
        self.Setup_or_Test_comboBox.currentTextChanged.connect(lambda: self.switchButtonsMode())

        
        self.Test_Mode_comboBox.currentTextChanged.connect(lambda: self.program.setupTest.setMetaGov(self.Test_Mode_comboBox.currentText().lower()))
        self.Test_Mode_comboBox.currentTextChanged.connect(lambda: self.switchMetaGov())
        
        self.intValidator = QtGui.QIntValidator()
        self.intValidator.setRange(0, 59)
        self.minutesBox.setValidator(self.intValidator)
        self.secondsBox.setValidator(self.intValidator)
        self.startTimerButton.clicked.connect(lambda: self.updateMetaDemTime())
        self.startTimerButton.clicked.connect(lambda: self.startDemTimer())

        self.General_Setup_pushButton.clicked.connect(lambda: self.generalSetup(False))
        self.General_Setup_pushButton.clicked.connect(lambda: self.program.setupTest.setCountdown(self.Countdown_spinBox.value()))

        self.lineEdit.returnPressed.connect(lambda: self.handleReturnPressed(self.lineEdit.text(), self.listWidget, self.lineEdit))
        self.lineEdit_2.returnPressed.connect(lambda: self.handleReturnPressed(self.lineEdit_2.text(), self.listWidget_2, self.lineEdit_2))

        self.tapCheckbox.clicked.connect(lambda: self.handleTimeLengthCheckboxStateChanged(self.tapCheckbox))
        self.pressCheckbox.clicked.connect(lambda: self.handleTimeLengthCheckboxStateChanged(self.pressCheckbox))
        self.holdCheckbox.clicked.connect(lambda: self.handleTimeLengthCheckboxStateChanged(self.holdCheckbox))

        self.tapSpinbox.valueChanged.connect(lambda: self.handleTimeLengthValueChanged(self.tapSpinbox))
        self.pressSpinbox.valueChanged.connect(lambda: self.handleTimeLengthValueChanged(self.pressSpinbox))
        self.holdSpinbox.valueChanged.connect(lambda: self.handleTimeLengthValueChanged(self.holdSpinbox))

        self.actualizeButtonsForSetup()

    def handleTimeLengthValueChanged(self, timeLengthObj):
        defaultTimeLengthStr = self.program.setupTest.getDefualtTimeLengthStr()
        timeLength = timeLengthObj.value()
        
        if timeLengthObj == self.tapSpinbox:
            self.program.setupTest.setTapTime(timeLength)
            if defaultTimeLengthStr == 'tap':
                self.program.setupTest.setDefaultTimeLength('tap')
        
        elif timeLengthObj == self.pressSpinbox:
            self.program.setupTest.setPressTime(timeLength)
            if defaultTimeLengthStr == 'press':
                self.program.setupTest.setDefaultTimeLength('press')
        
        elif timeLengthObj == self.holdSpinbox:
            self.program.setupTest.setHoldTime(timeLength)
            if defaultTimeLengthStr == 'hold':
                self.program.setupTest.setDefaultTimeLength('hold')
            

    def handleTimeLengthCheckboxStateChanged(self, senderCheckbox):
        # I was initially confused as to why this next line wasn't an if not statement,
        # but once a checkbox is clicked the checked status changesanyways which is why this works
        if senderCheckbox.isChecked():
            if senderCheckbox == self.tapCheckbox:
                self.pressCheckbox.setChecked(False)
                self.holdCheckbox.setChecked(False)
                self.program.setupTest.setDefaultTimeLength('tap')
            elif senderCheckbox == self.pressCheckbox:
                self.tapCheckbox.setChecked(False)
                self.holdCheckbox.setChecked(False)
                self.program.setupTest.setDefaultTimeLength('press')
            elif senderCheckbox == self.holdCheckbox:
                self.tapCheckbox.setChecked(False)
                self.pressCheckbox.setChecked(False)
                self.program.setupTest.setDefaultTimeLength('hold')

        else:
            senderCheckbox.setChecked(True)

    def switchMetaGov(self):
        gov = self.program.setupTest.getMetaGov()
        setupOrTest = self.program.setupTest.getMetaMode()
        if gov == 'anarchy':
            self.stackedWidget.setCurrentIndex(0)
            self.program.setupTest.democracyThreadStatus = False
            self.program.setupTest.anarchyThreadStatus = True
        elif gov == 'democracy':
            self.stackedWidget.setCurrentIndex(1)
            self.program.setupTest.anarchyThreadStatus = False          
            self.program.setupTest.democracyThreadStatus = True

        # for some reason, the buttons were deactualizing when the metaGovernment switched
        if setupOrTest == 'setup':
            self.actualizeButtonsForSetup()
        elif setupOrTest == 'test':
            self.actualizeButtonsForTest()
        
    
    def updateMetaDemTime(self):
        minutes = int(self.minutesBox.text()) if self.minutesBox.text() else 0
        seconds = int(self.secondsBox.text()) if self.secondsBox.text() else 0

        total_seconds = (minutes * 60) + seconds
        self.program.setupTest.setMetaDemTime(total_seconds)

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

    def handleReturnPressed(self, text, listW, edit):
        text = text.lower()
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        gov = self.program.setupTest.getMetaGov()
        if (text == 'clear'):
            listW.clear()
            edit.clear()
        elif text in inputs:
            if gov == 'anarchy':
                listW.addItem(text)
                edit.clear()
            elif gov == 'democracy':
                listW.insertItem(0, text)
                edit.clear()
        else:
            edit.clear()

    """ 
    When the General_Setup_pushButton or when a UI controller button is pressed in setup metaMode, generalSetup() starts a QTimer which uses setupTimerStep() each second (1000 ms).
    isSingleInput argument is to determine the countdown should be for just one input or the entire setup. True if just single input, false otherwise.
    Button is passed if just for a single input. Something to note is that while the setup is in anarchy mode, the anarchy thread will need to be stopped and reset.
    """
            
    def generalSetup(self, isSingleInput, button = None):
        mode = self.program.setupTest.getMetaGov()
        if mode == 'anarchy':
            # I need to somehow stop the anarchy thread from running here
            self.program.setupTest.setAnarchyThreadStatus(False)
        elif mode == 'democracy':
            self.program.setupTest.setDemocracyThreadStatus(False)
        if not self.setupTimer.isActive():
            self.setupTimer.timeout.connect(lambda: self.setupTimerStep(isSingleInput, button))
            self.setupTimer.start(1000)

    def setupTimerStep(self, isSingleInput, button = None):
        countDownNum = self.program.setupTest.getCountdown()
        if countDownNum >= 0:
            self.listWidget.addItem(str(countDownNum))
            self.program.setupTest.reduceSetupCount()
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
        self.setupTimer.stop()
        self.setupTimer.timeout.disconnect()
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
            self.setupTimer.stop()
            self.setupTimer.timeout.disconnect()
            self.listWidget.clear()
            # I need to continue the anarchy thread running here if the setup metaGov is set to anarchy
            mode = self.program.setupTest.getMetaGov()
            if mode == 'anarchy':
                self.program.setupTest.setAnarchyThreadStatus(True)

    def resetDemVotes(self):
        winner = self.position1Input.text()
        self.program.setupTest.setLastDemocracyWinner (winner)
        # should be latestWinnerLabel but for whatever reason pyuic5 not changing the label name. Weird. *update: PyQt Designer just randomly decides when it wants and doesn't want to update names apparently
        self.latestWinnerLabel.setText(f'Latest Winner: {winner}')
        for i in range(4):
            inputVar = getattr(self, f'position{i+1}Input')
            votesVar = getattr(self, f'position{i+1}Votes')
            inputVar.setText('empty')
            votesVar.setText(str(0))
            

    def startDemTimer(self):
            if not self.democracyTimer.isActive():
                self.democracyTimer.timeout.connect(lambda: self.democracyTimerStep())
                self.democracyTimer.start(1000)

    def democracyTimerStep(self):
        demTime = self.program.setupTest.getMetaDemTime()
        if demTime >= 0:
            minutes = demTime // 60
            seconds = demTime - minutes*60
            if seconds >= 10:
                self.countdownLabel.setText(f'Countdown: {minutes}:{seconds}')
            else:
                self.countdownLabel.setText(f'Countdown: {minutes}:0{seconds}')
            self.program.setupTest.reduceDemocracyCount()
        else:
            self.democracyTimer.stop()
            self.democracyTimer.disconnect()
            self.updateMetaDemTime()
            demTime = self.program.setupTest.getMetaDemTime()
            minutes = demTime // 60
            seconds = demTime - minutes*60
            self.program.setupTest.resetVoteList()
            self.program.setupTest.controller.pressButton(self.position1Input.text(), self.program.setupTest.getDefualtTimeLength())
            self.resetDemVotes()
            self.listWidget_2.clear()
            if seconds >= 10:
                self.countdownLabel.setText(f'Countdown: {minutes}:{seconds}')
            else:
                self.countdownLabel.setText(f'Countdown: {minutes}:0{seconds}')

    """
    The function never stops executing. I'm having a hard time with threading and events(), frankly I don't understand why they couldn't just pause individual threads and resume them like anything else.
    If I could just pause self.anarchyThread while self.generalSetup() is going on, that would be fantastic; but, it isn't that simple. Once a thread executes its function, it cannot be called again.
    The workaround I came up with, which is meant to be temporary is that a status for the threads. While other shit is going on, these threads keep executing but don't do anything.
    The except block in executeAnarchyCommand method is there because TypeError is raised when the 'command' variable is initiated as NoneType.
    """

    def executeAnarchyThread(self):
        while True:
            try:
                status = self.program.setupTest.getAnarchyThreadStatus()
                gov = self.program.setupTest.getMetaGov()
                if not status or gov != 'anarchy':
                    continue

                command = self.listWidget.item(0).text()
                if command != None:
                    print("worked")
                    self.program.setupTest.metaCommand(command)
                    self.listWidget.takeItem(0)
            
            except:
                continue

    # I don't know why but this method wasn't working when defined after executeDemocracyThread
    def updateVoteCountOnUi(self):
    # even though its called 'voteList' its actually a dictionary
        voteList = self.program.setupTest.getVoteList()
        # This variable is a sorted list from most to least of voteList keys according to their value ints.
        voteListSorted = sorted(voteList, key=lambda x: voteList[x], reverse=True)
        print(voteList)
        print(voteListSorted)
        # I don't know why this for loop isn't giving out an error when there isn't a voteListSorted[i] but it works so whatever
        for i in range(4):
            inputVar = getattr(self, f'position{i+1}Input')
            votesVar = getattr(self, f'position{i+1}Votes')
            input = voteListSorted[i]
            votes = voteList[input]
            inputVar.setText(input)
            votesVar.setText(str(votes))

    def executeDemocracyThread(self):
        while True:
            try:
                status = self.program.setupTest.getDemocracyThreadStatus()
                gov = self.program.setupTest.getMetaGov()
                if not status or gov != 'democracy' or not self.democracyTimer.isActive():
                    continue
                # somehow make it to where it checks if this command variable is the same as executed last time, otherwise it'll increase vote infinitely
                currentItem = self.listWidget_2.item(0)
                lastItem = self.program.setupTest.getLastDemocracyItem()
                if currentItem == lastItem:
                    continue
                
                command = currentItem.text()
                self.program.setupTest.setLastDemocracyItem(currentItem)
                print(command)
                # this adds the command to the 'vote list' or increments vote on already existing candidate
                self.program.setupTest.metaCommand(command)
                self.updateVoteCountOnUi()
                
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
    ui.democracyThread.start()
    test_stup_window.show()
    sys.exit(app.exec_())