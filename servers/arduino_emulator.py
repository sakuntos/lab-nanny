"""
Software emulated response of the arduino.

For testing purposes.
"""
import os
import pty
import serial
import time
from numpy import sin,pi
import threading

NUM_CHANNELS=9 #Number of analog readings + 1

class ArduinoSerialEmulator(threading.Thread):
    def __init__(self,baudrate= 115200, verbose=True):   #9600 baudrate
        threading.Thread.__init__(self)
        self.master, self.slave = pty.openpty()
        self.baudrate = 115200
        self.s_name = os.ttyname(self.slave)
        self.init_time = time.time()
        self.keepRuning = True
        self.channels_value=[]
        
        if verbose:
            print("\nTTY open in {}".format(self.s_name))

    def report_server(self):
        return self.s_name

    def run(self):
        print('Entering arduino emulation loop')
        self.keepRunning = True

        #This loop continualy looks for a command from the node computer and writes a series of values in response.
        # However, if we close (using KeyboardInterrupt a couple of times) the process while the emulator is waiting for
        # serial (the os.read() call) it will hang indefinitely. If done correctly, a single interrupt might just work.
        # TODO: fix the hanging problems with the os.read() call after a KeyboardInterrupt
        try:
            while self.keepRunning:
                # This part just reads a single char from the port and echoes it
                signal = os.read(self.master,1)
                os.write(self.master,signal+'\n')
                
                currTime = time.time()
                self.channels_value =['{},'.format(self.myFunction(currTime, offset))
                                      for offset in range(NUM_CHANNELS-1)]
                channelsString = "".join(self.channels_value)
                fullString = '{},'.format(currTime)+channelsString+'\n'
                os.write(self.master,fullString)
        except KeyboardInterrupt:
            self.join()
        print('Exiting emulation loop')
            
    def myFunction(self, time, offset):
        return int((sin((time-self.init_time+offset)*pi/5)+1)*2**11)
    
    def close(self):
        self.keepRunning=False
        self.join()


def main():
    pass

if __name__== "__main__":
    my_emulator = ArduinoSerialEmulator()
    emulation_port = my_emulator.report_server()
    my_emulator.start()
    print('Starting emulation for port {}'.format(emulation_port))

    from communications import SerialCommManager as SCM

    comm_mgr = SCM.SerialCommManager(0.01,emulatedPort = emulation_port)
    try:
        while True:
            comm_mgr.poll_arduino()
            time.sleep(1)
    except KeyboardInterrupt:
        my_emulator.keepRunning=False
        my_emulator.join(0.1)
        comm_mgr.poll_arduino()
