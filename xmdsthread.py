#
# 
# 
import base64
import calendar
import os
import time

from PySide.QtCore import QThread
from PySide.QtCore import Signal
from PySide.QtCore import Slot

import util
import xmds
import xmr

#===============================
#
#
class XmdsThread(QThread):

    downloading_signal = Signal(str, str)
    downloaded_signal = Signal(object)
    layout_signal = Signal(str, str, tuple)

    def __init__(self, config, parent):
        super(XmdsThread, self).__init__(parent)
        self.config = config
        self.mac_address = None
        self.hardware_key = None
        self.xmds_stop = False
        self.xmds_running = False
        self.xmr_pubkey = ''
        self.xmr_channel = ''
        self.ss_param = None
        self.single_shot = False
        self.layout_id = '0'
        self.schedule_id = '0'
        self.layout_time = (0, 0)
        if  not os.path.isdir(config.saveDir):
            os.mkdir(config.saveDir, 0o700)
        self.xmdsClient = xmds.Client(config.url, config.clientId, ver=config.xmdsVersion)
        self.xmdsClient.set_keys(config.serverKey)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if  exc_tb or exc_type or exc_val:
            pass

    @Slot()
    def stop(self):
        self.xmds_stop = True
        while self.xmds_running:
            self.msleep(250)
        self.quit()

    def str_to_epoch(self, time_str):
        seconds = calendar.timegm(time.strptime(time_str, self.config.strTimeFmt))
        return seconds - self.config.cmsTzOffset

    def epoch_to_str(self, time_str):
        seconds = float(time_str)
        return time.strftime(self.config.strTimeFmt, time.gmtime(seconds + self.config.cmsTzOffset))

    def submit_stats(self):
        if  isinstance(self.ss_param, xmds.SubmitStatsParam):
            cl = self.xmdsClient
            resp = cl.send_request('SubmitStats', self.ss_param)
            success = xmds.SuccessResponse().parse(resp)
            if  success:
                self.ss_param = None

    #***********************
    #
    #
    def download(self, req_file_entry=None):
        if  not req_file_entry or not req_file_entry.files:
            return None
        cl = self.xmdsClient
        self.is_downloading = True
        get_resource_param = xmds.GetResourceParam()
        get_file_param = xmds.GetFileParam()
        for entry in req_file_entry.files:
            if  self.xmds_stop:
                break
            resp = None
            file_path = None
            downloaded = False
            if  'resource' == entry.type:
                file_path = '{0}/{1}_{2}_{3}{4}'.format(
                    self.config.saveDir,
                    entry.layoutid,
                    entry.regionid,
                    entry.mediaid,
                    self.config.res_file_ext
                )
                param = get_resource_param
                param.layoutId = entry.layoutid
                param.regionId = entry.regionid
                param.mediaId = entry.mediaid
                self.downloading_signal.emit(entry.type, file_path)
                resp = cl.send_request('GetResource', param)
                if  resp:
                    try:
                        with open(file_path, 'wb') as f:
                            f.write(resp.content)
                            f.flush()
                            os.fsync(f.fileno())
                            downloaded = True
                    except IOError:
                        print '---- xmdsthread: file io error ----'
            elif entry.type in ('media', 'layout'):
                file_ext = ''
                if  'layout' == entry.type:
                    file_ext = self.config.layout_file_ext
                file_path = self.config.saveDir + '/' + entry.path + file_ext
                if  util.md5sum_match(file_path, entry.md5):
                    continue
                param = get_file_param
                param.fileId = entry.id
                param.fileType = entry.type
                self.downloading_signal.emit(entry.type, file_path)
                try:
                    with open(file_path, 'wb') as f:
                        for offset in range(0, int(float(entry.size)), 1024*1024*2):
                            param.chuckSize = str(1024*1024*2)
                            param.chunkOffset = str(offset)
                            resp = cl.send_request('GetFile', param)
                            if  resp:
                                f.write(resp.content)
                                f.flush()
                                os.fsync(f.fileno())
                                downloaded = True
                except IOError:
                    print '---- xmdsthread: file io error ----'

            if  downloaded:
                self.downloaded_signal.emit(entry)

    #***********************
    #
    #
    def xmds_cycle(self):
        self.xmds_running = True
        self.xmds_stop = False
        cl = self.xmdsClient
        param = xmds.RegisterDisplayParam(display_name=self.config.clientId)
        #---- kong ----
        param.macAddress = cl.mac_address
        param.xmrChannel = self.xmr_channel
        param.xmrPubKey = self.xmr_pubkey
        #----
        sched_resp = xmds.ScheduleResponse()
        sched_cache = self.config.saveDir + '/schedule.xml'
        rf_cache = self.config.saveDir + '/rf.xml'
        collect_interval = 60

        while not self.xmds_stop:
            display = cl.send_request('RegisterDisplay', param)
            if  isinstance(display, xmds.RegisterDisplayResponse):
                if  'READY' == display.code:
                    collect_interval = display.details.get('collectInterval', 60)

            rf = cl.send_request('RequiredFiles')
            if  isinstance(rf, xmds.RequiredFilesResponse):
                if  not util.md5sum_match(rf_cache, rf.content_md5sum()):
                    rf.save_as(rf_cache)
                    self.download(rf)

            schedule = cl.send_request('Schedule')
            if  isinstance(schedule, xmds.ScheduleResponse):
                if  not util.md5sum_match(sched_cache, schedule.content_md5sum()):
                    schedule.save_as(sched_cache)
            else:
                if  sched_resp.parse_file(sched_cache):
                    schedule = sched_resp

            schedule_found = False
            if  schedule and schedule.layouts:
                for layout in schedule.layouts:
                    from_time = self.str_to_epoch(layout.fromdt)
                    to_time = self.str_to_epoch(layout.todt)
                    now_time = time.time()

                    if  to_time < now_time:
                        continue

                    if  from_time <= now_time <= to_time:
                        self.layout_id = layout.file
                        self.schedule_id = layout.scheduleid
                        self.layout_time = (from_time, to_time)
                        #---- kong ----
                        schedule_found = True
                        self.layout_signal.emit(self.layout_id, self.schedule_id, self.layout_time)
                        next_collect_time = time.time() + float(collect_interval)
                        while time.time() < next_collect_time and not self.xmds_stop:
                            self.msleep(5000)
                        #----
                        continue

                    if  now_time < from_time:
                        schedule_found = True
                        next_collect_time = time.time() + float(collect_interval)
                        while time.time() < next_collect_time and not self.xmds_stop:
                            self.msleep(5000)
                        break

            if  schedule and not schedule_found:
                ''' play default layout '''
                self.layout_id = schedule.layout
                self.schedule_id = None
                self.layout_time = (0, 0)
                self.layout_signal.emit(self.layout_id, self.schedule_id, self.layout_time)
                next_collect_time = time.time() + float(collect_interval)
                while time.time() < next_collect_time and not self.xmds_stop:
                    self.msleep(5000)

            self.__submit_stats()
            if  self.single_shot:
                break
        # while not ...

        self.xmds_running = False
        if  self.single_shot:
            self.quit()

    def run(self):
        if  not self.xmds_running:
            self.xmds_cycle()

    # def quit(self):
    #     self.stop()
    #     return super(XmdsThread, self).quit()

    def set_xmr_info(self, channel, pubkey):
        self.xmr_channel = channel
        self.xmr_pubkey = pubkey

    def queue_stats(self, type_, from_date, to_date, schedule_id, layout_id, media_id):
        if  self.ss_param is None:
            self.ss_param = xmds.SubmitStatsParam()
        self.ss_param.add(
            type_,
            self.epoch_to_str(from_date),
            self.epoch_to_str(to_date),
            schedule_id,
            layout_id,
            media_id
        )

#
#
#