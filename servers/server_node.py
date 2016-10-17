""" This script
"""

import time
import json
import datetime
import SerialCommManager as SDF
import socket
from serial.serialutil import SerialException
from tornado import websocket, web, ioloop
from SerialCommManager import write_handshake


paymentTypes = ["cash", "tab", "visa","mastercard","bitcoin"]
namesArray = ['Ben', 'Jarrod', 'Vijay', 'Aziz']
SOCKETNAME = r'/ArduMon1'
SOCKETNAME2 = r'/ArduMon2'
SOCKETPORT = 8001
SOCKETPORT2 = 8002


class WebSocketHandler(websocket.WebSocketHandler):

    #on open of this socket
    def open(self):
        print 'Connection established.'
        self.data_fetcher= SDF.SerialCommManager(0.01, verbose=False)
        print 'Data fetcher setup'
        #ioloop to wait for 3 seconds before starting to send data
        ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=3), self.send_data)

 #close connection
    def on_close(self):
        print 'Connection closed.'
    def check_origin(self, origin):
        return True

    def on_message(self, message):
        self.data_fetcher.poll_arduino(handshake_func=write_handshake)
        print message

  # Our function to send new (random) data for charts
    def send_data(self):

        try:
            t, channels = self.data_fetcher.poll_arduino()
            print "Data acquired"
            #create a bunch of random data for various dimensions we want
            channels = [channel[0]*3.3/4095 for channel in channels]

            #create a new data point
            point_data = {
                'ch0': channels[0],
                'ch1' : channels[1],
                'ch2' : channels[2],
                'ch3' : channels[3],
                'ch4' : channels[4],
                'ch5' : channels[5],
                'x': time.time(),
                'error':False
            }
            #print point_data

        #write the json object to the socket
            self.write_message(json.dumps(point_data))
        except SerialException:
            #self.data_fetcher.cleanup()
            point_data = {
                  'ch0': 0,
                  'ch1' : 0,
                  'ch2' : 0,
                  'ch3' : 0,
                  'ch4' : 0,
                  'ch5' : 0,
                  'x': time.time(),
                  'error':True
            }
            print 'Serial Exception'
            self.write_message(json.dumps(point_data))

        #create new ioloop instance to intermittently publish data
        ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=0.1), self.send_data)

if __name__ == "__main__":
    #create new web app w/ websocket endpoint available at /websocket
    print "Starting websocket server program. Awaiting client requests to open websocket ..."
    application1 = web.Application([(SOCKETNAME, WebSocketHandler)])
    application1.listen(SOCKETPORT)
    #application2 = web.Application([(SOCKETNAME2, WebSocketHandler)])
    #application2.listen(SOCKETPORT2)
    print 'Websocket established in {}:{}/{}'.format(socket.gethostbyname(socket.gethostname()),
                                                     SOCKETPORT,SOCKETNAME)   #socket.gethostbyname(socket.getfqdn())
    ioloop.IOLoop.instance().start()
