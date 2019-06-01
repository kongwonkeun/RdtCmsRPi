#
#
#
import os
import json

#===============================
#
#
class XiboConfig:

    def __init__(self, path = None):
        self.path = path
        self.saveDir = None
        self.url = None
        self.serverKey = None
        self.strTimeFmt = None
        self.cmsTzOffset = None
        self.res_file_ext = None
        self.layout_file_ext = None
        self.xmdsVersion = None
        self.xmrPubUrl = None
        self.clientId = None
        self.load()
        pass

    @property
    def defaults(self):
        #***********************
        #   9*3600 --> UTC+9 --> depends on your cms location
        # 
        return {
            'cmsTzOffset': 9*3600,
            'layout_file_ext': '.xml',
            'res_file_ext': '.html',
            'saveDir': '/home/pi/xibo/saveDir',
            'serverKey': 'rdtone',
            'strTimeFmt': '%Y-%m-%d %H:%M:%S',
            'url': 'http://35.221.100.165/xibo',
            'xmdsVersion': 5,
            'xmrPubUrl': 'tcp://35.221.100.165:9505',
            'clientId': 'rdt-pi-x'
        }

    def load(self):
        tmp = {}
        if  os.path.isfile(self.path):
            with open(self.path) as f:
                try:
                    tmp = json.load(f)
                except ValueError:
                    tmp = {}
        for k, v in tmp.iteritems():
            if  getattr(self, k) is None:
                setattr(self, k, v)
        for k, v in self.defaults.iteritems():
            if  getattr(self, k) is None:
                setattr(self, k, v)

    def save(self):
        data = {}
        for k, v in self.defaults.iteritems():
            if  'path' == k:
                continue
            data[k] = getattr(self, k)
        with open(self.path, 'w') as f:
            json.dump(data, f, indent = 4, separators = (',', ': '), sort_keys = True)

#
#
#