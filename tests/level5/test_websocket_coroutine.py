import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
import aquests
from websocket import create_connection
import platform

def test_websocket_coroutine (launch):
    with launch ("./examples/websocket.py") as engine:
        # test NOTHREAD ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket/echo_coroutine")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.send("Hello, World")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"
        result =  ws.recv()
        assert result == "echo: Hello, World"
        result =  ws.recv()
        assert result == "double echo: Hello, World"
        ws.close()


        ws = create_connection("ws://127.0.0.1:30371/websocket/echo_coroutine2")
        ws.send("Hello, World")
        result =  ws.recv()
        assert "<title>Example Domain</title>" in result

        ws.send("Hello, World")
        result =  ws.recv()
        assert "<title>Example Domain</title>" in result

        ws.close()


