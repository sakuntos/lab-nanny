#!/usr/bin/python
"""Slave nodes for lab-nanny

Communicates with arduino using a serial connection and connects with the
master server through websockets.

The node server instance starts by setting up the connection to the arduino
using the SlaveNode.connect_to_arduino() method.
The typical application would call the slave_node_instance.keepalive_ws
method inside a loop, which is a coroutine working asynchronously, which
'keeps alive' the connection between the arduino and the master server.
The normal operation of the script keeps an outer "while True" loop that
performs several actions in case of connection errors.

The communication between the master server and the arduino is "bridged" by
using the Slavenode.message_bridging_arduino method, which converts
-- messages sent from the master server to an arduino command using the
   convert_message_to_command function.
-- a list of channels to a JSON dictionary, using the SlaveNode.convert_data
   method) which is written into the master server's websocket

To deploy:
-- Change the DICT_CONTENTS variable to state the actual contents of the
   channels.
-- Run from the root folder using 'python -m servers.server_node', and using
   the required modifiers such as the lab references (lab6, lab7,...), the
   master websocket address, using emulation,...

   E.g.
    python -m servers.server_node -ws masterserver_fqdn:8001/nodes_ws -r lab7

"""
import tornado
import tornado.websocket
from tornado import gen, websocket, web, ioloop
from tornado.httpclient import HTTPError

from serial.serialutil import SerialException
from communications import SerialCommManager as SCM
from communications.SerialCommManager import ArduinoConnectionError,\
                                            handshake_func
from server_master import METAKEYWORD

import json
import time
import socket

import argparse

USER_REFERENCE = 'lab7'
EMULATE = True
VERBOSE = True
##Settings for the Arduino MEGA
ADC_MAXINT = 1023  # Maximum integer for analog channels (10 bit precision)
ADC_MAXVOLT = 5.0   #For conversion of the analog readings

# Location of the master server. It is prepended by the 'ws://' protocol.
MASTER_LOCATION = "ws://127.0.0.1:8001/nodes_ws" #"ws://localhost:8001/nodes_ws" #10.3.20.25

# To make an arduino pin HIGH or LOW, we send it a character (int) whose value is
# -- MESSAGE_PINVALUE_0+pinNumber for HIGH signals,
# -- MESSAGE_PINVALUE_0-pinNumber-1 for LOW signals
## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
MESSAGE_PINVALUE_0 = 65

# Time format
TFORMAT = '%y/%m/%d %H:%M:%S'

DICT_CONTENTS = {
            'ch0' :'temp sensor',
            'ch1' : 'more stuff',
            'ch2' : 'probe spectroscopy',
            'ch3' : 'empty',
            'ch4' : 'empty',
            'ch5' : 'empty',
            'ch6' : 'empty',
            METAKEYWORD : True
        }

