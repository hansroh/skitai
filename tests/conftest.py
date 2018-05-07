import pytest, os, time
import confutil
import skitai
from skitai.saddle import Saddle
from skitai import saddle
from aquests.lib import logger
from skitai.server import offline
from skitai.server.offline import server, channel as cha

try:
	import pytest_ordering
except ImportError:
	raise
else:
	del pytest_ordering	

@pytest.fixture (scope = "module")
def app ():
	return Saddle (__name__)

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
	
		