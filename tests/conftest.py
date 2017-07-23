import pytest, os
import confutil
from skitai.saddle import Saddle
from aquests.lib import commprocess, logger
try:
	import pytest_ordering
except ImportError:
	raise
else:
	del pytest_ordering	

@pytest.fixture (scope = "module")
def runner ():
	p = commprocess.Process (communicate = False)
	return p
	
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


		