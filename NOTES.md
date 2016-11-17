## Notes for the server API:
- The request must be easy to code(something like “monitor1, ‘ch1’,’ch2’,’ch3’”, or maybe just the “monitor” part, and then each client selects the data
- There must be a way, in the server, to list the channels from the monitors (so that the requests from the clients can be compared to this list).
-The server needs to cope with connection loss (from any segment)
- Also, the server can save the data at intervals using mysql.

# Notes about synchronized node response synchronization
It should be relatively simple:
- create external queue to hold responses from nodes
- on_message(from node): append received message to an external queue
- (in periodic callback): send contents of the queue to all of the clients.

We may run into access locking conditions, thus we may need to implement semaphores or something similar.


## Some sources:
Connection: http://www.benjaminmbrown.com/2016/02/tutorial-how-to-build-real-time-data-visualization-with-d3-crossfilter-and-websockets-in-python-by-example/

Feedback: http://www.instructables.com/id/Raspberry-Web-server-sending-GET-data-to-Arduino-N/step2/Setting-up-a-RaspberryPi-as-a-WAP-web-server-and-j/

General "create graph" pattern: https://gist.github.com/benjchristensen/1148374

websocket: https://www.toptal.com/tornado/simple-python-websocket-server, http://www.html5rocks.com/en/tutorials/websockets/basics/

realtime python: http://mrjoes.github.io/2013/06/21/python-realtime.html
