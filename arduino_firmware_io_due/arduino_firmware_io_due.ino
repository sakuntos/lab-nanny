/*
lab-nanny Firmware

Controller of the arduino that sends data from the inputs and performs actions depending
on the messages received.

Analog input on the analog pins is read-in at a sampling rate of ~xyz kS/s
The sampling rate can be adjusted for more channels, or slower sampling rate, 
[channels must be enabled/disabled by setting the registers in the setup() method below],
by adjusting the sampling_time variable

PySerial is used to grab the data from the serial port and read it into python.

************
** NOTE: the USB connection to the Arduino must be to the NATIVE port, not the programming port!
************

Author: David Paredes
30/09/2015

Adapted from James Keaveney's https://github.com/jameskeaveney/LiveArduinoData

*/

// set up variables
const int buffer_length = 1; // length of data chunks sent at a time via SerialUSB

const int sampling_time_sleep = 50; // in micros
unsigned long init_time = 0;
int ledPin = 13;
int maxDIPin = 14;
int commandNumber =0;

String strTime = "";
String strOut = "";
String strC0 = "";
String strC1 = "";
String strC2 = "";
String strC3 = "";
String strC4 = "";
String strC5 = "";
String strC6 = "";
String strC7 = "";
String strC8 = "";
String strC9 = "";
String strC10 = "";
String strC11 = "";

/* To enable channels  (see page 1338 of datasheet) of the AX pins.
See 1320 of datasheet for conversion ADXX->PAXX
See also http://www.arduino.cc/en/Hacking/PinMappingSAM3X for the pin mapping 
between Arduino names and SAM3X pin names
*/
                  
const int A0_PIN  = 0b10000000;
const int A1_PIN  = 0b1000000;
const int A2_PIN  = 0b100000;
const int A3_PIN  = 0b10000;
const int A4_PIN  = 0b1000;
const int A5_PIN  = 0b100;
const int A6_PIN  = 0b10;
const int A7_PIN  = 0b1;
const int A8_PIN  = 0b10000000000;
const int A9_PIN  = 0b100000000000;
const int A10_PIN = 0b1000000000000;
const int A11_PIN = 0b10000000000000;

/* The PIN_MAP is a mask that specifices which analog channels to read. It can be
 * constructed as the sum of the different AX_PIN constants. */

const int PIN_MAP = A0_PIN+A1_PIN+A2_PIN+A3_PIN+A4_PIN+A5_PIN+A6_PIN+A7_PIN;

 // There might be a problem if we "activate" a lot of the channels but they are not connected: 
 // the "floating" signal wiggles when the rest of the lines are changed.
unsigned long current_time;

void setup() {
  
  // set ADC resolution
  analogReadResolution(12);
  
  // manually set registers for faster analog reading than the normal arduino methods
  ADC->ADC_MR |= 0xC0; // set free running mode (page 1333 of the Sam3X datasheet)
  ADC->ADC_CHER = PIN_MAP; 
  ADC->ADC_CHDR = 0xFFFF-PIN_MAP; // disable all other channels
  ADC->ADC_CR=2;        // begin ADC conversion
  
  
  // initialise serial port
  SerialUSB.begin(115200); // baud rate is ignored for USB - always at 12 Mb/s
  while (!SerialUSB); // wait for USB serial port to be connected - wait for pc program to open the serial port
  init_time =millis();
  pinMode(11, OUTPUT);
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);


}



void loop() {

  // data acquisition will start with a synchronisation step:
  // python should send a single byte of data, the arduino will send one back to sync timeouts
  int incoming = 0;
  if (SerialUSB.available() > 0) // polls whether anything is ready on the read buffer - nothing happens until there's something there
  {
    incoming = SerialUSB.read();
    // after data received, send the same back
    // if abs(incoming)<maxDIPin  (14 in this case)
    commandNumber = incoming-65;
    if (abs(commandNumber)<=maxDIPin){
      if (commandNumber>=0){
        digitalWrite(abs(commandNumber),HIGH);
            SerialUSB.println(abs(commandNumber));
      }   // Can be done faster toggling if PIND used
      else{
        digitalWrite(abs(commandNumber)-1,LOW); 
        SerialUSB.println(abs(commandNumber)-1);
      }
    }
    else{SerialUSB.println(incoming);
    }
    
    
    // measure start time - then acquire data for an amount of time set by the acquisition_time variable
    unsigned long start_micros = micros();
    unsigned long start_time = millis();
            
    /*  Generate and concatenate strings. 
     *  In principle, this loop can be improved by just sending the byte
     *  information of the different inputs */
    for (int jj = 0; jj < buffer_length; jj++)
    {
      
      // ADC acquisition
      
      // can put this in a small loop for some averaging if required - takes ~ 60 microsec per read/concatenate cycle
      while((ADC->ADC_ISR & 0x80)!=0x80); // wait for conversion to complete - see page 1345 of datasheet     
      // concatenate strings
      current_time = millis()-init_time;
      strTime.concat(current_time); // time axis
      strTime.concat(',');     
      strC0.concat(ADC->ADC_CDR[7]); // read data from the channel data register
      strC0.concat(',');
      strC1.concat(ADC->ADC_CDR[6]); // read data from the channel data register
      strC1.concat(',');
      strC2.concat(ADC->ADC_CDR[5]); // read data from the channel data register
      strC2.concat(',');
      strC3.concat(ADC->ADC_CDR[4]); // read data from the channel data register
      strC3.concat(',');
      strC4.concat(ADC->ADC_CDR[3]); // read data from the channel data register
      strC4.concat(',');
      strC5.concat(ADC->ADC_CDR[2]); // read data from the channel data register
      strC5.concat(',');
      strC6.concat(ADC->ADC_CDR[1]); // read data from the channel data register
      strC6.concat(',');
      strC7.concat(ADC->ADC_CDR[0]); // read data from the channel data register
      strC7.concat(',');
      
      //Serial.print(current_time);
      //Serial.print(",");
      
      delayMicroseconds(sampling_time_sleep); // limit sampling rate to something reasonable - a few kS/s
    }      
    // send data via SerialUSB
    // perform a flush first to wait for the previous buffer to be sent, before overwriting it
    SerialUSB.flush();
    strOut = strTime + strC0 + strC1 + strC2 + strC3 + strC4 + strC5 + strC6 + strC7; 
    SerialUSB.print(strOut); // doesn't wait for write to complete before moving on
    
    // clear string data - re-initialise
    strTime = "";
    strC0 = "";
    strC1 = "";
    strC2 = "";
    strC3 = "";
    strC4 = "";
    strC5 = "";
    strC6 = "";
    strC7 = "";
    strC8 = "";
    strC9 = "";
    // finally, print end-of-data and end-of-line character to signify no more data will be coming
    SerialUSB.println("\0");
    
  }
}
