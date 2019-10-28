import pytest
import os
import socket
import time

@pytest.mark.skip
def test_http3 (launch):
    serve = '../examples/http3.py'
    with launch (serve, port = 30443) as engine:
        resp = engine.get ("/")

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


