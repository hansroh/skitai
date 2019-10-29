from unittest.mock import MagicMock
import socket
from ..backbone.http_server import http_channel
from . import server

def Conn ():
    class Socket (MagicMock):
        def __init__ (self, *args, **karg):
            MagicMock.__init__ (self, *args, **karg)
            self.__buffer = []

        def send (self, data):
            self.__buffer.append (data)
            return len (data)

        def getvalue (self):
            return b"".join (self.__buffer)

    sock = Socket (name="socket", spec=socket.socket)
    sock.fileno.return_value = 1
    return sock


def Channel ():
    c = http_channel (server.Server (), Conn (), ('127.0.0.100', 65535))
    c.connected = True
    return c
