import sys, os
import csv
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSvg import *
import math
import time, datetime

def printMinuteSecondDelta(delta):
    s = delta.total_seconds()
    return '{min:02d}:{sec:02d}'.format(min=int(s % 3600) // 60, sec=int(s % 60))

labelFontCoeff = 15
countDownFontCoeff = 20
logoSizeCoeffMin = 0.17
logoSizeCoeffMax = 0.35


class App(QWidget):
    def __init__(self, states):
        super().__init__()
        self.title = 'IPT clock'
        self.state = 0
        self.prev_state = 0
        self.states = states

        self.setWindowTitle(self.title)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(255,255,255))
        self.setPalette(p)

        # Title of the state
        self.label = QLabel()
        self.label.setText(self.states[self.state]['name'])
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont('Arial', self.frameGeometry().height()/labelFontCoeff))

        # Initialize the clock
        self.m = AnalogClock(self.states[self.state]['duration'], parent=self)
        self.m.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.m.show()

        # Right layout
        self.countDown = QLabel()
        self.countDown.setAlignment(Qt.AlignCenter)
        self.countDown.setFont(QFont('Arial', self.frameGeometry().height()/countDownFontCoeff))
        self.rightLayout = QVBoxLayout()

        self.rightLayout.addWidget(self.label)
        self.rightLayout.addWidget(self.m)
        self.rightLayout.addWidget(self.countDown)

        # Left layout
        self.leftLayout = QVBoxLayout()
        self.logoIPT = QLabel()

        if hasattr(sys, "_MEIPASS"):  # For PyInstaller
            IPTFile = os.path.join(sys._MEIPASS, 'img1.png')
        else:
            IPTFile = 'img1.png'

        self.pixmapIPT = QPixmap(IPTFile)
        self.logoIPT.setPixmap(self.pixmapIPT)
        self.logoIPT.setMinimumSize(1, 1)
        self.logoIPT.installEventFilter(self)

        self.logoIPT.setMinimumWidth(self.frameGeometry().width()*logoSizeCoeffMin)
        self.logoIPT.setMaximumWidth(self.frameGeometry().width()*logoSizeCoeffMax)

        self.leftLayout.addWidget(self.logoIPT)

        # Complete layout
        self.fullLayout = QHBoxLayout()
        self.fullLayout.addLayout(self.leftLayout)
        self.fullLayout.addLayout(self.rightLayout)
        self.setLayout(self.fullLayout)

        self.childWindow = ClockControls(self)  # Clock controls
        self.childWindow.generateList(states)

        # Start at first event
        self.selectState(0)

    def eventFilter(self, source, event):
        if (source is self.logoIPT and event.type() == QEvent.Resize):
            # re-scale the pixmap when the label resizes
            self.logoIPT.setPixmap(self.pixmapIPT.scaled(
                self.logoIPT.size(), Qt.KeepAspectRatio,
                Qt.SmoothTransformation))
        return super(QWidget, self).eventFilter(source, event)

    def selectState(self, i):
        self.childWindow.list.setCurrentItem(self.childWindow.statesList[i])

    def setEvent(self, i):
        if i < len(self.states):
            self.prev_state = self.state
            self.state = i
            print('Stepping to state {}'.format(
                self.states[self.state]['name']))

            self.m.reset(self.states[self.state]['duration'],self.states[self.state]['force_step'])

            self.update_state_appearance()
        else:
            self.close()

    def returnToLastState(self):
        print('Canceling mistake')
        self.state = self.prev_state

        self.childWindow.list.currentItemChanged.disconnect(self.childWindow.changeState)
        self.selectState(self.state)
        self.childWindow.list.currentItemChanged.connect(self.childWindow.changeState)

        self.m.cancelChange()

        self.update_state_appearance()

    def startTimeout(self):
        print('Timeout')
        self.m.startTimeout()
        self.label.setText(self.states[self.state]['name']+ '<br />(Timeout)')
        self.update()

    def stopTimeout(self):
        print('End of timeout')
        self.label.setText(self.states[self.state]['name'])
        self.update()

    def update_state_appearance(self):
            # Change the label for the state name
            self.label.setText(self.states[self.state]['name'])

            self.update()

    def stepEvent(self):
        if self.m.timeout:
            self.m.stopTimeout()
        else:
            i = self.state
            self.selectState(i+1)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_N:
            self.setEvent(self.state + 1)

    def resizeEvent(self, event):
        self.label.setFont(QFont('Arial', self.frameGeometry().height()/labelFontCoeff))
        self.countDown.setFont(QFont('Arial', self.frameGeometry().height()/countDownFontCoeff))

        self.logoIPT.setMinimumWidth(self.frameGeometry().width()*logoSizeCoeffMin)
        self.logoIPT.setMaximumWidth(self.frameGeometry().width()*logoSizeCoeffMax)

