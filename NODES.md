# lab-nanny nodes

Each of the nodes consists of a bunch of sensors connected to the arduino, plus a *slave* computer which communicates with both the arduino and the *master* server.

Since the slave nodes are directly connected to the arduinos, they show a much lower latency to their stimuli; one may use this to implement low-latency responses to contingencies. For example, if a TTL pulse signals that a potentially harmful condition is met, one might stop an experiment.

*NOTE*: Each node must have a unique identifier. This name is encoded in the 'user' names of the dictionaries used in the communications. Also, the names should contain alphanumeric characters, and must start with a letter (to avoid problems with the creation of tables in sqlite)

## Communications
The slave nodes communicate with arduino using a serial connection and connect with the master server through websockets. 

Each node server instance starts by setting up the connection to the arduino
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
   method
This message_bridging_arduino will then send this dictionary by writing into 
the master server's websocket. 

## Nodes must provide dictionaries with physical values
The nodes are in charge of adapting the values provided by arduino (typically
an integer between 0-(2^(number of ADC bits)-1) to a physical value relevant
to the experiment. 

For example, channel 0 might contain a voltage, which can
be computed using the formula  (ch0_bit_reading*ADC_MAXVOLT/ADC_MAXINT),
or channel 1 can be the reading of a temperature sensor, and we should output
the value in degrees celsius. 

See the SlaveNode.convert_data method for details

## Metadata
If the connection has just started, or has been dropped and the node is
re-connecting (in general, when the SlaveNode.metadata_registered flag is set
to False), the nodes will send a dictionary with the metadata. This dictionary
has the special key 'meta' (set in servers.server_master.METAKEYWORD), and its
contents will be saved in text form into the metadata table of the database.



To deploy:
----------

- Change the DICT_CONTENTS variable to state the actual contents of the
   channels.
- Run from the root folder using 'python -m servers.server_node', and using
   the required modifiers such as the lab references (lab6, lab7,...), the
   master websocket address, using emulation,...

# How to run
To run a slave node, run the following line on the root directory of lab-nanny.
~~~~
python -m servers.server_node -r lab7 
       -ws ws://[MASTERSERVERLOCATION]:[PORT]/nodes_ws
~~~~
