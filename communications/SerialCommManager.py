"""
lab-nanny's slave server interface to the arduino



Author: David Paredes
19/05/2015
"""

import time
import serial
from serial.serialutil import SerialTimeoutException, SerialException
import numpy as np
from serial.tools.list_ports import grep as port_grep
from servers.server_master import TFORMAT
import logging

X0E = serial.to_bytes([0x0e])
NUM_CHANNELS = 9 # number of total channels (time axis + ADC channels 0-7)
DATA_LEN = 1 # numbers in each array that serial.print does in arduino

def handshake_func(serialinst,verbose=False,command='A'):
    """ Send/receive char to synchronize data gathering

    the function "handshake_func" sends a "command" to arduino using an
    instance of a serial connection.
    The commands, as recognized by the arduino_firmware_io, are single bytes
    with a value near 65 ('A'), which turns ON/OFF a digital channel.
    """
    if serialinst.isOpen():
        nbytes = serialinst.write(command.encode()) # can write anything here, just a single byte (any ASCII char)
        if verbose:
            print('(HSK) Wrote bytes to serial port: {}'.format(nbytes))
        #wait for byte to be received before returning
        st = time.clock()
        try:
            if (serialinst.inWaiting()>0):
                byte_back = serialinst.readline()
                et = time.clock()
                if verbose:
                    print('(HSK) Received handshake data from serial port: {}'.format(byte_back))
                    print('(HSK) Time between send and receive: {}s'.format(et-st))
                return byte_back
        except SerialTimeoutException:
            serialinst.close()
            raise ArduinoConnectionError


class SerialCommManager:
    """
    class for interfacing with lab-nanny

    The data logger runs on an Arduino DUE; the sketch is "arduino_firmware_io.ino"
    and should also be in the arduino_firmware directory

    """
    def __init__(self,recording_time=1,verbose=True,emulatedPort=[],arduino_port=[]):
        self.recording_time = recording_time
        self.verbose = verbose
        self.time_axis = None

        # Common connection_settings
        self.connection_settings={
                'baudrate':115200,
                'bytesize':serial.EIGHTBITS,
                'stopbits':serial.STOPBITS_ONE,
                'parity':serial.PARITY_NONE,
                'timeout':self.recording_time}
        if emulatedPort:
            port=emulatedPort
            self.connection_settings['rtscts'] = True
            self.connection_settings['dsrdtr'] = True
            self.connection_settings['port'] = port
        elif arduino_port:
            print('(SCM  {}) Given port: {}'\
                  .format(time.strftime(TFORMAT),
                          arduino_port))
            self.connection_settings['port']=arduino_port
        else:
            try:
                port = self.get_arduino_port()
            except StopIteration:
                print('Arduino not found')
                raise KeyboardInterrupt
            print('(SCM  {}) Trying port: {}'\
                  .format(time.strftime(TFORMAT),
                          port))
            self.connection_settings['port'] = port
        self.init_arduino_connection()

    def is_arduino_connected(self):
        return self.ser.isOpen()

    def init_arduino_connection(self):
        try:
            if self.verbose:
                print('(SCM  {}) Trying to connect to serial'\
                      .format(time.strftime(TFORMAT)))
            self.ser = serial.Serial(**self.connection_settings)
            # After opening the serial port, we wait for a bit until it's ready.
            # Otherwise, we might block the serial reading (for example, sleep(0.5)
            # blocks the MEGA)
            time.sleep(1.5)
            print('(SCM  {}) Connection Acquired'\
                    .format(time.strftime(TFORMAT)))

        except ValueError as err:
            raise ArduinoConnectionError
        except SerialException as err:
            pass

    def read_data_from_arduino(self):
        if self.ser.inWaiting():
            return self.ser.readline().decode()

    def get_arduino_port(self):
        """ Obtain the serial port being used by arduino using the "port_grep" function

        Note: if you have more than one arduino connected to the computer, it will only take the first one.

        :return:
        """
        myPort_generator = port_grep('arduino|genuino')
        try:

            firstPort = myPort_generator.next()  # .__next__() # for python3
        except AttributeError:
            firstPort = myPort_generator.__next__()
        print('(SCM  {}) Arduino found in port {}'\
              .format(time.strftime(TFORMAT),
                      firstPort[0]))
        return firstPort[0]


    def poll_arduino(self, handshake_func=handshake_func,**args):
        """
    	Initialise serial port and listen for data until timeout.

    	Convert the bytestream into numpy arrays for each channel

    	Returns:
    		(NUM_CHANNELS+1) numpy arrays (1D) representing time and ADC channels 0-5

	    """
        #TODO: Error situations. Especially those of the connection.
        #TODO: Check if connection_to_server needs to be done for every poll
        #TODO: Send/receive data in byte form?
        ## CONNECTION
        #self.connect_to_server()
        try:
            #ser = serial.Serial(**self.connection_settings)
            st = time.clock()
            byte_back = handshake_func(self.ser,verbose=self.verbose,**args)
            if self.verbose:
                print('(SCM) Byte back from handshake {}'.format(byte_back))
        #get data
            data = self.read_data_from_arduino()
            et = time.clock() - st
            if self.verbose:
                print('(SCM) ------------------------\n(SCM) INIT POLLING ARDUINO:\n(SCM)------------------------')
                print('(SCM) Time reading data (s): {0:.2e},  data: {1}'.format(et,repr(data)))
            #Fault conditions:
            # Empty data (just /r or /n)
            if (data is not None):
                data_list = data.split(',')
                #not prescribed number of channels
                # This might have the effect of reading erroneously (for example, if the
                # serial connection stops before reading the final values)
                # Need to check for data integrity at the node implementation.
                    ##PROCESS
                if len(data_list)>1:
                    #make string into list of strings, comma separated

                    # make list of strings into 1D numpy array of floats (ignore last point as it's an empty string)
                    data_array = np.array([float(i) for i in data_list[:-1]])

                    #print(data_array)
                    self.channels = data_array[1:]
                    self.time_axis = data_array[0]

                    if self.verbose:
                        print('(SCM) Data acquisition complete. Time spent {0:.2e}\n(SCM)------------------------'.format( time.clock() - st))

                    return self.time_axis, self.channels
                else:
                    return None
            else:
                return None

        except ValueError as err:    #If the cable gets disconnected
            self.ser.close()
            raise ArduinoConnectionError

        except TypeError as err:  #If disconnected it may not get a data point
            print(err.args)
            self.ser.close()
            raise ArduinoConnectionError
        except IndexError as err:
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.close()
            raise ArduinoConnectionError


            # Every so often, arduino will fail to read the values. Uncommenting the following "else" bit will count those
            # failures as a SerialException.
            #else:
            #    raise serial.SerialException


    def connect_to_server(self):
        """ Open a serial connection with the arduino.

        :return:
        """
        self.ser = serial.Serial(**self.connection_settings)
        #     port ='/dev/cu.usbmodemfa131',
        #     #port='COM6',   #look in the arduino software

    def cleanup(self):
        if self.verbose:
            print('(SCM) Cleaning up connection')
        self.ser.close()

class ArduinoConnectionError(Exception):
    pass


def main():
    try:
        fetcher = SerialCommManager(0.001, verbose=True)
        pinNumber = 'A'
        dataList = fetcher.poll_arduino(handshake_func=handshake_func,
                                        command=pinNumber)
        print(dataList)

        return True
    except Exception as err: #If the arduino is not connected
        print(err.args)
        print('(SCM  {}) Arduino not connected: please, connect the arduino and try running the node script again'\
                      .format(time.strftime(TFORMAT)))



if __name__ == '__main__':
    main()
