"""
Software emulated response of the arduino.

For testing purposes.
"""
import os, pty, serial, time
from numpy import sin,pi



class ArduinoSerialEmulator(object):
    def __init__(self,baudrate= 9600, verbose=True):
        self.master, self.slave = pty.openpty()
        self.s_name = os.ttyname(self.slave)
        self.init_time = time.time()
        
        if verbose:
            print "tty open in {}".format(self.s_name)
        return self.s_name

    def loop(self):
        while True:
            try:
                signal = os.read(self.master,1)
                currTime = time.time()
                ch0 = self.myFunction(currTime,0)
                ch1 = self.myFunction(currTime,1)
                ch2 = self.myFunction(currTime,2)
                ch3 = self.myFunction(currTime,3)
                ch4 = self.myFunction(currTime,4)
                ch5 = self.myFunction(currTime,5)
                os.write(self.master,'{},{},{},{},{},{},{}\n'.format(currTime,ch0,ch1,ch2,ch3,ch4,ch5))
            except KeyboardInterrupt:
                return

    def myFunction(self, time, offset):
        return (sin((time-self.time+offset)*pi/5)+1)*2**11

    
    #def connect(self):
    #    self.ser = serial.Serial(self.s_name,baudrate, rtscts=True,dsrdtr=True)
        
    #def close_connection(self):
    #    self.ser.close()

    #def on_message(self, message):
    #    print message
    #def write( message):
    #    self.ser.write(message)
def main():
    pass

if __name__== "__main__":
    pass
## To Write to the device
#ser.write('Your text')#
#
## To read from the device
#a = os.read(master,1000)
#print a
