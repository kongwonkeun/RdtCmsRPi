#
#
#
import os
import signal
import time

from PySide.QtCore import QObject
from PySide.QtCore import QProcess
from PySide.QtCore import QRect
from PySide.QtCore import QTimer
from PySide.QtCore import QUrl
from PySide.QtCore import Qt
from PySide.QtCore import SIGNAL
from PySide.QtCore import Signal
from PySide.QtCore import Slot
from PySide.QtGui import QImage
from PySide.QtGui import QLabel
from PySide.QtGui import QPixmap
from PySide.QtGui import QPixmapCache
from PySide.QtGui import QWidget
from PySide.QtWebKit import QWebView

#===============================
#
#
class MediaView(QObject):

    started_signal = Signal()
    finished_signal = Signal()

    def __init__(self, media, parent):
        super(MediaView, self).__init__(parent)
        self.parent = parent
        self.id = media['id']
        self.type = media['type']
        self.duration = media['duration']
        self.render = media['render']
        self.options = media['options']
        self.raws = media['raws']
        self.layout_id = media['layout_id']
        self.schedule_id = media['schedule_id']
        self.region_id = media['region_id']
        self.save_dir = media['save_dir']
        self.zindex = media['zindex']
        self.widget = None
        self.play_timer = QTimer(self)
        self.started = 0
        self.finished = 0
        self.errors = None
        self.connect_signals()

    def connect_signals(self):
        self.started_signal.connect(self.mark_started)
        self.finished_signal.connect(self.mark_finished)
        self.play_timer.setSingleShot(True)
        self.connect(self.play_timer, SIGNAL('timeout()'), self.stop)

    @staticmethod
    def make(media, parent):
        if  'type' not in media:
            return None
        if  'image' == media['type']:
            view = ImageMediaView(media, parent)
        elif 'video' == media['type']:
            view = VideoMediaView(media, parent)
        elif 'webpage' == media['type']:
            view = WebMediaView(media, parent)
        else:
            view = TextMediaView(media, parent)
        return view

    @Slot()
    def play(self):
        pass

    @Slot()
    def stop(self, delete_widget=False):
        if  self.is_finished():
            return False
        if  self.widget:
            tries = 10
            while tries > 0 and not self.widget.close():
                tries -= 1
                time.msleep(100)
            if  delete_widget:
                del self.widget  #---- ? ----
                self.widget = None
        self.finished_signal.emit()
        return True

    @Slot()
    def mark_started(self):
        self.started = time.time()

    @Slot()
    def mark_finished(self):
        if  not self.is_finished():
            self.finished = time.time()
            self.parent.queue_stats(
                'media',
                self.started,
                self.finished,
                self.schedule_id,
                self.layout_id,
                self.id
            )

    def is_started(self):
        return self.started > 0

    def is_finished(self):
        return self.finished > 0

    def is_playing(self):
        return self.is_started() and not self.is_finished()

    def set_default_widget_prop(self):
        if  self.widget is not None:
            self.widget.setAttribute(Qt.WA_DeleteOnClose, False)
            self.widget.setFocusPolicy(Qt.NoFocus)
            self.widget.setContextMenuPolicy(Qt.NoContextMenu)
            self.widget.setObjectName('%s-widget' % self.objectName())

