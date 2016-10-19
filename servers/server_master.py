# Master server for lab-nanny
# 
# Collects data from the different nodes and makes it available to the clients through websockets.
# 
# The nodes might be unavailable at some times, so the server needs a way to "register" the different nodes,
# and to deal with the faulty situations.
#
# Also, we want to save the data to a database, probably a mysql server running in the same machine.
#

# class ServerMaster
#     Needs to keep connections "alive", or a way to check if connections are lost (to nodes)
#     It might keep a "representation" of the states of the nodes.
#     property: list of nodes
#               each of the nodes requires a list of properties they expose.
#     property: database
#     
#     method: communicate_with_node(send_command=[])
#     method: update_client(s)
#     method: setup_client   // which channels to show, which signals to make available
#     method: setup_node     // which channels are available (all?)
#     method: update_db
#     method: on_client_command   -> which command to which node

#Initially: In each "tick" we poll the different nodes and send data to the connected devices.
