import pytest, os
from skitai.server.wastuff import triple_logger
from skitai.server.http_server import http_server, http_channel
from skitai.server.handlers import pingpong_handler
from mock import MagicMock
import socket
	
@pytest.fixture
def log ():
	logger = triple_logger.Logger ("screen", None)
	yield logger
	logger.close ()

@pytest.fixture
def conn ():
	sock = MagicMock (name="socket", spec = socket.socket)
	sock.send.fileno = 10
	return sock

@pytest.fixture
def server (log):
	s = http_server ('0.0.0.0', 3000, log.get ("server"), log.get ("request"))	
	s.install_handler (pingpong_handler.Handler ())
	yield s
	s.close ()

@pytest.fixture
def channel (server, conn):
	import confutil
	
	c = http_channel (server, conn, ('127.0.0.100', 65535))
	c.connected = True
	confutil.CHANNEL = c
	yield c
	c.close ()


	