class AnalogClock(QWidget):

    def __init__(self, duration, parent=None):
        super().__init__(parent)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(10)
        self.startPause = datetime.datetime.now()
        self.timeout = False

        self.elapsedTimeClock = datetime.timedelta()
        self.prev_elapsed = datetime.timedelta()
        self.datestart = datetime.datetime.now()
        self.prev_datestart = self.datestart

        self.duration = duration
        self.force_step = False
        self.prev_duration = self.duration
        self.paused = True
        self.overtime = False

        self.parent = parent

        self.setMinimumSize(500, 500)
        self.elapsedTime = 0
        self.timeout_duration = 60
        self.t_elapsedC = 0
        self.timeout_start = 0
        self.prev_pause = 0

    def paintEvent(self, event):
        side = int(min(self.width(), self.height()) * 0.8 / 2)
        if not self.paused:
            if self.timeout:
                self.t_elapsedC = (datetime.datetime.now() - self.timeout_start)
            else:
                self.elapsedTimeClock = (datetime.datetime.now() - self.datestart)
                self.prev_elapsed = datetime.datetime.now() - self.prev_datestart
        self.elapsedTime = self.elapsedTimeClock.total_seconds()

        # Create and start a QPainter
        self.painter = QPainter()

        self.painter.begin(self)
        self.painter.setRenderHint(QPainter.Antialiasing)

        # Put the origin at the center
        self.painter.translate(self.width() / 2, self.height() / 2)

        # Setup pen and brush
        self.painter.setPen(Qt.NoPen)
        self.painter.setBrush(QColor(0, 200, 0))

        # Do the actual painting
        self.painter.save()
        currentAngle = - 2 * math.pi * self.elapsedTime / self.duration
        if not(abs(currentAngle) > 2 * math.pi):
            self.painter.drawPie(-side, -side, 2 * side, 2 * side, 90*16,
                                 currentAngle * (360 / (2 * math.pi)) * 16)
            self.parent.countDown.setText(
                'Time remaining : ' + printMinuteSecondDelta(datetime.timedelta(seconds=self.duration) - self.elapsedTimeClock))
        elif 4 * math.pi > abs(currentAngle) > 2 * math.pi:
            self.overtime = True
            self.painter.drawPie(-side, -side, 2 * side,
                                 2 * side, 90 * 16, 360 * 16)
            self.painter.setBrush(QColor(200, 0, 0))
            self.painter.drawPie(-side, -side, 2 * side, 2 * side, 90 * 16,
                                 (currentAngle + 2 * math.pi) *
                                 (360 / (2 * math.pi)) * 16)
        else:
            self.painter.setBrush(QColor(200, 0, 0))
            self.painter.drawPie(-side, -side, 2 * side,
                                 2 * side, 90 * 16, 360 * 16)
        # timeout
        if self.timeout:
            self.painter.setBrush(QColor(235, 120, 0))
            t_angle = - 2 * math.pi * self.t_elapsedC.total_seconds() / self.timeout_duration
            self.painter.drawPie(-side, -side, 2 * side, 2 * side,
                                 currentAngle * (360 / (2 * math.pi)) * 16 + 90*16,
                                 t_angle * (360 / (2 * math.pi)) * 16)
            self.parent.countDown.setText(
                'Time remaining : ' + printMinuteSecondDelta(datetime.timedelta(seconds=self.duration) - self.elapsedTimeClock)
                + ' (' + printMinuteSecondDelta(datetime.timedelta(seconds=self.timeout_duration) - self.t_elapsedC) + ')')
            delta = datetime.timedelta(seconds=self.timeout_duration) - self.t_elapsedC
            if delta.total_seconds() < 0:
                self.stopTimeout()
        self.painter.setPen(QColor(0, 0, 0))
        self.painter.setBrush(Qt.NoBrush)
        self.painter.drawLine(QPoint(0, 0), QPoint(
            -side * math.cos(math.pi / 2 - currentAngle),
            -side * math.sin(math.pi / 2 - currentAngle)))
        self.painter.drawArc(-side, -side, 2 * side,
                             2 * side, 90 * 16, 360 * 16)
        self.painter.restore()

        self.painter.end()

        if self.overtime and self.force_step and self.parent:
            self.parent.stepEvent()


    def switchPause(self):
        if self.paused:
            self.paused = False
            # Act as if there was no pause
            delta = (datetime.datetime.now() - self.startPause)
            self.datestart += delta
            self.prev_datestart += delta
            if self.timeout:
                self.timeout_start += delta
        else:
            self.paused = True
            if self.timeout:
                self.t_elapsedC = (datetime.datetime.now() - self.timeout_start)
            else:
                self.elapsedTimeClock = (datetime.datetime.now() - self.datestart)
                self.prev_elapsed = (datetime.datetime.now() - self.prev_datestart)
            self.startPause = datetime.datetime.now()

    def reset(self, duration, force_step=False):
        self.overtime = False
        self.prev_duration = self.duration
        self.prev_force_step = self.force_step
        self.prev_datestart = self.datestart
        self.duration = duration
        self.force_step = force_step
        self.datestart = datetime.datetime.now()

        if self.paused:
            self.prev_pause = self.startPause
            self.startPause = datetime.datetime.now()

        self.elapsedTimeClock = datetime.timedelta()
        self.datestart = datetime.datetime.now()

    def cancelChange(self):
        self.elapsedTimeClock = self.prev_elapsed
        self.duration = self.prev_duration
        self.datestart = self.prev_datestart
        if self.paused:
            self.startPause = self.prev_pause

    def startTimeout(self):
        self.timeout = True
        self.t_elapsedC = datetime.timedelta()
        self.timeout_start = datetime.datetime.now()

    def stopTimeout(self):
        self.timeout = False
        delta = (datetime.datetime.now() - self.timeout_start)
        self.datestart += delta
        self.prev_datestart += delta
        self.parent.stopTimeout()

    def addTime(self, toadd):
        self.duration += toadd


