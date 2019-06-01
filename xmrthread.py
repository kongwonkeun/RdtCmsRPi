#
#
#
import base64
import calendar
import os
import json
import time

from PySide.QtCore import QThread
from PySide.QtCore import Signal
from PySide.QtCore import Slot

from Crypto.PublicKey import RSA
from hashlib import md5
from ast import literal_eval

import util
import xmds
import xmr

#===============================
#
#
class XmrThread(QThread):

    message_signal = Signal(list)

    def __init__(self, config, parent):
        super(XmrThread, self).__init__(parent)
        self.config = config
        self.xmrkey = 'xmrkey.json'
        self._channel = ''
        self._pubkey = ''
        self._prikey = ''
        self.prepare_keys()
        self.sub = xmr.Subscriber(
            self.config.xmrPubUrl,
            self._channel,
            self.handle_message
        )

    def run(self):
        self.sub.run()

    def stop(self):
        self.sub.stop()

    def handle_message(self, messages):
        if  messages[0] == '':
            pass
        else:
            self.decrypt_message(messages)

    def decrypt_message(self, messages):
        sealed_data = base64.decodestring(messages[1])
        env_key = base64.decodestring(messages[0])
        #---- kong ---- for RPi
        cmd_str = util.openssl_open(sealed_data, env_key, self._prikey)
        cmd = literal_eval(cmd_str)
        print cmd
        for k, v in cmd.iteritems():
            if  'commandCode' == k:
                if  'R' == v:
                    os.system('reboot')
                if  'F' == v:
                    os.system('vcgencmd display_power 0')
                if  'O' == v:
                    os.system('vcgencmd display_power 1')
                if  'X' == v:
                    os.system('rm -r /tmp/_MEI*')
                if  'C' == v:
                    os.system('rm /home/pi/xibo/saveDir/*')
                    os.system('reboot')
            if  'action' == k:
                if  'reKeyAction' == v:
                    os.system('rm /home/pi/xibo/xmrkey.json')
                    os.system('reboot')
        #----

    def prepare_keys(self):
        key = {}
        if  os.path.isfile(self.xmrkey):
            with open(self.xmrkey) as f:
                try:
                    key = json.load(f)
                except ValueError:
                    key = {}
            for k, v in key.iteritems():
                if  k == 'prikey':
                    self._prikey = v
                if  k == 'pubkey':
                    self._pubkey = v
                if  k == 'ch':
                    self._channel = v
        else:
            rsa = RSA.generate(2048)
            self._prikey = rsa.exportKey()
            self._pubkey = rsa.publickey().exportKey()
            self._channel = md5('%d %s' % (time.time(), self.config.xmrPubUrl)).hexdigest()
            for k, v in self.defaults.iteritems():
                if  k == 'prikey':
                    key[k] = self._prikey
                if  k == 'pubkey':
                    key[k] = self._pubkey
                if  k == 'ch':
                    key[k] = self._channel
            with open(self.xmrkey, 'w') as f:
                json.dump(key, f, indent=4, separators=(',', ': '), sort_keys=True)

    @property
    def pubkey(self):
        return self._pubkey

    @property
    def channel(self):
        return self._channel

    @property
    def defaults(self):
        return {
            'prikey': 'prikeyval',
            'pubkey': 'pubkeyval',
            'ch': 'chval',
        }

#
#
#