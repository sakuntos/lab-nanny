#To Do:

Currently, a single node (`servers/server_node.py`) is written, which just serves the data from the connected arduino.

- Write the master/slave architecture

A simulated arduino(`servers\dummy_arduino_nix.py`) is half-written that creates a pair of virtual ports to write/read 
its data. 
- Finish the simulated arduino for testing.
- Port the code to be compatible with Windows machines (probably using com0com)

