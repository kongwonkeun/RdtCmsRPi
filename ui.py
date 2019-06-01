#
#
#
import os
import time

from PySide.QtCore import Qt
from PySide.QtCore import QThread
from PySide.QtCore import QTimer
from PySide.QtGui import QMainWindow
from PySide.QtGui import QWidget

import xlf
from xmdsthread import XmdsThread
from xmrthread import XmrThread
from xlfview import RegionView

#===============================
#
#
class XiboWidget(QWidget):

    def __init__(self, xmds, parent):
        super(XiboWidget, self).__init__(parent)
        self.xmds = xmds

    def queue_stats(self, type_, from_date, to_date, schedule_id, layout_id, media_id):
        self.xmds.queue_stats(type_, from_date, to_date, schedule_id, layout_id, media_id)

#===============================
#
#
class XiboWindow(QMainWindow):

    def __init__(self, config):
        super(XiboWindow, self).__init__()
        self.schedule_id = '0'
        self.config = config
        self.region_view = []
        self.xmds = None
        self.xmr = None
        self.running = False
        self.layout_id = None
        self.layout_time = (0, 0)
        self.setup_xmr()
        self.setup_xmds()
        self.xibo_widget = XiboWidget(self.xmds, self) 
        self.setCentralWidget(self.xibo_widget)
        self.layout_timer = QTimer()
        self.layout_timer.setSingleShot(True)
        self.layout_timer.timeout.connect(self.stop)
        self.url = False
        if  self.url == False:
            #---- kong ----
            os.system('./dist/url') # for RPi
            #----
            self.url = True
        self.setStyleSheet('background-color: black;')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.xmds.stop()
        if  self.xmr:
            self.xmr.stop()
        if  exc_tb or exc_type or exc_val:
            pass

    def setup_xmds(self):
        self.xmds = XmdsThread(self.config, self)
        self.xmds.layout_signal.connect(self.set_layout)
        self.xmds.downloaded_signal.connect(self.item_downloaded)
        if  self.config.xmdsVersion > 4:
            self.xmds.set_xmr_info(self.xmr.channel, self.xmr.pubkey)
        self.xmds.start(QThread.IdlePriority)

    def setup_xmr(self):
        if  self.config.xmdsVersion > 4:
            self.xmr = XmrThread(self.config, self)
            self.xmr.start(QThread.IdlePriority)

    def set_layout(self, layout_id, schedule_id, layout_time):
        #---- kong ----
        if  self.layout_id != layout_id:
            self.stop()
            self.play(layout_id, schedule_id)
        elif self.layout_time != layout_time:  #---- for the layout repeated
            self.stop()
            self.play(layout_id, schedule_id)
        #----
        self.layout_id = layout_id
        self.schedule_id = schedule_id
        self.layout_time = layout_time
        if  schedule_id and layout_time[1]:
            stop_time = layout_time[1] - time.time()
            if  stop_time > 604800:  #---- week to sec
                stop_time = 604800
            self.layout_timer.setInterval(int(stop_time * 1000))  #---- msec
            self.layout_timer.start()

    def item_downloaded(self, entry):
        if  'layout' == entry.type and self.layout_id == entry.id:
            self.stop()
            self.play(self.layout_id, self.schedule_id)

    def play(self, layout_id, schedule_id):
        path = "%s/%s%s" % (self.config.saveDir, layout_id, self.config.layout_file_ext)
        layout = xlf.get_layout(path)
        if  not layout:
            print '---- ui: layout error ----'
            return False
        self.setStyleSheet('background-color: %s' % layout['bgcolor'])
        
        #---- kong ----
        for region in layout['regions']:
            region['layout_id'] = layout_id
            region['schedule_id'] = schedule_id
            region['save_dir'] = self.config.saveDir
            view = RegionView(region, self.xibo_widget)
            self.region_view.append(view)

        if  self.region_view:
            for view in self.region_view:
                view.play()
        #----
        return True

    def stop(self):
        if  self.region_view:
            for view in self.region_view:
                view.stop()

        self.region_view = []  #---- del self._region_view[:]
        self.xibo_widget = None
        self.xibo_widget = XiboWidget(self.xmds, self)
        self.setCentralWidget(self.xibo_widget)

#
#
#