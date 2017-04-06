"""Master server for lab-nanny

Collects data from the different nodes and makes it available to the
clients using websockets.

The functionality of the master server is to join the data from the
different nodes and make it available in two forms:
-- clients using websockets
-- store it in a database

To do this, the master uses the Masterserver.tick method, which
-- submits updates to the clients
-- sends requests for data to the nodes
(in this order)
By centralizing the communications (that is, nodes send updates to
MasterServer, which then sends them to the clients), we reduce the
amount of connections required from (#clients * #nodes) to
(#clients + #nodes)

The master server handles the connections both with the inside (nodes)
and the outside (clients) using two classes: NodeHandler and
ClientHandler, which are classes derived from the
tornado.websocket.WebSocketHandler class.

The server uses an auxilitary communications handler class (CommsHandler)
which keeps a list of nodes and clients, and the last data from the nodes.

"""
# Master server for lab-nanny
#
# Collects data from the different nodes and makes it available to the clients through websockets.

#!/usr/bin/python

#TODO: have a way to "disconnect" the nodes when they do disconnect.
import tornado.httpserver
import tornado.websocket
import tornado.ioloop as ioloop
import tornado.web
from tornado.websocket import WebSocketClosedError
import signal

import argparse
import time
from database.DBHandler import DBHandler as DBHandler

import uuid
import socket
import json

SLAVE_SOCKETPORT  = 8001
SLAVE_SOCKETNAME  = r'/nodes_ws'
CLIENT_SOCKETPORT = 8008
CLIENT_SOCKETNAME = r'/client_ws'

DEFAULTMESSAGE    = 'X,50,0'
DEFAULTDBNAME     = 'example.db'
PERIODICITY       = 100
DB_PERIODICITY    = 30000   #Save data to db every...

TFORMAT = '%y/%m/%d %H:%M:%S'

