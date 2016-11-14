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

import uuid
import socket
import json

SLAVE_SOCKETPORT = 8001
SLAVE_SOCKETNAME = r'/nodes_ws'
CLIENT_SOCKETPORT = 8008
CLIENT_SOCKETNAME = r'/client_ws'

PERIODICITY = 500

class SlaveNodeHandler(tornado.websocket.WebSocketHandler):
    slave_nodes = []

    def initialize(self, comms_handler):
        """
        :param comms_handler:
        :type comms_handler: CommsHandler
        :return:
        """
        """Store a reference to the communications handler"""
        self.__comms_handler = comms_handler

    def open(self):
        # We could do here the configuration of the node, like a dictionary with the channels exposed

        #self.write_message('Init')

        SlaveNodeHandler.slave_nodes.append(self)
        self.id = uuid.uuid4()
        print 'new connection from {}. Total of slave nodes: {}'.format(self.request.remote_ip, len(SlaveNodeHandler.slave_nodes))
        print 'UUID: {}'.format(self.id)



    def on_message(self, message): #From the Node

        message_dict = json.loads(message)
        if message_dict['error']==False:
            print 'time: {0:.3f}, user: {1}, error: {2}, ch0: {3}'.format(message_dict["x"],
                                                                  message_dict["user"],
                                                                  message_dict["error"],
                                                                  message_dict["ch0"])
        else:
            print 'time: {0:.3f}, user: {1}, error: {2}'.format(message_dict["x"],
                                                                  message_dict["user"],
                                                                  message_dict["error"])

        # If we do this, we send a message to the clients for each reading. Maybe it will be slow
        for client in self.__comms_handler.clients:
            client.write_message(message)

    def on_close(self):
        print 'connection closed'
        SlaveNodeHandler.slave_nodes.remove(self)

    def check_origin(self, origin):
        #TODO: change this to actually check the origin
        return True

    @classmethod
    def broadcast_to_slave_nodes(cls):
        try:
            msg = 'X,50,0'  #Write a command that causes "no harm", i.e. we don't actually use. The 'X' ensures that all nodes reply

            #We write to all the clients, but only the right user will actually generate output
            # TODO: should only send data to the right connection, instead of relying on the nodes to check whether the message is for them?
            for ii, client in enumerate(cls.slave_nodes):
                client.write_message(msg)
        except KeyboardInterrupt:
            raise


class ClientHandler(tornado.websocket.WebSocketHandler):
    client_list = []

    def initialize(self, comms_handler):
        """
        :param comms_handler:
        :type comms_handler: CommsHandler
        :return:
        """
        """Store a reference to the communications handler"""
        self.__comms_handler = comms_handler

    def open(self):
        # We could do here the configuration of the node, like a dictionary with the channels exposed
        ClientHandler.client_list.append(self)
        print 'new connection from {}. Total of slave nodes: {}'.format(self.request.remote_ip, len(ClientHandler.client_list))

    def on_message(self, message): #From the Node
        print 'message received from client: %s' % message
        for node in self.__comms_handler.server_nodes:
            node.write_message(message)


    def on_close(self):
        print 'connection closed'
        ClientHandler.client_list.remove(self)

    def check_origin(self, origin):
        return True


class CommsHandler(object):
    def __init__(self):
        self.server_nodes =SlaveNodeHandler.slave_nodes
        self.clients=ClientHandler.client_list

    def broadcast_to_slaves(self):
        SlaveNodeHandler.broadcast_to_slave_nodes()


if __name__ == "__main__":
    comms_handler = CommsHandler()
    application = tornado.web.Application([(SLAVE_SOCKETNAME, SlaveNodeHandler,{'comms_handler':comms_handler}),
                                           (CLIENT_SOCKETNAME, ClientHandler,{'comms_handler':comms_handler})])
    application.listen(SLAVE_SOCKETPORT)

    print('Two connections created:')
    print('-Client WS EST @ {}:{}{},  ({})'.format(socket.getfqdn(),
                                                     CLIENT_SOCKETPORT, CLIENT_SOCKETNAME,socket.gethostbyname(socket.gethostname())))
    print('-Nodes WS EST  @ {}:{}{},  ({})'.format(socket.getfqdn(),
                                                     SLAVE_SOCKETPORT, SLAVE_SOCKETNAME,socket.gethostbyname(socket.gethostname())))

    callback= ioloop.PeriodicCallback(comms_handler.broadcast_to_slaves,PERIODICITY)
    callback.start()
    print 'starting ioloop'
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        ioloop.IOLoop.instance().stop()
        print 'Exiting gracefully...'

