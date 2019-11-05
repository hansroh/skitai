import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
import aquests
from websocket import create_connection
import platform

IS_PYPY = platform.python_implementation() == 'PyPy'

def test_websocket (launch):
    with launch ("./examples/websocket.py") as engine:
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

        # test GROUPCHAT ---------------------------------- ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket/chat2?room_id=1")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result =="Client 2 has entered"
        result =  ws.recv()
        assert result == "Client 2 Said: Hello, World"

        ws2 = create_connection("ws://127.0.0.1:30371/websocket/chat2?room_id=1")
        ws2.send("Absolutely")
        result =  ws2.recv()
        assert result == "Client 3 Said: Absolutely"
        result =  ws.recv()
        assert result == "Client 3 Said: Absolutely"
        ws.close()
        ws2.close()


def test_websocket (launch):
     if IS_PYPY:
        # CANNOT FIND BUG, this work fine on local pypy:3 container
        return

    with launch ("./examples/websocket.py") as engine:
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

    with launch ("./examples/websocket.py") as engine:
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

def test_websocket_flask (launch):
    if IS_PYPY:
        # CANNOT FIND BUG, this work fine on local pypy:3 container
        return

    with launch ("./examples/websocket-flask.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/echo2")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result =="Welcome Client 0"
        result =  ws.recv()
        assert result == "1st: Hello, World"
        result =  ws.recv()
        assert result == "2nd: Hello, World"
        ws.close()
