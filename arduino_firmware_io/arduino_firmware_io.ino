/*
lab-nanny Firmware

Controller of the arduino DUE that sends data from the inputs and performs actions depending
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


//#define FASTADC 1

// defines for setting and clearing register bits
//#ifndef cbi
//#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
//#endif
//#ifndef sbi
//#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
//#endif


// set up variables
const int buffer_length = 1; // length of data chunks sent at a time via SerialUSB

const int sampling_time_sleep = 100; // in micros
unsigned long init_time = 0;

int ledPin = 13;
int maxDIPin = 14;
int commandNumber =0;
int current_time = 0;

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
String strC15 = "";


void setup() {
  Serial.begin(115200); // baud rate is ignored for USB - always at 12 Mb/s
  pinMode(13, OUTPUT);
  digitalWrite(13,HIGH);

//#if FASTADC
// // set prescale to 16
// sbi(ADCSRA,ADPS2) ;
// cbi(ADCSRA,ADPS1) ;
// cbi(ADCSRA,ADPS0) ;
//#endif

  // initialise serial port
  //while (!Serial); // wait for USB serial port to be connected - wait for pc program to open the serial port
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
  if (Serial.available() > 0) // polls whether anything is ready on the read buffer - nothing happens until there's something there
  {
    incoming = Serial.read();
    // after data received, send the same back
    // if abs(incoming)<maxDIPin  (14 in this case)
    commandNumber = incoming-65;
    if (abs(commandNumber)<=maxDIPin){
      if (commandNumber>=0){
        digitalWrite(abs(commandNumber),HIGH);
            Serial.println(abs(commandNumber));
      }   // Can be done faster toggling if PIND used
      else{
        digitalWrite(abs(commandNumber)-1,LOW); 
        Serial.println(abs(commandNumber)-1);
      }
    }
    else{Serial.println(incoming);
    }
    
    
    // measure start time - then acquire data for an amount of time set by the acquisition_time variable
    unsigned long start_micros = micros();
    unsigned long start_time = millis();
            
    /*  Generate and concatenate strings. 
     *  In principle, this loop can be improved by just sending the byte
     *  information of the different inputs */
    for (int jj = 0; jj < buffer_length; jj++)
    {
      
        
      // concatenate strings
      current_time = millis()-init_time;
      strTime.concat(current_time); // time axis
      strTime.concat(',');     
      strC0.concat(analogRead(0)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(1)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(2)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(3)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(4)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(5)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(6)); // read data from the channel data register
      strC0.concat(',');
      strC0.concat(analogRead(7)); // read data from the channel data register
      strC0.concat(',');
      
      //Serial.print(current_time);
      //Serial.print(",");
      
      //delayMicroseconds(sampling_time_sleep); // limit sampling rate to something reasonable - a few kS/s
    }      
    // send data via SerialUSB
    // perform a flush first to wait for the previous buffer to be sent, before overwriting it
    Serial.flush();
    strOut = strTime + strC0 ; 
    Serial.print(strOut); // doesn't wait for write to complete before moving on
    
    // clear string data - re-initialise
    strTime = "";
    strC0 = "";
    // finally, print end-of-data and end-of-line character to signify no more data will be coming
    Serial.println("\0");
    
  }
}
