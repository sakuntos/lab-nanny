"""
lab-nanny's slave server interface to the arduino

It can perform two types of handshake:
- Standard: just collect data
- Write: it sends a "command" back to arduino. In the simple case of the arduino_firmware_io, it is a byte with a value
 near 65 ('A'), which turns ON/OFF a digital channel.

Author: David Paredes
19/05/2015
"""

import time
import serial
import numpy as np
from serial.tools.list_ports import grep as port_grep
import logging
NUM_CHANNELS = 9 # number of total channels (time axis + ADC channels 0-7)
DATA_LEN = 1 # numbers in each array that serial.print does in arduino

def standard_handshake(serialinst,verbose=False):
    """ Send/receive char to synchronize data gathering """
    nbytes = serialinst.write("z") # can write anything here, just a single byte (any ASCII char)
    if verbose:
        print('(std) Wrote bytes to serial port: ', nbytes)
    #wait for byte to be received before returning
    st = time.clock()
    byte_back = serialinst.readline()
    et = time.clock()
    if verbose:
        print('(std) Received handshake data from serial port: {}'.format(byte_back))
        print('(std) Time between send and receive: {}s'.format(et-st))

def write_handshake(serialinst,verbose=False,command='A'):
    """ Send/receive pair of bytes to synchronize data gathering """
    nbytes = serialinst.write(command.encode()) # can write anything here, just a single byte (any ASCII char)
    if verbose:
        print('(handshake) Wrote bytes to serial port:{} '.format(nbytes))
    #wait for byte to be received before returning
    st = time.clock()
    byte_back = serialinst.readline()
    et = time.clock()
    if verbose:
        print('(handshake) Received handshake data from serial port: {}'.format(byte_back))
        print('(handshake) Time between send and receive: {}s'.format(et-st))


class SerialCommManager:
    """
    class for interfacing with lab-nanny

    The data logger runs on an Arduino DUE; the sketch is "arduino_firmware_io.ino"
    and should also be in the arduino_firmware directory

    """
    def __init__(self,recording_time=1.,verbose=True,emulatedPort=[]):
        self.recording_time = recording_time
        self.verbose = verbose
        self.time_axis = None
        # Obtain the id of the first port to use "arduino" as ID.
        if emulatedPort:
            port=emulatedPort
            self.connection_settings={
                'port':port,
                'baudrate':115200,
                'rtscts':True,
                'dsrdtr':True,
                'bytesize':serial.EIGHTBITS,
                'stopbits':serial.STOPBITS_ONE,
                'parity':serial.PARITY_NONE,
                'timeout':self.recording_time}

        else:
            port = self.get_arduino_port()
            print('Trying port: {}'.format(port))
            self.connection_settings= {
                'port':port,
                'baudrate':115200,
                'parity':serial.PARITY_NONE,
                'stopbits':serial.STOPBITS_ONE,
                'bytesize':serial.EIGHTBITS,
                'timeout':self.recording_time}

    def get_arduino_port(self):
        myPort_generator = port_grep('arduino')
        try:
            firstPort = myPort_generator.next()  # .__next__() # for python3
        except AttributeError:
            firstPort = myPort_generator.__next__()
        return firstPort[0]

    def poll_arduino(self, handshake_func=standard_handshake,**args):
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

        with serial.Serial(**self.connection_settings) as ser:
            st = time.clock()
            handshake_func(ser,verbose=self.verbose,**args)
        #get data
            data = ser.readline()

        if data is not []:
            ##PROCESS
            et = time.clock() - st
            if self.verbose:
                print('------------------------\n INIT POLLING ARDUINO:\n------------------------')
                print('Time reading data (s): {0:.2e},  data: {1}'.format(et,data))

            #make string into list of strings, comma separated
            data_list = data.split(b',')

            # make list of strings into 1D numpy array of floats (ignore last point as it's an empty string)
            data_array = np.array([float(i) for i in data_list[:-1]])

            #if self.verbose:
            print('Length of array: {}'.format(len(data_array)))
            data_array_3d = data_array.reshape(NUM_CHANNELS,DATA_LEN)

            if DATA_LEN>0:
                self.time_axis = data_array_3d[0]
                self.channels = [data_array_3d[ii+1] for ii in range(NUM_CHANNELS - 1)]
            if self.verbose:
                print('Data acquisition complete. Time spent {0:.2e}\n------------------------'.format( time.clock() - st))

            return self.time_axis, [channel for channel in self.channels]
        else:
            raise serial.SerialException



    def connect_to_server(self):
        """ Open a serial connection with the arduino.

        :return:
        """
        self.ser = serial.Serial(**self.connection_settings)
        #     port ='/dev/cu.usbmodemfa131',
        #     #port='COM6',   #look in the arduino software


    def cleanup(self):
        self.ser.close()




def main():
    fetcher = SerialCommManager(0.01, verbose=False)
    pinNumber = chr(14)
    dataList = fetcher.poll_arduino(handshake_func=write_handshake,
                                       command=pinNumber)

    pass



if __name__ == '__main__':
    main()
