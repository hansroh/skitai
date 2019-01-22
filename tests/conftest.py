import pytest, os, time
import confutil
import skitai
from atila import Atila
import atila
from rs4 import logger
from skitai import offline
from skitai.offline import server, channel as cha
import sqlite3

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


DBPATH = os.path.join (os.path.dirname (__file__), 'example.sqlite')
	
@pytest.fixture (scope = "session")
def dbpath ():	
	conn = sqlite3.connect (DBPATH)
	c = conn.cursor()
	# Create table
	c.execute('''CREATE TABLE IF NOT EXISTS stocks (date text, trans text, symbol text, qty real, price real)''')
	c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")	
	conn.commit()
	c.fetchall()
	c.close ()
	yield DBPATH
	conn.close ()
	os.unlink (DBPATH)
	
		