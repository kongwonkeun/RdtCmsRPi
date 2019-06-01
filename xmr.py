#
#
#
from Crypto import Random

import zmq

#===============================
#
#
class Subscriber:

    def __init__(self, url, channel, callback):
        self.url = url
        #---- kong ----
        self.reboot = 'R'
        self.screenOff = 'F'
        self.screenOn = 'O'
        self.clearCache = 'X'
        self.clearContent = 'C'
        #----
        self.channel = channel
        self.callback = callback
        self.context = zmq.Context()
        self.push = None
        self.stop_command = Random.new().read(16)

    def run(self):
        sub = self.context.socket(zmq.SUB)
        sub.connect(self.url)

        #---- kong ----
        sub.setsockopt_string(zmq.SUBSCRIBE, self.reboot.decode('ascii'))
        sub.setsockopt_string(zmq.SUBSCRIBE, self.screenOff.decode('ascii'))
        sub.setsockopt_string(zmq.SUBSCRIBE, self.screenOn.decode('ascii'))
        sub.setsockopt_string(zmq.SUBSCRIBE, self.clearCache.decode('ascii'))
        sub.setsockopt_string(zmq.SUBSCRIBE, self.clearContent.decode('ascii'))
        sub.setsockopt_string(zmq.SUBSCRIBE, self.channel.decode('ascii'))
        #----

        push = self.context.socket(zmq.PUSH)
        port = push.bind_to_random_port('tcp://127.0.0.1')
        self.push = push

        pull = self.context.socket(zmq.PULL)
        pull.connect('tcp://127.0.0.1:%d' % port)

        poller = zmq.Poller()
        poller.register(pull, zmq.POLLIN)
        poller.register(sub, zmq.POLLIN)

        while True:
            socks = dict(poller.poll())
            if  sub in socks and socks[sub] == zmq.POLLIN:
                message = sub.recv_multipart()
                #---- kong ----
                if  len(message) == 3 and message[0] in (self.reboot, self.screenOff, self.screenOn, self.clearCache, self.clearContent, self.channel):
                    if  callable(self.callback):
                        self.callback(message[1:])
                #----
            if  pull in socks and socks[pull] == zmq.POLLIN:
                control = pull.recv()
                if  self.stop_command == control:
                    break

    def stop(self):
        self.push.send(self.stop_command)

#
#
#