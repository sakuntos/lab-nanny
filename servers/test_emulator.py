import arduino_emulator
import serial
import time

my_emulator = arduino_emulator.ArduinoSerialEmulator()
emulation_port = my_emulator.report_server()
my_emulator.start()
print 'Starting emulation for port {}'.format(emulation_port)

try:
    ser = serial.Serial(emulation_port,baudrate=115200,
                    rtscts=True,dsrdtr=True)
    print 'Connection established with port {}\n------------------\n'.format(emulation_port)
except serial.SerialException:
    print 'Could not open connection in {}'.format(emulation_port)
    raise
  
try:
    while True:
        ser.write('a')
        print ser.readline()
        print ser.readline()
        time.sleep(1)
except KeyboardInterrupt:
    #This is a hack: to avoid hanging-up the process while reading the serial, one needs to send a "final" character
    #TODO: a graceful end for the emulator
    my_emulator.keepRunning=False
    my_emulator.join(0.1)
    ser.write('a')
    ser.close()
print 'Server closed'