class SlaveNode(object):

    def __init__(self, emulate=False,
                 verbose=True,
                 masterWSlocation=MASTER_LOCATION,
                 reference=USER_REFERENCE,
                 arduino_port = []):
        self.emulate = emulate
        self.location = masterWSlocation
        self.reference = reference
        self.verbose = verbose
        self.master_server = []  #This will be the result of tornado.websocket.websocket_connect(self.location)
        self.arduino_port = arduino_port

        #Register node in master (metadata)
        self.metadata_registered = False  # If the metadata has been sent to the master server
        self.metadata_dict = DICT_CONTENTS
        self.metadata_dict['user']=self.reference


        print("Initiating Slave Node {}".format(self.reference))
        if self.verbose:
            print("Verbose mode")
        print("Emulation = {}".format(self.emulate))
        self.is_arduino_connected = False
        self.is_master_connected = False
        self.emulation_port = []

        self.arduino_COMS = self.connect_to_arduino()



    def connect_to_arduino(self):
        """
        Tries to establish a connection with an arduino device in the computer.

        The connection is made using the SerialCommManager.SerialCommManager class.

        :return: An instance of SerialCommManager.
        """
        try:
            if self.emulate:
                print('(node) Emulating arduino')
                my_emulator = ArduinoSerialEmulator()
                self.emulation_port = my_emulator.report_server()
                my_emulator.start()
            else:
                self.emulation_port=[]


            print('(node) Setting-up arduino communications')
            arduino_COMS= SCM.SerialCommManager(0.01,
                                                verbose=self.verbose,
                                                emulatedPort=self.emulation_port,
                                                arduino_port=self.arduino_port)

            if arduino_COMS.is_arduino_connected():
                self.is_arduino_connected = True
                print('(node) Arduino connected')
            else:
                self.is_arduino_connected = False
            return arduino_COMS

        except SerialException:
            print('Serial exception ocurred. Try again in a few seconds @{}'\
                  .format(time.strftime(TFORMAT)))
            self.is_arduino_connected = False
            raise
        except ValueError as err:
            raise ArduinoConnectionError

    def message_bridging_arduino(self,msg):
        """
        Method that bridges the connection between the master server and the arduino

        For every message sent from the master server, it checks whether the message
        is addressed to this node (through the "user" of the message), and it
        "polls" the arduino. Later, using the response of the arduino, a message is
        sent back to the master server as a response. The serial communications to
        arduino is performed using the SerialCommManager.SerialCommManager instance
        in self.arduino_comms, which sends a handshake through the
        poll_arduino method.

        The communication with the master server is performed by writing the
        appropriate response into the websocket instance in self.master_server.
        This function performs two conversions:
            -- messages (string) sent from the master server to an arduino command
               using the convert_message_to_command function.
            -- a list of channels to a JSON dictionary, using the
               SlaveNode.convert_data method, which is later written into the master
               server's websocket

        :param msg: Message from the master node, currently implemented using the
                    syntax 'user,pin_number,pin_value', where
                    user=lab6,lab7,... [If user=X, all arduinos will respond.]
                    pin_number=integer,
                    pin_value=(0,1).
        :type msg: str

        :return:
        """
        if self.is_arduino_connected:
            user, pinValue, pinNumber = convert_message_to_command(msg)
            #Check if the message is for this node
            if (user in (self.reference,'X')) and self.is_arduino_connected:
                if self.verbose:
                    print("(node) Incoming msg is: {}".format(msg))
                    print("(node) CMD to arduino:  {}".format(pinNumber))
                #This "try" block will look for KeyboardInterrupt events to close the program

                poll_output = self.arduino_COMS.poll_arduino(
                                    handshake_func=handshake_func,
                                    command=pinNumber)
                if poll_output is not None:
                    t, channels = poll_output
                    point_data = self.convert_data(channels)
                    self.master_server.write_message(json.dumps(point_data))

        else:
            self.send_message_on_serial_exception()


    @gen.coroutine
    def reconnect_to_arduino(self):
        """ Reconnects to an arduino device, trying to cope with typical errors.
        :return:
        """
        while not self.is_arduino_connected:
            try:
                if self.verbose:
                    print('(node) Trying to connect @{}'.format(time.time()))
                self.arduino_COMS.init_arduino_connection()
                self.is_arduino_connected = True
            except SerialException:
                print('(node) Serial exception ocurred. Try again in a few seconds')
                self.is_arduino_connected = False
                raise
            except ValueError as err:
                raise
            except ArduinoConnectionError:
                time.sleep(1)

    def send_message_on_serial_exception(self):
        """ Default message sent if a serial exception is present.
        :return:
        """
        point_data = {
                        'x': time.time(),
                        'user':self.reference,
                        'error':True
                    }
        self.master_server.write_message(json.dumps(point_data))


    @gen.coroutine
    def keepalive_ws(self):
        """
        Callback executed in the slave nodes.

        It initialises the communications with the arduino and connects, via a
        websocket, to a certain location defined in self.location.

        Then, it enters a loop and waits for signals coming from the master
        server.

        :return:
        """
        #TODO: should the data coming from the arduino be converted here? or in the master?
        # pro: master does not need to know about the details of the acquisition
        # con: more data sent through the websocket

        ################################
        # CONNECT AND LISTEN TO MASTER
        ################################
        #Structure of the "listen" loop:
        # - Read message
        # - Convert to arduino command
        # - Connect to arduino using the command
        # - Receive data from arduino and send back to master # Initialises the error state

        while not self.is_master_connected:
            try:
                print("(node) Connecting to WS connection = {} @{}"\
                      .format(self.location,
                              time.strftime(TFORMAT)))
                self.master_server = yield tornado.websocket.websocket_connect(self.location)
                print('(node) Connection with master server started')
                self.is_master_connected = True
            except socket.error as error:
                if error.errno == 10061:
                    print('\n(node) Connection refused by host. Maybe it is not running? Waiting')
                    time.sleep(2)
                self.is_master_connected = False
                self.metadata_registered = False
            except HTTPError as error:
                print('(node) Connection taking quite long... @{}'\
                      .format(time.strftime(TFORMAT)))


        #Main loop for data acquisition/sending
        #Acquire data from master
        while self.is_master_connected :
            try:
                if not self.metadata_registered:
                    self.master_server.write_message(json.dumps(self.metadata_dict))
                    self.metadata_registered=True

                msg = yield self.master_server.read_message() #we may use a callback here, instead of the rest of this code block
            except UnboundLocalError:
                print('\n(node)Connection refused by host. Maybe Master server is not running?')
                self.is_master_connected = False
                self.metadata_registered = False
                raise HostConnectionError

            #Process data:
            if msg is not None:
                try:
                    self.message_bridging_arduino(msg)

                # Sometimes the Arduino disconnectis, throwing a SerialException. We handle this and let the master server know
                # there is an error.
                except (SerialException, ArduinoConnectionError):
                    # If the connection is not accessible, send a "standard" dictionary, with the 'error' flag
                    self.send_message_on_serial_exception()
                    print('(node) Serial Exception @{}'.format(time.time()))
                    if self.is_arduino_connected:
                        self.is_arduino_connected = False
                        self.arduino_COMS.cleanup()
                        self.reconnect_to_arduino()
                except ValueError as err:
                    print('(node) ValueError thrown')
                    print(err.args)

                except RuntimeError as err:
                    if err.args[0]=='generator raised StopIteration':
                        print('(node) Cannot find arduino connection')
                    else:
                        raise err
                except KeyboardInterrupt:
                    self.is_master_connected=False
                    self.metadata_registered = False
                    raise

            else:
                print('(node) Could not retrieve message from server. It may be disconnected.')
                self.is_master_connected = False
                self.metadata_registered = False
                #raise KeyboardInterrupt


    def convert_data(self,list_of_data):
        """Converts data from arduino to a value in volts.

        Arduino Due provides ADC with 12 bits resolution. This function converts the
        data sent from the Arduino to a 0-3.3V range

        Typically, the list of data

        :param list_of_data: typically a list with values 0-(2^12-1) for a number of analog channels

        """
        list_of_data = [round(datum*ADC_MAXVOLT/ADC_MAXINT,5) for datum in list_of_data]
        list_of_data[2] = list_of_data[2]*100  #Temperature conversion
        point_data =  {
            'user': self.reference,
            'error': False,   #Distinguishes it from the error state
            'ch0': list_of_data[0],
            'ch1' : list_of_data[1],
            'ch2' : list_of_data[2],
            'ch3' : list_of_data[3],
            'ch4' : list_of_data[4],
            'ch5' : list_of_data[5],
            'ch6' : list_of_data[6],
            'x': time.time()
        }
        return point_data