#===============================
#
#
class ImageMediaView(MediaView):

    def __init__(self, media, parent):
        super(ImageMediaView, self).__init__(media, parent)
        self.widget = QLabel(parent)
        self.widget.setGeometry(media['geometry'])
        self.img = QImage()
        self.set_default_widget_prop()

    @Slot()
    def play(self):
        self.finished = 0
        path = '%s/%s' % (self.save_dir, self.options['uri'])
        rect = self.widget.geometry()
        self.img.load(path)
        self.img = self.img.scaled(
            rect.width(),
            rect.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        self.widget.setPixmap(QPixmap.fromImage(self.img))
        self.widget.show()
        self.widget.raise_()
        if  float(self.duration) > 0:
            self.play_timer.setInterval(int(float(self.duration) * 1000))
            self.play_timer.start()
        self.started_signal.emit()

    @Slot()
    def stop(self, delete_widget=False):
        #---- kong ----
        if  not self.widget:
            return False
        del self.img
        self.img = QImage()
        #----
        super(ImageMediaView, self).stop(delete_widget)
        return True

#===============================
#
#
class VideoMediaView(MediaView):

    def __init__(self, media, parent):
        super(VideoMediaView, self).__init__(media, parent)
        self.widget = QWidget(parent)
        self.process = QProcess(self.widget)
        self.process.setObjectName('%s-process' % self.objectName())
        self.std_out = []
        self.errors = []
        self.stopping = False
        self.mute = False
        self.widget.setGeometry(media['geometry'])
        self.connect(self.process, SIGNAL('error()'), self.process_error)
        self.connect(self.process, SIGNAL('finished()'), self.process_finished)
        self.connect(self.process, SIGNAL('started()'), self.process_started)
        self.set_default_widget_prop()
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.setInterval(1000)
        self.stop_timer.timeout.connect(self.process_timeout)
        #---- kong ---- for RPi
        self.rect = media['geometry']
        self.omxplayer = True
        #----

    @Slot()
    def process_timeout(self):
        os.kill(self.process.pid(), signal.SIGTERM)
        self.stopping = False
        if  not self.is_started():
            self.started_signal.emit()
        super(VideoMediaView, self).stop()

    @Slot(object)
    def process_error(self, err):
        print '---- process error ----'
        self.errors.append(err)
        self.stop()

    @Slot()
    def process_finished(self):
        self.stop()

    @Slot()
    def process_started(self):
        self.stop_timer.stop()
        if  float(self.duration) > 0:
            self.play_timer.setInterval(int(float(self.duration) * 1000))
            self.play_timer.start()
        self.started_signal.emit()
        pass

    @Slot()
    def play(self):
        self.finished = 0
        self.widget.show()
        self.widget.raise_()
        path = '%s/%s' % (self.save_dir, self.options['uri'])
        #---- kong ----
        if  self.omxplayer is True:
            left, top, right, bottom = self.rect.getCoords()
            rect = '%d,%d,%d,%d' % (left,top,right,bottom)
            args = [ '--win', rect, '--no-osd', '--layer', self.zindex, path ]
            self.process.start('omxplayer.bin', args)
            self.stop_timer.start()
        else:
            args = [ '-slave', '-identify', '-input', 'nodefault-bindings:conf=/dev/null', '-wid', str(int(self.widget.winId())), path ]
            self.process.start('mplayer', args)
            self.stop_timer.start()
        #----

    @Slot()
    def stop(self, delete_widget=False):
        #---- kong ----
        if  not self.widget:
            return False
        if  self.stopping or self.is_finished():
            return False
        self.stop_timer.start()
        self.stopping = True
        if  self.process.state() == QProcess.ProcessState.Running:
            if  self.omxplayer is True:
                self.process.write('q')
            else:
                self.process.write('quit\n')
            self.process.waitForFinished()
            self.process.close()
        super(VideoMediaView, self).stop(delete_widget)
        self.stopping = False
        self.stop_timer.stop()
        return True
        #----

#===============================
#
#
class WebMediaView(MediaView):

    def __init__(self, media, parent):
        super(WebMediaView, self).__init__(media, parent)
        self.widget = QWidget(parent)
        self.process = QProcess(self.widget)
        self.process.setObjectName('%s-process' % self.objectName())
        self.std_out = []
        self.errors = []
        self.stopping = False
        self.mute = False
        self.widget.setGeometry(media['geometry'])
        self.connect(self.process, SIGNAL('error()'), self.process_error)
        self.connect(self.process, SIGNAL('finished()'), self.process_finished)
        self.connect(self.process, SIGNAL('started()'), self.process_started)
        self.set_default_widget_prop()
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.setInterval(1000)
        self.stop_timer.timeout.connect(self.process_timeout)
        self.rect = self.widget.geometry()

    @Slot()
    def process_timeout(self):
        os.kill(self.process.pid(), signal.SIGTERM)
        self.stopping = False
        if  not self.is_started():
            self.started_signal.emit()
        super(WebMediaView, self).stop()

    @Slot(object)
    def process_error(self, err):
        print '---- process error ----'
        self.errors.append(err)
        self.stop()

    @Slot()
    def process_finished(self):
        self.stop()

    @Slot()
    def process_started(self):
        self.stop_timer.stop()
        if  float(self.duration) > 0:
            self.play_timer.setInterval(int(float(self.duration) * 1000))
            self.play_timer.start()
        self.started_signal.emit()
        pass

    @Slot()
    def play(self):
        self.finished = 0
        self.widget.show()
        self.widget.raise_()
        
        #---- kong ----
        url = self.options['uri']
        args = [
            #'--kiosk', 
            str(self.rect.left()), 
            str(self.rect.top()),
            str(self.rect.width()),
            str(self.rect.height()),
            QUrl.fromPercentEncoding(url)
        ]
        #self.process.start('chromium-browser', args)
        self.process.start('./dist/web', args)
        self.stop_timer.start()
        #----

    @Slot()
    def stop(self, delete_widget=False):
        #---- kong ----
        if  not self.widget:
            return False
        if  self.stopping or self.is_finished():
            return False
        self.stop_timer.start()
        self.stopping = True
        if  self.process.state() == QProcess.ProcessState.Running:
            #os.system('pkill chromium')
            os.system('pkill web')
            self.process.waitForFinished()
            self.process.close()
        super(WebMediaView, self).stop(delete_widget)
        self.stopping = False
        self.stop_timer.stop()
        return True
        #----
#===============================
#
#
class TextMediaView(MediaView):

    def __init__(self, media, parent):
        super(TextMediaView, self).__init__(media, parent)
        self.widget = QWebView(parent)
        self.widget.setGeometry(media['geometry'])
        self.set_default_widget_prop()
        self.widget.setDisabled(True)
        self.widget.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.widget.page().mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)

    @Slot()
    def play(self):
        self.finished = 0
        path = '%s/%s_%s_%s.html' % (
            self.save_dir,
            self.layout_id,
            self.region_id,
            self.id
        )
        self.widget.load('file://' + path)
        self.widget.show()
        self.widget.raise_()
        if  float(self.duration) > 0:
            self.play_timer.setInterval(int(float(self.duration) * 1000))
            self.play_timer.start()
        self.started_signal.emit()

    @Slot()
    def stop(self, delete_widget=False):
        #---- kong ----
        if  not self.widget:
            return False
        super(TextMediaView, self).stop(delete_widget)
        return True
        #----