class MasterServer(object):
    """ Class that runs the Master Server for lab-nanny.

    It keeps a NodeHandler and a ClientHandler object to communicate with
    the slave nodes and the clients, which in turn use an instance of the
    CommsHandler class to do internal communications.

    Periodically (every fraction of a second), the Master server polls the
    nodes for data, and sends the results to the clients.
    Additionally, with a different periodicity (~10s) the Master server
    saves a copy of the data to a database.

    """
    def __init__(self, slave_socketname = SLAVE_SOCKETNAME,
                 socket_port=SLAVE_SOCKETPORT,
                 client_socketport=CLIENT_SOCKETPORT,
                 client_socketname=CLIENT_SOCKETNAME,
                 periodicity=PERIODICITY,
                 db_periodicity = DB_PERIODICITY,
                 verbose = True):
         #Init parameters
        self.socket_port             = socket_port
        self.slave_socketname        = slave_socketname
        self.client_socketname       = client_socketname
        self.client_socketport       = client_socketport
        self.callback_periodicity    = periodicity
        self.db_callback_periodicity = db_periodicity
        self.verbose                 = verbose
        self.callback                = []
        self.dbcallback              = []
        self.HTTPserver              = []

        # Create instance of the CommsHandler to mediate communications between
        # node and client handlers
        self.comms_handler = CommsHandler()
        # Also, start communication with the database
        self.db_handler = DBHandler(db_name=DEFAULTDBNAME)
        # Init program
        self.run()

    def run(self):
        """ Main function of the MasterServer class.

        It creates a tornado web application with two websocket handlers: one
        for the nodes, and one for the clients, listening on the same port
        (self.socket_port), but using different names.

        Then, it initialises two periodic callbacks:
        - One that manages the node/client communications, typically with a
        sub-second periodicity
        - Another one to store long-term traces of the data to a database
        (every ~10s)
        """
        self.application = tornado.web.Application([(self.slave_socketname,
                                                     NodeHandler,
                                                     {'comms_handler':self.comms_handler,
                                                      'verbose':self.verbose}),
                                                     (self.client_socketname,
                                                     ClientHandler,
                                                     {'comms_handler':self.comms_handler,
                                                      'verbose':self.verbose})])
        try:
            self.HTTPserver = self.application.listen(self.socket_port)
            print('Two connections created:')
            fqdn = socket.getfqdn()
            alias = socket.gethostbyname(socket.gethostname())
            print('-Client WS EST @ {}:{}{},  ({})'.format(fqdn,
                                                           self.client_socketport,
                                                           self.client_socketname,
                                                           alias))
            print('-Nodes WS EST  @ {}:{}{},  ({})'.format(fqdn,
                                                           self.socket_port,
                                                           self.slave_socketname,
                                                           alias))
        except socket.error as error:
            #Catch the error if the connections are already present:
            if error.errno == 10048:
                pass
            else:
                raise

        self.callback= ioloop.PeriodicCallback(self.tick,
                                               self.callback_periodicity)
        self.callback.start()
        print('Starting ioloop')


        # To save to DB:
        self.dbcallback= ioloop.PeriodicCallback(self.db_tick,
                                                 self.db_callback_periodicity)
        self.dbcallback.start()

        try:
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('Exiting gracefully... @{}'.format(time.strftime(TFORMAT)))
        finally:
            self.on_close()


    def tick(self):
        """ Function called periodically to manage node/client communication

        - First, the function sends the last data (obtained from the nodes)
        to the clients
        -  Then, it requests more data to the nodes.

        By first sending the data, and then asking for more, we make sure the
        nodes have time to send the data back to the MasterServer before
        sending that data to the clients; this comes at the expense of sending
        "old data" (with a repetition period), which has no impact unless the
        application is time-critical.
        """
        # TODO: should only send data to the right client connection, instead of relying on the nodes to check whether the message is for them?

        try:
            # If the NodeHandler decides to write messages to the clients upon reception of each message, comment this
            # line
            broadcast(self.comms_handler.clients,self.comms_handler.last_data)
            msg = DEFAULTMESSAGE  #Write a command with no side consequences. The 'X' ensures that all nodes reply
            broadcast(self.comms_handler.nodes,msg)

        except WebSocketClosedError:
            print('Websocket closed')
        #In case we want to exit, we send a KeyboardInterrupt
        except KeyboardInterrupt:
            raise

    def db_tick(self):
        """ Function called periodically to save data to the database

        This function generates an entry in the database for each node ID
        held in the CommsHandler.last_data instance. The entry in the
        database is composed of a timestamp, a username, and the JSON string.
        """
        # Write values to db (called every N seconds, probably 30-60)
        # if self.verbose:
        num_connected_devices = len(self.comms_handler.last_data)
        if num_connected_devices>0:
            print('(MASTER) Adding {} entries to DB @{}'\
                  .format(num_connected_devices,time.strftime(TFORMAT)))

        for id in self.comms_handler.last_data:
            datadict = self.comms_handler.last_data[id]
            # Add data to observations table
            # Check if table with name "id" exists
            # Add data to specific table for ID
            self.db_handler.add_database_entry(datadict)
        self.db_handler.commit()


    def on_close(self):
        self.db_handler.close()




class NodeHandler(tornado.websocket.WebSocketHandler):
    """ Class that handles the communication via websockets with the slave nodes.
    """

    node_list = []

    def initialize(self, comms_handler,verbose=True):
        """Initialisation of an object of the NodeHandler class.

        We provide a communications handler object which keeps a list of the nodes
        and clients, and a list of the last messages from the nodes.

        :param comms_handler:
        :type comms_handler: CommsHandler
        :param verbose: True for verbose output
        :return:
        """

        self.__comms_handler = comms_handler
        self.verbose = verbose

    def open(self):
        """ Callback executed upon opening a new slave node connection.

        This function adds the new connection to the class "nodes" list and
        provides a unique id to the connection using the uuid.uuid4().hex
        function.

        :return:
        """
        # We could do here the configuration of the node, like a dictionary with the channels exposed

        #self.write_message('Init')

        NodeHandler.node_list.append(self)
        self.id = uuid.uuid4().hex
        print('(NDH) New NODE {}. (out of {}) @ {}'\
              .format(self.request.remote_ip,
                      len(NodeHandler.node_list),
                      time.strftime(TFORMAT)))
        print('(NDH) UUID: {}'.format(self.id))

    def on_message(self, message):
        """ Callback executed upon message reception from the node.

        The message is a JSON string, which is converted to a dictionary.

        :param message:
        :return:
        """
        message_dict = json.loads(message)
        if self.verbose:
            if not message_dict['error']:
                print('(NDH) time: {0:.3f}, user: {1}, error: {2}, ch0: {3}'\
                      .format(message_dict["x"],
                              message_dict["user"],
                              message_dict["error"],
                              message_dict["ch0"]))
            else:
                print('(NDH) time: {0:.3f}, user: {1}, error: {2}'\
                      .format(message_dict["x"],
                              message_dict["user"],
                              message_dict["error"]))

        #There are two ways in which we can pass the data to the clients:
        # - Store the data in the self.__comms_handler.last_data dictionary
        # - Send the data to the clients everytime a message is received
        # The first one helps with synchronizing sending the data to the clients.
        # The second one is more immediate, but it might impact the performance of the network,
        # since we communicate with each of the clients on every message received.

        # To use the first method, uncomment this line, and make sure that the "tick()" function
        # in the master server uses :
        self.__comms_handler.last_data[self.id] = message_dict

        # To use the second method, uncomment this other line
        #for client in self.__comms_handler.clients:
        #    client.write_message(message)


    def on_close(self):
        print('(NDH) Connection with {} closed @{}'.format(self.id,
                                                           time.strftime(TFORMAT)))
        self.__comms_handler.remove_key(self.id)
        NodeHandler.node_list.remove(self)

    def check_origin(self, origin):
        #TODO: change this to actually check the origin
        return True

    @classmethod
    def broadcast_to_nodes(cls,msg=DEFAULTMESSAGE):
        """ Function to send a message to all the nodes held in the self.__comms_handler nodes list.

        :param msg: message to broadcast
        :return:
        """
        #In case we want to exit, we send a KeyboardInterrupt
        try:
            broadcast(cls.node_list,msg)
        except KeyboardInterrupt:
            raise