class ClockControls(QDialog):
    def __init__(self, parent,):
        QDialog.__init__(self, parent)
        self.title = 'IPT clock controls'
        self.state = 0
        self.setWindowTitle(self.title)
        self.parent = parent


        # list of states
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.changeState)

        # step to next state button
        self.nextButton = QPushButton()
        self.nextButton.setText('Next')
        self.nextButton.clicked.connect(self.parent.stepEvent)


        # pause and start button
        self.pauseButton = QPushButton()
        self.pauseButton.setText('Start')
        self.pauseButton.clicked.connect(self.switchPause)

        # timeout button
        self.timeout = QPushButton()
        self.timeout.setText('Timeout')
        self.timeout.clicked.connect(self.parent.startTimeout)

        # button to cancel mistake
        self.cancelMistake = QPushButton()
        self.cancelMistake.setText('Cancel mistake')
        self.cancelMistake.clicked.connect(self.parent.returnToLastState)

        # time modifiers
        self.add1m = QPushButton()
        self.add1m.setText('+ 1 minute')
        self.add1m.clicked.connect(self.addMinute)

        self.rem1m = QPushButton()
        self.rem1m.setText('- 1 minute')
        self.rem1m.clicked.connect(self.removeMinute)

        self.add5s = QPushButton()
        self.add5s.setText('+ 5 seconds')
        self.add5s.clicked.connect(self.add5sec)

        self.rem5s = QPushButton()
        self.rem5s.setText('- 5 seconds')
        self.rem5s.clicked.connect(self.remove5sec)

        self.manualTimeS = QSpinBox()
        self.manualTimeS.setValue(10)
        self.manualTimeS.setMaximum(59)
        self.manualTimeS.setSuffix('s')
        self.manualTimeS.setSingleStep(5)

        self.manualTimeM = QSpinBox()
        self.manualTimeM.setValue(0)
        self.manualTimeM.setMaximum(60)
        self.manualTimeM.setSuffix('m')

        self.moreTime = QPushButton()
        self.moreTime.setText('+')
        self.moreTime.clicked.connect(self.addTime)

        self.remTime = QPushButton()
        self.remTime.setText('-')
        self.remTime.clicked.connect(self.removeTime)


        # layout
        self.vLayout = QVBoxLayout()
        self.vLayout.addWidget(self.list)
        self.vLayout.addWidget(self.nextButton)
        self.vLayout.addWidget(self.pauseButton)
        self.vLayout.addWidget(self.timeout)

        self.holder = QFrame()
        self.holder.setFrameShadow(QFrame.Sunken)
        self.holder.setFrameShape(QFrame.Panel)
        self.holder.setLineWidth(2)
        self.grid = QGridLayout()
        self.grid.addWidget(self.add1m, 1, 1)
        self.grid.addWidget(self.rem1m, 1, 2)
        self.grid.addWidget(self.add5s, 2, 1)
        self.grid.addWidget(self.rem5s, 2, 2)
        self.hLayout1 = QHBoxLayout()
        self.hLayout1.addWidget(self.manualTimeM)
        self.hLayout1.addWidget(self.manualTimeS)
        self.grid.addLayout(self.hLayout1,3,1)
        self.hLayout2 = QHBoxLayout()
        self.hLayout2.addWidget(self.moreTime)
        self.hLayout2.addWidget(self.remTime)
        self.grid.addLayout(self.hLayout2,3,2)

        self.holder.setLayout(self.grid)

        self.vLayout.addWidget(self.holder)
        self.vLayout.addWidget(self.cancelMistake)


        self.setLayout(self.vLayout)

    def generateList(self, states):
        self.statesList = []
        for state in states:
            item = QListWidgetItem('{} ({} s)'.format(
                state['name'].replace('<br />','').replace('<br/>',''), state['duration']))
            self.statesList.append(item)
            self.list.addItem(item)

    def switchPause(self):
        if self.parent.m.paused:
            self.pauseButton.setText('Pause')
        else:
            self.pauseButton.setText('Start')
        self.parent.m.switchPause()

    def changeState(self, curr):
        new_state = self.statesList.index(curr)
        self.parent.setEvent(new_state)

    def addMinute(self):
        self.parent.m.addTime(60)

    def removeMinute(self):
        self.parent.m.addTime(-60)

    def add5sec(self):
        self.parent.m.addTime(5)

    def remove5sec(self):
        self.parent.m.addTime(-5)

    def addTime(self):
        dt = self.manualTimeS.value() + self.manualTimeM.value()*60
        self.parent.m.addTime(dt)

    def removeTime(self):
        dt = self.manualTimeS.value() + self.manualTimeM.value()*60
        self.parent.m.addTime(-dt)

if __name__ == '__main__':
    if hasattr(sys, "_MEIPASS"):  # For PyInstaller
        statesFile = os.path.join(sys._MEIPASS, 'states.csv')
    else:
        statesFile = 'states.csv'

    states = []
    with open(statesFile, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='|')
        for row in reader:
            state = {'name': row[0], 'duration': float(row[1])*60}
            state['force_step'] = ( len(row) > 2 and row[2] )
            states.append(state)

    app = QApplication(sys.argv)
    ex = App(states)
    ex.show()
    ex.childWindow.show()
    sys.exit(app.exec_())
