#
#
#
import sys
import argparse

from PySide import QtCore
from PySide import QtGui
from PySide import QtWebKit
from PySide.QtCore import Qt

#===============================
#
#
parser = argparse.ArgumentParser()
parser.add_argument('X', type = int, help = '1st is x')
parser.add_argument('Y', type = int, help = '2nd is y')
parser.add_argument('W', type = int, help = '3rd is w')
parser.add_argument('H', type = int, help = '4th is h')
parser.add_argument('U', type = str, help = '5th is u')

arg = parser.parse_args()
left = arg.X
top = arg.Y
width = arg.W
height = arg.H
url = arg.U

app = QtGui.QApplication(sys.argv)
web = QtWebKit.QWebView()

web.setWindowFlags(Qt.FramelessWindowHint)
web.setGeometry(left, top, width, height)
web.setAttribute(Qt.WA_DeleteOnClose, False)
web.setFocusPolicy(Qt.NoFocus)
web.setContextMenuPolicy(Qt.NoContextMenu)
web.setDisabled(True)
web.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
web.page().mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
web.load(url)
web.show()

sys.exit(app.exec_())

#
#
#
