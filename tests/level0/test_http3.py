import pytest
import os
import socket
import time

@pytest.mark.skip
def test_http3 (launch):
    serve = '../examples/http3.py'
    with launch (serve) as engine:
        resp = engine.get ("/")

def test_udp ():
    raddr = ('localhost', 30443)
    sock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
    print (dir (sock))
    sock.connect (raddr)
    for i in range (3):
        sent = sock.send (b'hello')
        print ('sent', sent)
        print ('recv...')
        ret = sock.recvfrom (65536)
        print ('ret', ret)
    sock.close ()


