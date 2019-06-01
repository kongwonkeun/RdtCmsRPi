#
#
#
import os
import json
import cgi
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

MY_PORT = 8080

#===============================
#
#
class MyHandler(BaseHTTPRequestHandler):

    Page = '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>xibo cms configuration</title>
        </head>
        <body>
            <h1>Hello World !</h1>
            <form action="/post" method="POST">
                <p>Please tell me the ip and key of your cms.<br></p>
                <table>
                <tr><td>cms ip</td><td><input type="text" name="cms_ip"></td></tr>
                <tr><td>cms key</td><td><input type="text" name="cms_key"></td></tr>
                <tr><td>client id</td><td><input type="text" name="client_id"></td></tr>
                <tr><td></td><td><input type="submit" value="submit"></td></tr>
                </table>
            </form>
        </body>
    </html>
    '''

    PageCopyProtect = '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>xibo cms configuration</title>
        </head>
        <body>
            <h1>Hello World !</h1>
            <p>
                This is not an original copy of software for this device.<br>
                Please order the original software.
            </p>
        </body>
    </html>
    '''

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(self.Page)))
        self.end_headers()
        if  mySerial == x:
            self.wfile.write(self.Page)
        else:
            self.wfile.write(self.PageCopyProtect)
        return
    
    def do_HEAD(self):
        pass

    def do_POST(self):
        if  self.path == '/post':
            form = cgi.FieldStorage(
                fp = self.rfile,
                headers = self.headers,
                environ = {
                    'REQUEST_METHOD' : 'POST',
                    'CONTENT_TYPE' : self.headers['Content-Type'],
                }
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write('Thank You for using Me !\nI will reboot ...')

            self.config = './config.json'
            cfg = {}
            if  os.path.isfile(self.config):
                with open(self.config) as f:
                    try:
                        cfg = json.load(f)
                    except ValueError:
                        cfg = {}
            for k, v in cfg.iteritems():
                if  k == 'serverKey':
                    cfg[k] = form.getvalue('cms_key')
                if  k == 'url':
                    cfg[k] = 'http://%s/xibo' % form.getvalue('cms_ip')
                if  k == 'xmrPubUrl':
                    cfg[k] = 'tcp://%s:9505' % form.getvalue('cms_ip')
                if  k == 'clientId':
                    cfg[k] = form.getvalue('client_id')
            with open(self.config, 'w') as f:
                json.dump(cfg, f, indent = 4, separators = (',',': '), sort_keys = True)
                #os.system('reboot')
            return

#===============================
#
#
if  __name__ == '__main__':

    myAddress = ('',MY_PORT)
    #---- kong ---- SD serial number
    mySerial = '0x2a253dc5'
    #----
    
    #f = os.popen('cat /sys/block/mmcblk0/device/serial')
    #r = f.read()
    #x = r.split('\n')[0]

    #---- kong ---- for test
    x = mySerial
    #----

    server = HTTPServer(myAddress,MyHandler)
    server.serve_forever()

#
#
#