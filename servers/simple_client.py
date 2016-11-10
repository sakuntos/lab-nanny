#!/usr/bin/python
EMULATE=True

import tornado
import tornado.websocket
from communications import SerialCommManager as SCM
from tornado import gen




LOCATION = "ws://localhost:8001/nodes_ws")

@gen.coroutine
def test_ws():
    client = yield tornado.websocket.websocket_connect("ws://localhost:8001/nodes_ws")
    client.write_message("Testing from client")
    msg = yield client.read_message()
    print("msg is %s" % msg)
    msg = yield client.read_message()
    print("msg is %s" % msg)
    msg = yield client.read_message()
    print("msg is %s" % msg)
    client.close()


if __name__ == "__main__":
    tornado.ioloop.IOLoop.instance().run_sync(test_ws)
