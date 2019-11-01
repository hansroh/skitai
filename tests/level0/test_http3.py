import pytest
import os
import socket
import time
from aquests.protocols.http3 import requests

@pytest.mark.skip
def test_http3 (launch):
    serve = '/home/ubuntu/skitai/tests/examples/http3.py'
    with launch (serve, port = 30443) as engine:
        resp = engine.get ("/")

def test_get_http3 (launch):
    serve = '/home/ubuntu/aioquic/examples/http3_server.py'
    if os.path.isfile (serve):
        with launch (serve, port = 4433) as engine:
            r = requests.get ('https://localhost:4433/')
            assert ":status" in r.headers

@pytest.mark.skip
def test_udp ():
    raddr = ('localhost', 30443)
    sock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect (raddr)
    for i in range (3):
        sent = sock.send (b'hello' + str (i).encode ())
        print ('sent', sent)
        print ('recv...')
        ret = sock.recvfrom (65536)
        print ('ret', ret)

    sent = sock.send (b'\r\n\r\n')
    print ('sent', sent)
    print ('recv...')
    ret = sock.recvfrom (65536)
    print ('ret', ret)

    sock.close ()


