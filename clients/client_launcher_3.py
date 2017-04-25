import webbrowser as wb

import sys
import http.server
from http.server import SimpleHTTPRequestHandler


HandlerClass = SimpleHTTPRequestHandler
ServerClass  = http.server.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 3000
server_address = ('127.0.0.1', port)

HandlerClass.protocol_version = Protocol
httpd = ServerClass(server_address, HandlerClass)

sa = httpd.socket.getsockname()
address = 'http://{}:{}/clients/datavis-master.html'.format(sa[0],sa[1])
print("Opening webbrowser instance at {}".format(address))
wb.open(address)
print(("Serving HTTP on {} port {}...".format(sa[0],sa[1])))
httpd.serve_forever()


    
