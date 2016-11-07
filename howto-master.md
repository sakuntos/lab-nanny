## For the master/slave architecture
In the master server:

%event handlers react to obtaining data
% they should work regardless of any clients connected to the master node (e.g. even if just to save data to the DB)

For ii in nodes:
    open_connection with node.
    attach event handlers 


%main loop
every tick:
    %this fires the events
    send request to all slave_nodes
    %after sending the requests, the slave nodes respond back
    update connected clients
   
    
    