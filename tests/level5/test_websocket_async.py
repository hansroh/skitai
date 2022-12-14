import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
from websocket import create_connection
from websocket._exceptions import WebSocketBadStatusException
import platform

def test_websocket_async (launch, launch_dry):
    with launch ("./examples/websocket-atila.py") as engine:
        # test NOTHREAD ----------------------------------
        with pytest.raises (WebSocketBadStatusException):
            ws = create_connection("ws://127.0.0.1:30371/websocket/echo_async")

        ws = create_connection("ws://127.0.0.1:30371/websocket/echo_async?a=b")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.send("Hello, World")
        ws.send("Hello, World")

        result =  ws.recv()
        assert result == "echo: Hello, World"

        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.close()


        ws = create_connection("ws://127.0.0.1:30371/websocket/echo_async_iter?a=b")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.send("Hello, World")
        ws.send("Hello, World")

        result =  ws.recv()
        assert result == "echo: Hello, World"

        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.close()
