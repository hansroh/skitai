import pytest, os, time
import confutil
import skitai
from atila import Atila
import atila
from rs4 import logger
from skitai import offline
from skitai.offline import server, channel as cha

try:
	import pytest_ordering
except ImportError:
	raise
else:
	del pytest_ordering	

@pytest.fixture (scope = "module")
def app ():
	return Atila (__name__)

@pytest.fixture
def client ():
	return confutil.client
	
@pytest.fixture
def log ():
	logger = offline.logger ()
	yield logger
	logger.close ()

@pytest.fixture
def wasc ():
	offline.activate ()
	return offline.wasc

@pytest.fixture
def conn ():
	sock = cha.Conn ()	
	return sock

@pytest.fixture
def channel ():
	c = cha.Channel ()
	yield c
	c.close ()

@pytest.fixture
def server ():
	s = server.Server ()
	yield s
	s.close ()
	
		