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
#     method: on_slave_connection: add slave node to list of nodes

#Initially: In each "tick" we poll the different nodes and send data to the connected devices.
#!/usr/bin/python

import datetime
import tornado.httpserver
import tornado.websocket
import tornado.ioloop as ioloop
import tornado.web
from tornado.concurrent import run_on_executor
import time

import socket

SLAVE_SOCKETPORT = 8001
SLAVE_SOCKETNAME = r'/nodes_ws'
PERIODICITY = 500

class SlaveNodeHandler(tornado.websocket.WebSocketHandler):
    slave_nodes = []

    def open(self):
        # We could do here the configuration of the node, like a dictionary with the channels exposed
        print 'new connection'
        #self.write_message("Initialising connection")
        print self.request.remote_ip
        SlaveNodeHandler.slave_nodes.append(self)
        print SlaveNodeHandler.slave_nodes

    def on_message(self, message): #From the Node
        print 'message received %s' % message

    def on_close(self):
        print 'connection closed'
        SlaveNodeHandler.slave_nodes.remove(self)

    @classmethod
    def broadcast_to_slave_nodes(cls):
        try:
            msg = "0,False"
            print "Writing message \"{}\" to {} clients. Time: {}".format(msg,len(cls.slave_nodes),time.time())
            for ii, client in enumerate(cls.slave_nodes):
                client.write_message(msg)
        except KeyboardInterrupt:
            raise

def periodicCall():
    print 'hello'

if __name__ == "__main__":
    application = tornado.web.Application([(SLAVE_SOCKETNAME, SlaveNodeHandler)])
    application.listen(SLAVE_SOCKETPORT)
    print 'Websocket established in {}:{}/{}'.format(socket.gethostbyname(socket.gethostname()),
                                                     SLAVE_SOCKETPORT, SLAVE_SOCKETNAME)   #socket.gethostbyname(socket.getfqdn())
    #http_server = tornado.httpserver.HTTPServer(application)
    #http_server.listen(SOCKETPORT)

    #callback= ioloop.PeriodicCallback(periodicCall,PERIODICITY)
    callback= ioloop.PeriodicCallback(SlaveNodeHandler.broadcast_to_slave_nodes,PERIODICITY)
    callback.start()
    print 'starting ioloop'
    ioloop.IOLoop.instance().start()
