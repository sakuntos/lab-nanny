#!/usr/bin/python
import tornado
import tornado.websocket
from tornado import gen, websocket, web, ioloop

import sys
import json
import time
import socket
import logging

from serial.serialutil import SerialException
from communications import SerialCommManager as SCM
from communications.SerialCommManager import write_handshake

USER_REFERENCE = 'lab6'
EMULATE = False
VERBOSE = True

if EMULATE:
    from arduino_emulator import ArduinoSerialEmulator



LOCATION = "ws://10.3.20.25:8001/nodes_ws"
PORT = 3000
message_digital_0 = 65

def convert_message_to_command(message):
    """ This converts a message received through the socket to a command that arduino will interpret.

    :param message: Typically a string indicating the pin number and the state ( eg. "1,false")
    :return: (pinValue, pinNumber)
    """

    split_message = message.split(',')
    print message
    pinValue = int(split_message[2]) # split_message[1] in ('True','true')
    user = split_message[0]

    ## We will use 65+pinNumber for HIGH signals, and 65-pinNumber-1 for LOW signals
    ## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
    if pinValue:
        pinNumber = chr(int(split_message[1])+message_digital_0)
    else:
        pinNumber = chr(message_digital_0-int(split_message[1])-1)

    return (user, pinValue, pinNumber)

def convert_data(list_of_data):
    list_of_data = [round(datum[0]*3.3/4095,5) for datum in list_of_data]
    point_data =  {
        'user':USER_REFERENCE,
        'error':False,   #Distinguishes it from the error state
        'ch0': list_of_data[0],
        'ch1' : list_of_data[1],
        'ch2' : list_of_data[2],
        'ch3' : list_of_data[3],
        'ch4' : list_of_data[4],
        'ch5' : list_of_data[5],
        'x': time.time()
    }
    return point_data

@gen.coroutine
def keepalive_ws():
    """
    Callback executed in the slave nodes.

    It initialises the communications with the arduino and connects, via a websocket, to a certain LOCATION.
    Then, it enters a loop and waits for signals coming from the master server.

    :return:
    """
    #TODO: should the data coming from the arduino be converted here? or in the master?
    # pro: master does not need to know about the details of the acquisition
    # con: more data sent through the websocket

    #Init
    verbose = False
    try:
        if EMULATE:
            print('(node) Emulating arduino')
            my_emulator = ArduinoSerialEmulator()
            emulation_port = my_emulator.report_server()
            my_emulator.start()
        else:
            emulation_port=[]

        print('(node) Setting-up arduino communications')
        arduino_serial_comms= SCM.SerialCommManager(0.001, verbose=verbose,
                                                         emulatedPort=emulation_port)
    except SerialException:
        print('Serial exception ocurred. Try again in a few seconds')
        raise

    ################################
    # CONNECT AND LISTEN TO MASTER
    ################################
    #Structure of the "listen" loop:
    # - Read message
    # - Convert to arduino command
    # - Connect to arduino using the command
    # - Receive data from arduino and send back to master
    errorState = False
    try:
        client = yield tornado.websocket.websocket_connect(LOCATION)
        print('(node) waiting for messages:')
        # Init_msg = yield client.read_message()
        # if Init_msg == 'Init':
        #     client.write_message(USER_REFERENCE)
        # print('(node) Init message {}'.format(Init_msg))
    except socket.error as error:
        if error.errno == 10061:
            print '\nConnection refused by host. Maybe it is not running?'
            raise KeyboardInterrupt


    while not errorState:

        msg = yield client.read_message()
        user, pinValue, pinNumber = convert_message_to_command(msg)
        if user in (USER_REFERENCE,'X'):
            if VERBOSE:
                print("(node) incoming msg is: {}".format(msg))
                print("(node) command to arduino: {}".format(pinNumber))
            #This "try" block will look for KeyboardInterrupt events to close the program
            try:
                print pinNumber, pinValue
                t, channels = arduino_serial_comms.poll_arduino(handshake_func=write_handshake,
                                                       command=pinNumber)
                point_data = convert_data(channels)
                client.write_message(json.dumps(point_data))

            # Sometimes the Arduino disconnectis, throwing a SerialException. We handle this and let the master server know
            # there is an error.
            except SerialException:
                # If the connection is not accessible, send a "standard" dictionary, with the 'error' flag
                point_data = {
                    'x': time.time(),
                    'user':USER_REFERENCE,
                    'error':True
                }
                print 'Serial Exception'
                client.write_message(json.dumps(point_data))



if __name__ == "__main__":
    try:
        tornado.ioloop.IOLoop.instance().run_sync(keepalive_ws)
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().close()
        print 'Exiting gracefully'