#===============================
#
#
class RegionView:

    def __init__(self, region, parent):
        self.parent = parent
        self.id = region['id']
        self.width = region['width']
        self.height = region['height']
        self.left = region['left']
        self.top = region['top']
        self.media = region['media']
        self.zindex = region['zindex']
        self.options = region['options']
        self.loop = False
        if  'loop' in self.options:
            self.loop = bool(int(self.options['loop']))
        self.layout_id = region['layout_id']
        self.schedule_id = region['schedule_id']
        self.save_dir = region['save_dir']
        self.media_view = []
        self.media_index = 0
        self.media_length = 0
        self._stop = False
        self.populate_media()

    def populate_media(self):
        for media in self.media:
            media['layout_id'] = self.layout_id
            media['schedule_id'] = self.schedule_id
            media['region_id'] = self.id
            media['save_dir'] = self.save_dir
            media['zindex'] = self.zindex
            media['geometry'] = QRect(
                int(float(self.left)),
                int(float(self.top)),
                int(float(self.width)),
                int(float(self.height))
            )
            view = MediaView.make(media, self.parent)
            view.finished_signal.connect(self.play_next)
            self.media_view.append(view)
            self.media_length += 1

    def play(self):
        if  self._stop or self.media_length < 1:
            return None
        self.media_view[self.media_index].play()

    def play_next(self):
        self.media_index += 1
        if  self.loop:
            if  self.media_index >= self.media_length:
                self.media_index = 0
        if  self.media_index < self.media_length:
            self.play()

    def stop(self):
        self._stop = True
        for view in self.media_view:
            if  view.is_playing():
                view.stop(delete_widget=True)

        self.media_view = []  #---- del self._media_view[:]

#
#
#