def convert_message_to_command(message):
    """ This converts a message received through the socket to a command that
    Arduino will interpret.

    A message typically has the syntax "source, channel, state", where "source"
    is the reference found in USER_REFERENCE, "channel" is the digital channel
    to affect, and "state" is either 0 or 1.

    :param message: Typically a string indicating the source, the pin number and
    the state ( eg. "lab6,1,false")
    :return: (pinValue, pinNumber)
    """

    split_message = message.split(',')
    pinValue = int(split_message[2]) # split_message[1] in ('True','true')
    user = split_message[0]

    ## We will use MESSAGE_PINVALUE_0+pinNumber for HIGH signals,
    ## and MESSAGE_PINVALUE_0-pinNumber-1 for LOW signals
    ## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
    if pinValue:
        pinNumber = chr(int(split_message[1]) + MESSAGE_PINVALUE_0)
    else:
        pinNumber = chr(MESSAGE_PINVALUE_0 - int(split_message[1]) - 1)

    return (user, pinValue, pinNumber)

### ERRORS
class HostConnectionError(Exception):
    """ This error is thrown whenever the master server is disconnected
    """
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e","--emulate", help="If emulation of the arduino is required (*nix only)",
    type=int,default=0)
    parser.add_argument("-ws","--websocket", help="address of the master server websocket",
                        default=MASTER_LOCATION)
    parser.add_argument("-r","--reference",help="Reference for this node ('lab6')",
        default=USER_REFERENCE)
    parser.add_argument("-p","--arduport",help="Arduino port",
        default=0)

    parser.add_argument("-v","--verbose",help="Activate verbose",
        type=int,default=0)
    args = parser.parse_args()
    if args.emulate:
        from servers.arduino_emulator import ArduinoSerialEmulator

    try:
        slaveNodeInstance = SlaveNode(emulate=args.emulate,
                                      masterWSlocation=args.websocket,
                                      reference=args.reference,
                                      verbose=args.verbose,
                                      arduino_port=args.arduport)
    except KeyboardInterrupt:
        print('Exiting gracefully')

    while True:
        try:
            print('\n-----------------------------\nStarting Slave node  {}\n-----------\
------------------\n'.format(args.reference))
            tornado.ioloop.IOLoop.instance().run_sync(slaveNodeInstance.keepalive_ws)
        except ArduinoConnectionError as err:
            print(err.args)
            print('(node) Problem found in serial connection. Exiting')
        #except TypeError as err:
        #    print('(node) TypeError thrown')
        #    print(err)
        except ValueError as err:
            print(type(err))
            print(err.args)
        except RuntimeError as err:
            if err.args[0]=='generator raised StopIteration':
                print('(node) Cannot find arduino connection')
            else:
                raise err
        except HostConnectionError:
            print('(node) Master server is disconnected.')
            slaveNodeInstance.is_master_connected = False
            slaveNodeInstance.metadata_registered = False
            time.sleep(10)
        except KeyboardInterrupt:
            tornado.ioloop.IOLoop.instance().stop()
            tornado.ioloop.IOLoop.instance().close()
            print('(node) Exiting gracefully')
            break
        time.sleep(2)
