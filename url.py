#
#
#
import signal
import sys
import os

from PySide import QtCore
from PySide import QtGui
from PySide.QtCore import QTimer
from PySide.QtCore import Qt
from PySide.QtGui import QLabel

#===============================
#
#
def handler():
    app.quit()

#===============================
#
#
app = QtGui.QApplication(sys.argv)
win = app.desktop().screenGeometry()

signal.signal(signal.SIGINT, handler)

#---- kong ---- for RPi
f = os.popen('hostname -I')
r = f.read()
ip = r.split(' ')[0]
#----

t = QTimer()
t.setSingleShot(True)
t.timeout.connect(handler)
t.start(10000)

url = QLabel()
url.setWindowFlags(Qt.FramelessWindowHint)
url.setGeometry(win)
url.setAttribute(Qt.WA_DeleteOnClose, False)
url.setFocusPolicy(Qt.NoFocus)
url.setContextMenuPolicy(Qt.NoContextMenu)
url.setStyleSheet('background-color: black;')
url.setText('<font size=10 color=white>http://%s:8080</font>' % ip)
url.setAlignment(Qt.AlignCenter)
url.show()

sys.exit(app.exec_())

#
#
#