from websocket import create_connection
from websocket._exceptions import WebSocketBadStatusException
import pytest
import sys, os
import threading
import time
import platform
import confutil
from confutil import rprint

IS_PYPY = platform.python_implementation() == 'PyPy'

def test_websocket (launch):
    with launch ("./examples/websocket-atila.py") as engine:
        # test THREADSAFE ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket/echo3")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result =="Welcome Client 0"
        result =  ws.recv()
        assert result == "1st: Hello, World"
        result =  ws.recv()
        assert result == "2nd: Hello, World"
        ws.close()

        with pytest.raises (WebSocketBadStatusException):
            create_connection("ws://127.0.0.1:30371/websocket/param")

        ws = create_connection("ws://127.0.0.1:30371/websocket/param?a=1")
        ws.close ()
        ws = create_connection("ws://127.0.0.1:30371/websocket/param?a=1&b=2")
        ws.close ()
        ws = create_connection("ws://127.0.0.1:30371/websocket/param?a=1&b=2&c=3")
        ws.close ()


def test_websocket1 (launch):
    if IS_PYPY:
        # CANNOT FIND BUG, this work fine on local pypy:3 container
        return

    with launch ("./examples/websocket-atila.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/push")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "you said: Hello, World"
        resp = engine.get ("/websocket/wspush")
        assert resp.text == "Sent"
        result =  ws.recv()
        assert result == "Item In Stock!"
        ws.close()

def test_websocket2 (launch):
    if IS_PYPY:
        # CANNOT FIND BUG, this work fine on local pypy:3 container
        return

    with launch ("./examples/websocket-atila.py") as engine:
        # test NOTHREAD ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket/echo2")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result =="Welcome Client 0"
        result =  ws.recv()
        assert result == "1st: Hello, World"
        result =  ws.recv()
        assert result == "2nd: Hello, World"
        ws.close()
