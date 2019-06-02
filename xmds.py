#
#
#
import base64
import exceptions
import os
import re
import sys
import uuid

from hashlib import md5
from suds import WebFault as SoapFault
from suds.client import Client as SoapClient
from xml.etree import ElementTree

#===============================
#
#
class Client:

    def __init__(self, url, cid, ver=4):
        self.keys = {
            'server': '',
            'hardware': ''
        }
        self.url = url
        self.ver = ver
        self.cid = cid
        self._mac_address = None
        self.client = None
        self.set_identity()
        self.connect()

    def set_identity(self):
        node = uuid.getnode()
        if  node is None:
            raise RuntimeError('no network interface found')
        self._mac_address = ':'.join([str('%012x' % node)[x:x + 2] for x in range(0, 12, 2)])
        url = '%s://%s/%s/%s' % (self.cid, sys.platform, os.name, self._mac_address)
        self.keys['hardware'] = uuid.uuid3(uuid.NAMESPACE_URL, url.encode('utf-8'))

    @property
    def mac_address(self):
        return self._mac_address

    def was_connected(self):
        return self.client and self.client.wsdl is not None

    def set_keys(self, server_key=None):
        self.keys['server'] = server_key

    #***************************
    #
    #
    def connect(self):
        try:
            self.client = SoapClient(self.url + '/xmds.php?WSDL&v=' + str(self.ver))
        except exceptions.IOError, err:
            print '---- xmds: connection io error ----'
            self.client = None
        return self.client is not None

    #***************************
    #
    #
    def send_request(self, method=None, params=None):
        if  not self.was_connected():
            self.connect()
            return None
        response = None
        text = None
        tmp = None
        try:
            if  'registerDisplay'.lower() == method.lower():
                params.macAddress = self._mac_address
                if  self.ver == 4:
                    text = self.client.service.RegisterDisplay(
                        self.keys['server'],
                        self.keys['hardware'],
                        getattr(params,'name'),
                        getattr(params,'type'),
                        getattr(params,'version'),
                        getattr(params,'code'),
                        getattr(params,'os'),
                        getattr(params,'macAddress')
                    )
                elif self.ver == 5:
                    text = self.client.service.RegisterDisplay(
                        self.keys['server'],
                        self.keys['hardware'],
                        getattr(params,'name'),
                        getattr(params,'type'),
                        getattr(params,'version'),
                        getattr(params,'code'),
                        getattr(params,'os'),
                        getattr(params,'macAddress'),
                        getattr(params,'xmrChannel'),
                        getattr(params,'xmrPubKey')
                    )
                tmp = RegisterDisplayResponse()

            elif 'requiredFiles'.lower() == method.lower():
                text = self.client.service.RequiredFiles(
                    self.keys['server'],
                    self.keys['hardware']
                )
                tmp = RequiredFilesResponse()

            elif 'schedule' == method.lower():
                text = self.client.service.Schedule(
                    self.keys['server'],
                    self.keys['hardware']
                )
                tmp = ScheduleResponse()

            elif 'getFile'.lower() == method.lower():
                text = self.client.service.GetFile(
                    self.keys['server'],
                    self.keys['hardware'],
                    getattr(params,'fileId'),
                    getattr(params,'fileType'),
                    getattr(params,'chunkOffset'),
                    getattr(params,'chuckSize')
                )
                tmp = GetFileResponse()

            elif 'getResource'.lower() == method.lower():
                text = self.client.service.GetResource(
                    self.keys['server'],
                    self.keys['hardware'],
                    getattr(params,'layoutId'),
                    getattr(params,'regionId'),
                    getattr(params,'mediaId')
                )
                tmp = GetResourceResponse()

            elif 'submitStats'.lower() == method.lower():
                text = self.client.service.SubmitStats(
                    self.keys['server'],
                    self.keys['hardware'],
                    params.dumps()
                )
                tmp = SuccessResponse()

        except SoapFault, err:
            print '---- xmds: soap fault error ----'
        except exceptions.IOError, err:
            print '---- xmds: soap io error ----'

        if  tmp and tmp.parse(text):
            response = tmp
        return response

#===============================
#
#
class XmdsResponse(object):

    def __init__(self):
        self.content = None

    def parse(self, text):
        return False

    def save_as(self, path):
        if  not self.content:
            return 0
        try:
            with open(path, 'w') as f:
                f.write(self.content)
                f.flush()
                os.fsync(f.fileno())
            written = os.stat(path).st_size
        except IOError:
            print '---- xmds: file io error ----'
            written = 0
        return written

    def parse_file(self, path):
        try:
            with open(path, 'r') as f:
                return self.parse(f.read())
        except IOError:
            print '---- xmds: file io error ----'
            return False

    def content_md5sum(self):
        content = ''
        if  self.content:
            content = self.content
        return md5(content).hexdigest()

#===============================
#
#
class XmlParam(object):

    def __init__(self, tag):
        xml = '<?xml version="1.0" encoding="UTF-8" ?>'
        self.tag = xml + '\n<{0}>%s</{0}>'.format(tag)
        self.tmp = ''

    def dumps(self):
        return self.tag % self.tmp

