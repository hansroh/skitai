import pytest, os
import confutil
from skitai.saddle import Saddle

@pytest.fixture (scope = "module")
def app ():
	return Saddle (__name__)
	
@pytest.fixture
def log ():
	logger = confutil.logger ()
	yield logger
	logger.close ()

@pytest.fixture
def wasc ():
	return confutil.wasc	
	
@pytest.fixture
def conn ():
	sock = confutil.conn	
	return sock

@pytest.fixture
def server ():
	s = confutil.server ()
	yield s
	s.close ()

@pytest.fixture
def channel ():
	c = confutil.channel ()
	yield c
	c.close ()


		