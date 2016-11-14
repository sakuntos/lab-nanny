""" This script runs a webserver that transmits the data from arduino.

The script runs a web application in a certain PORT. Periodically,
the server polls the ArduMon for data using the SerialDataFetcher. The data
is then sent out as a JSON dictionary to the clients connected.

Clients can connect to the machine running this server, and the connection is
performed through the websocket SOCKETNAME using port SOCKETPORT
"""
EMULATE = True
import time
import json
import datetime
from communications import SerialCommManager as SCM
import sys
#Uncomment if arduino_emulator is needed
if EMULATE:
    from arduino_emulator import ArduinoSerialEmulator

import socket
from serial.serialutil import SerialException
from tornado import websocket, web, ioloop
from communications.SerialCommManager import write_handshake

import threading
import SimpleHTTPServer
import SocketServer
PORT = 3000

SOCKETNAME = r'/ArduMon1'
SOCKETNAME2 = r'/ArduMon2'
SOCKETPORT = 8001
SOCKETPORT2 = 8002

message_digital_0 = 65

PERIODICITY = 500

class WebSocketHandler(websocket.WebSocketHandler):
    #on open of this socket
    def open(self):
        #TODO: Have a way to clean-up the emulated arduino
        # For emulation, uncomment the following lines
        if EMULATE:
            my_emulator = ArduinoSerialEmulator()
            emulation_port = my_emulator.report_server()
            my_emulator.start()
        else:
            emulation_port=[]

        print 'Connection established.'
        self.verbose = True

        self.arduino_serial_comms= SCM.SerialCommManager(0.001, verbose=self.verbose,
                                                         emulatedPort=emulation_port)

        print 'Data fetcher setup'
        ## Set up a periodic call to self.send_data, with a periodicity in miliseconds
        self.callback = ioloop.PeriodicCallback(self.send_data,PERIODICITY)
        self.callback.start()

 #close connection
    def on_close(self):
        print 'Connection closed.'

    def check_origin(self, origin):
        return True

    def on_message(self, message):
        """ The message sent to the arduino is a character around 65.

        To indicate a HIGH pin, add the pin number to 65.
        To indicate a LOW pin, subtract the pin number to 65, minus one.
        This is to distinguish between +0 and -0.
        """
        split_message = message.split(',')
        pinValue = int(split_message[1])
        ## We will use 65+pinNumber for HIGH signals, and 65-pinNumber-1 for LOW signals
        ## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
        if pinValue:
            pinNumber = chr(int(split_message[0])+message_digital_0)
        else:
            pinNumber = chr(message_digital_0-int(split_message[0])-1)
        if self.verbose:
            print '\n\n--------------------------------------'
            print 'Message from web received. Init comms'
            print 'Pin Value',pinValue
            print 'Initial pin calculated {}, value {}, sending {}----------------'.format(split_message[0], pinValue,(pinNumber))
        self.arduino_serial_comms.poll_arduino(handshake_func=write_handshake,
                                               command=pinNumber)
    def convert_message_to_command(self,message):
        split_message = message.split(',')
        pinValue = int(split_message[1])

        ## We will use 65+pinNumber for HIGH signals, and 65-pinNumber-1 for LOW signals
        ## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
        if pinValue:
            pinNumber = chr(int(split_message[0])+message_digital_0)
        else:
            pinNumber = chr(message_digital_0-int(split_message[0])-1)
        return pinValue, pinNumber

  # Our function to send new (random) data for charts
    def send_data(self):
        """ This function sends data through the websocket.

        It is typically called as part of a periodic callback.
        """
        try:
            t, channels = self.arduino_serial_comms.poll_arduino()
            print "Data acquired"
            #create a bunch of random data for various dimensions we want
            point_data = self.convert_data(channels)
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

    def convert_data(self, list_of_data):
        list_of_data = [datum[0]*3.3/4095 for datum in list_of_data]
        point_data =  {
            'ch0': list_of_data[0],
            'ch1' : list_of_data[1],
            'ch2' : list_of_data[2],
            'ch3' : list_of_data[3],
            'ch4' : list_of_data[4],
            'ch5' : list_of_data[5],
            'x': time.time(),
            'error':False
        }
        return point_data

def main():
    #Starting web server
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print "serving at port", PORT
    thread = threading.Thread(target=httpd.serve_forever)
    thread.setdaemon = True

    try:
        thread.start()

        #create new web app w/ websocket endpoint available at SOCKETNAME
        print "Starting websocket server program. Awaiting client requests to open websocket ..."
        application1 = web.Application([(SOCKETNAME, WebSocketHandler)])
        application1.listen(SOCKETPORT)
        #application2 = web.Application([(SOCKETNAME2, WebSocketHandler)])
        #application2.listen(SOCKETPORT2)
        print 'Websocket established in {}:{}/{}'.format(socket.gethostbyname(socket.gethostname()),
                                                     SOCKETPORT,SOCKETNAME)   #socket.gethostbyname(socket.getfqdn())
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        httpd.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()
