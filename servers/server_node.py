# Slave nodes for lab-nanny
#
# Communicates with arduino using a serial connection and connects with the master server through websockets.

#!/usr/bin/python
import tornado
import tornado.websocket
from tornado import gen, websocket, web, ioloop

from serial.serialutil import SerialException
from communications import SerialCommManager as SCM
from communications.SerialCommManager import write_handshake, SerialConnectionException

import json
import time
import socket

import argparse

USER_REFERENCE = 'lab6'
EMULATE = True
VERBOSE = True
ADC_MAXINT = 4095
ADC_MAXVOLT = 3.3   #For conversion of the analog readings


LOCATION = "ws://localhost:8001/nodes_ws" #10.3.20.25
PORT = 3000
message_digital_0 = 65

class SlaveNode(object):

    def __init__(self,emulate=False,
                 verbose=False,
                 masterWSlocation=LOCATION,
                 reference=USER_REFERENCE):
        self.emulate = emulate
        self.location = masterWSlocation
        self.reference = reference
        self.verbose = verbose
        self.master_server = []

        self.is_arduino_connected = False
        self.is_master_connected = False
        self.arduino_COMS = []

        print("Initiating Slave Node {}".format(self.reference))
        if self.verbose:
            print("Verbose mode")
        print("Emulation = {}".format(self.emulate))
        print("Master WS connection = {}".format(self.location))


    def connect_to_arduino(self):
        try:
            if self.emulate:
                print('(node) Emulating arduino')
                my_emulator = ArduinoSerialEmulator()
                emulation_port = my_emulator.report_server()
                my_emulator.start()
            else:
                emulation_port=[]

            print('(node) Setting-up arduino communications')
            arduino_COMS= SCM.SerialCommManager(0.01,
                                                        verbose=self.verbose,
                                                        emulatedPort=emulation_port)

            self.is_arduino_connected = True
            return arduino_COMS

        except SerialException:
            print('Serial exception ocurred. Try again in a few seconds')
            self.is_arduino_connected = False
            raise
        except ValueError as err:
            print('I am here')
            raise

    def message_bridging_arduino(self):
        pass

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

        #Init
        self.arduino_COMS = self.connect_to_arduino()

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
                self.master_server = yield tornado.websocket.websocket_connect(self.location)
                print('(node) Waiting for messages')
                self.is_master_connected = True
            except socket.error as error:
                if error.errno == 10061:
                    print('\n(node) Connection refused by host. Maybe it is not running? Waiting')
                    time.sleep(2)
                self.is_master_connected = False


        #Main loop for data acquisition/sending
        while self.is_master_connected:
            try:
                msg = yield self.master_server.read_message() #we may use a callback here, instead of the rest of this code block
            except UnboundLocalError:
                print('\nConnection refused by host. Maybe Master server is not running?')
                self.is_master_connected = False
                raise DisconnectedHostError

            if msg is None:
                errorStte = True
                print('(node) Could not retrieve message from server. It may be disconnected.')
                raise KeyboardInterrupt

            #self.send_message_to_master(msg)
            user, pinValue, pinNumber = convert_message_to_command(msg)
            #Check if the message is for this node
            if user in (self.reference,'X'):
                if self.verbose:
                    print("(node) Incoming msg is: {}".format(msg))
                    print("(node) CMD to arduino:  {}".format(pinNumber))
                #This "try" block will look for KeyboardInterrupt events to close the program
                try:
                    t, channels = self.arduino_COMS.poll_arduino(
                                        handshake_func=write_handshake,
                                        command=pinNumber)
                    point_data = self.convert_data(channels)
                    self.master_server.write_message(json.dumps(point_data))

                # Sometimes the Arduino disconnectis, throwing a SerialException. We handle this and let the master server know
                # there is an error.
                except (SerialException, SerialConnectionException):
                    # If the connection is not accessible, send a "standard" dictionary, with the 'error' flag
                    point_data = {
                        'x': time.time(),
                        'user':self.reference,
                        'error':True
                    }
                    print('(node) Serial Exception @{}'.format(time.time()))
                    self.master_server.write_message(json.dumps(point_data))
                except ValueError as err:
                    print(err.args)
                except RuntimeError as err:
                    if err.args[0]=='generator raised StopIteration':
                        print('(node) Cannot find arduino connection')
                    else:
                        raise err
                except KeyboardInterrupt:
                    self.is_master_connected=False
                    raise

    def convert_data(self,list_of_data):
        """Converts data from arduino to a value in volts.

        Arduino Due provides ADC with 12 bits resolution. This function converts the
        data sent from the Arduino to a 0-3.3V range

        Typically, the list of data

        :param list_of_data: typically a list with values 0-(2^12-1) for a number of analog channels

        """
        list_of_data = [round(datum[0]*ADC_MAXVOLT/ADC_MAXINT,5) for datum in list_of_data]
        list_of_data[0] = list_of_data[0]*100  #Temperature conversion
        point_data =  {
            'user': self.reference,
            'error': False,   #Distinguishes it from the error state
            'ch0': list_of_data[0],
            'ch1' : list_of_data[1],
            'ch2' : list_of_data[2],
            'ch3' : list_of_data[3],
            'ch4' : list_of_data[4],
            'ch5' : list_of_data[5],
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

    ## We will use 65+pinNumber for HIGH signals, and 65-pinNumber-1 for LOW signals
    ## e.g. pin 0 LOW corresponds to 64 and pin 1 HIGH corresponds to 66
    if pinValue:
        pinNumber = chr(int(split_message[1])+message_digital_0)
    else:
        pinNumber = chr(message_digital_0-int(split_message[1])-1)

    return (user, pinValue, pinNumber)

class DisconnectedHostError(Exception):
    pass

def main():
    try:
        tornado.ioloop.IOLoop.instance().run_sync(keepalive_ws)
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().close()
        print('Exiting gracefully')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e","--emulate", help="If emulation of the arduino is required (*nix only)",
    type=int,default=0)
    parser.add_argument("-ws","--websocket",help="address of the master server websocket",
    default=LOCATION)
    parser.add_argument("-r","--reference",help="Reference for this node ('lab6')",
        default=USER_REFERENCE)
    parser.add_argument("-v","--verbose",help="Activate verbose",
        type=int,default=0)
    args = parser.parse_args()
    if args.emulate:
        from servers.arduino_emulator import ArduinoSerialEmulator
    slaveNodeInstance = SlaveNode(emulate=args.emulate,
                                  masterWSlocation=args.websocket,
                                  reference=args.reference,
                                  verbose=args.verbose)

    while True:
        try:
            print('\n---------------------------------\nStarting Slave node\n---------------------------------\n')
            tornado.ioloop.IOLoop.instance().run_sync(slaveNodeInstance.keepalive_ws)

        except SerialConnectionException as err:
            print(err.args)
            print('(node) Problem found in serial connection. Exiting')
        except ValueError as err:
            print(type(err))
            print(err.args)
        except TypeError as err:  #Error thrown when disconnecting the serial connection AND RECONNECTING!
            print('(node) Problem found in serial connection with arduino. Maybe the serial cable was disconnected.')
        except RuntimeError as err:
            if err.args[0]=='generator raised StopIteration':
                print('(node) Cannot find arduino connection')
            else:
                raise err
        except DisconnectedHostError:
            print('(node) Master server is disconnected.')
            slaveNodeInstance.is_master_connected = False
            time.sleep(10)
        except KeyboardInterrupt:
            tornado.ioloop.IOLoop.instance().stop()
            tornado.ioloop.IOLoop.instance().close()
            print('(node) Exiting gracefully')
            break

        time.sleep(2)