#===============================
#
#
class RegisterDisplayParam:

    def __init__(
            self,
            display_name='xibopy',
            display_type='linux',
            version='1.8',
            code=102,
            operating_system='Linux',
            mac_address=''
        ):
        self.name = display_name
        self.type = display_type
        self.version = version
        self.code = code
        self.os = operating_system
        self.macAddress = mac_address
        # for xmds v5
        self.xmrChannel = None
        self.xmrPubKey = None

class RegisterDisplayResponse:

    def __init__(self):
        self.status = None
        self.code = None
        self.message = None
        self.version_instructions = None
        self.details = {}
        # for xmds v5
        self.commands = {}
        self.content = None

    def parse(self, text):
        if  not text:
            return False
        root = ElementTree.fromstring(text)
        if  'display' != root.tag:
            return 0
        for key, val in root.attrib.iteritems():
            if  hasattr(self, key):
                setattr(self, key, val)
        for detail in root:
            if  detail.text:
                if  'commands' == detail.tag:
                    for command in detail:
                        self.commands[command.tag] = command.text
                else:
                    self.details[detail.tag] = detail.text
        self.content = text
        return True

#===============================
#
#
class RequiredFilesEntry:

    def __init__(self):
        self.type = ''
        self.id = ''
        self.size = 0
        self.md5 = ''
        self.download = ''
        self.path = ''
        self.layoutid = ''
        self.regionid = ''
        self.mediaid = ''
        self.updated = 0

class RequiredFilesResponse(XmdsResponse):

    def __init__(self):
        super(RequiredFilesResponse, self).__init__()
        self.files = None

    def parse(self, text):
        if  not text:
            return False
        text = re.sub(
            r'(type="resource")(\s+id=".*")(\s+layout)',
            r'\1\3',
            text
        )
        root = ElementTree.fromstring(text)
        if  'files' != root.tag:
            return False
        self.files = []
        for child in root:
            if  not 'file' == child.tag:
                continue
            entry = RequiredFilesEntry()
            for key, val in child.attrib.iteritems():
                if  hasattr(entry, key):
                    setattr(entry, key, val)
            self.files.append(entry)
        self.content = text
        return True

#===============================
#
#
class ScheduleLayoutEntry:

    def __init__(self):
        self.file = None
        self.fromdt = None
        self.todt = None
        self.scheduleid = None
        self.priority = None
        self.dependents = None

class ScheduleResponse(XmdsResponse):

    def __init__(self):
        super(ScheduleResponse, self).__init__()
        self.layout = ''
        self.layouts = []
        self.dependants = []

    def parse(self, text):
        if  not text:
            return False
        root = ElementTree.fromstring(text)
        if  'schedule' != root.tag:
            return False
        for child in root:
            if  'layout' == child.tag:
                layout = ScheduleLayoutEntry()
                for key, val in child.attrib.iteritems():
                    if  hasattr(layout, key):
                        setattr(layout, key, val)
                self.layouts.append(layout)
            elif 'default' == child.tag:
                for key, val in child.attrib.iteritems():
                    if  'file' == key:
                        self.layout = val
            elif 'dependants' == child.tag:
                for dep in child:
                    if  dep.text:
                        self.dependants.append(dep.text)
        self.content = text
        return True

#===============================
#
#
class GetFileParam:

    def __init__(self, file_id='', file_type='', offset=0, size=0):
        self.fileId = file_id
        self.fileType = file_type
        self.chunkOffset = offset
        self.chuckSize = size

class GetFileResponse(XmdsResponse):

    def __init__(self):
        super(GetFileResponse, self).__init__()

    def parse(self, text):
        if  text and len(text) > 0:
            self.content = base64.decodestring(text)
            return True
        return False

#===============================
#
#
class GetResourceParam:

    def __init__(self, layout_id='', region_id='', media_id=''):
        self.layoutId = layout_id
        self.regionId = region_id
        self.mediaId = media_id

class GetResourceResponse(XmdsResponse):
    def __init__(self):
        super(GetResourceResponse, self).__init__()

    def parse(self, text):
        if  text and len(text) > 0:
            self.content = text
            return True
        return False

#===============================
#
#
class MediaInventoryParam(XmlParam):

    def __init__(self):
        super(MediaInventoryParam, self).__init__('files')

    def add(self, id_, complete, md5, last_checked):
        tmp = '<{} id="{}" complete="{}" md5="{}" lastChecked="{}" />'.format(
            'file', id_, complete, md5, last_checked
        )
        self.tmp += tmp

class SubmitLogParam(XmlParam):

    def __init__(self):
        super(SubmitLogParam, self).__init__('logs')

    def add(self, date, category, type_, message, method, thread):
        tmp = '<{} date="{}" category="{}" type="{}" message="{}" method="{}" thread="{}" />'.format(
            'log', date, category, type_, message, method, thread
        )
        self.tmp += tmp

class SubmitStatsParam(XmlParam):

    def __init__(self):
        super(SubmitStatsParam, self).__init__('stats')

    def add(self, type_, from_date, to_date, schedule_id, layout_id, media_id):
        self.tmp += '<{} type="{}" fromdt="{}" todt="{}" scheduleid="{}" layoutid="{}" mediaid="{}" />'.format(
            'stat', type_, from_date, to_date, schedule_id, layout_id, media_id
        )

class SuccessResponse(XmdsResponse):

    def __init__(self):
        super(SuccessResponse, self).__init__()

    def parse(self, text):
        if text:
            self.content = text
            return True
        return False

#
#
#