class ClientHandler(tornado.websocket.WebSocketHandler):
    """ Class that handles the communication via websockets with the
    slave nodes.
    """
    client_list = []

    def initialize(self, comms_handler,verbose=False):
        """ Initialisation of an object of the ClientHandler class.

        We provide a communications handler object which keeps a list of the
        nodes and clients, and a list of the last messages from the nodes.

        :param comms_handler:
        :type comms_handler: CommsHandler
        :param verbose: True for verbose output
        :return:
        """
        self.__comms_handler = comms_handler
        self.verbose = verbose

    def open(self):
        """ Callback executed upon opening a new client connection.

        This function adds the new connection to the class "client" list.

        :return:
        """
        # We could do here the configuration of the node, like a dictionary with the channels exposed
        ClientHandler.client_list.append(self)
        print('(CLH) New connection from {}. Total of slave nodes: {} @ {}'\
              .format(self.request.remote_ip,
                      len(ClientHandler.client_list),
                      time.strftime(TFORMAT)))

    def on_message(self, message):
        """ Callback executed upon message reception from the client.

        The message is a JSON string, which is then broadcasted to all the
        nodes sequentially.

        :param message:
        :return:
        """
        if self.verbose:
            print('(CLH) Message received from client: {} @ {}'\
                  .format(message,
                          time.strftime(TFORMAT)))
        for node in self.__comms_handler.nodes:
            node.write_message(message)


    def on_close(self):
        print('(CLH) Connection closed')
        ClientHandler.client_list.remove(self)
        print(ClientHandler.client_list)

    def check_origin(self, origin):
        #TODO: should actually check the origin
        return True



class CommsHandler(object):
    """ Class that keeps references of the nodes and the clients for
    communication purposes

    It also keeps a dictionary with a reference to the last data sent
    from each of the nodes.
    """
    def __init__(self):
        self.nodes = NodeHandler.node_list
        self.clients = ClientHandler.client_list
        self.last_data = {}

    def remove_key(self,id):
        self.last_data.pop(id,None)

def broadcast(list_of_endpoints, msg):
    """ Broadcasts a message to a list of endpoints using the "write_message"
    method.

    :param list_of_endpoints:
    :param msg:
    :return:
    """
    for endpoint in list_of_endpoints:
        endpoint.write_message(msg)



def main1(periodicity=100, verbose=0):
    my_master_server = MasterServer(periodicity=periodicity,
                                    verbose=verbose)
    return my_master_server


def signal_handler(signum,frame):
    tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-pr","--periodicity",help="address of the master server websocket",
                        type=int,default=100)
    parser.add_argument("-v","--verbose",help="Activate verbose",
                        type=int,default=0)
    args = parser.parse_args()

    signal.signal(signal.SIGINT,signal_handler)
    main1(periodicity=args.periodicity,
          verbose=args.verbose)
