import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
from rs4.protocols import aquests

def assert_status (resp):
    rprint (resp.status_code)
    assert resp.content == (1, 'Welcome Client 0')

def assert_status2 (resp):
    rprint (resp.status_code)
    assert resp.content == (1, "1st: I'm a Websocket")

def assert_status3 (resp):
    rprint (resp.status_code)
    assert resp.content == (1, "2nd: I'm a Websocket")

def test_websocket (launch):
    with launch ("./examples/websocket.py") as engine:
        aquests.configure (1, callback = assert_status)
        websocket = "ws://127.0.0.1:30371"
        aquests.ws (websocket + "/websocket/echo", "I'm a Websocket", callback = assert_status)
        aquests.fetchall ()

def test_websocket_nonthread (launch):
    with launch ("./examples/websocket.py") as engine:
        aquests.configure (1, callback = assert_status)
        websocket = "ws://127.0.0.1:30371"
        aquests.ws (websocket + "/websocket/echo2", "I'm a Websocket", callback = assert_status)
        aquests.ws (websocket + "/websocket/echo2", "I'm a Websocket", callback = assert_status2)
        aquests.ws (websocket + "/websocket/echo2", "I'm a Websocket", callback = assert_status3)
        aquests.fetchall ()

def test_websocket_session (launch):
    with launch ("./examples/websocket.py") as engine:
        aquests.configure (1, callback = assert_status)
        websocket = "ws://127.0.0.1:30371"
        aquests.ws (websocket + "/websocket/echo4", "I'm a Websocket", callback = assert_status2)
        aquests.ws (websocket + "/websocket/echo4", "I'm a Websocket", callback = assert_status3)
        aquests.fetchall ()
