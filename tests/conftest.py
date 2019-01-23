import pytest, os, time
import confutil
import skitai
from atila import Atila
from rs4 import logger
from skitai import testutil
from skitai.testutil import server, channel as cha

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
    logger = testutil.logger ()
    yield logger
    logger.close ()

@pytest.fixture
def wasc ():
    testutil.activate ()
    return testutil.wasc

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
    import sqlite3
	
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
    
@pytest.fixture (scope = "session")
def wasc_with_clusters ():
    from skitai import PROTO_HTTP, PROTO_HTTPS, PROTO_WS, DB_PGSQL, DB_SQLITE3, DB_MONGODB, DB_REDIS
    from skitai.wsgiappservice import WAS

    def add_cluster (wasc, name, args):
	    ctype, members, policy, ssl = args
	    wasc.add_cluster (ctype, name, members, ssl, policy)
    
    wasc = testutil.setup_was (WAS) # nned real WAS from this testing    
    add_cluster (wasc, *skitai.alias ("@example", PROTO_HTTP, "www.example.com"))
    add_cluster (wasc, *skitai.alias ("@examples", PROTO_HTTPS, "www.example.com"))
    add_cluster (wasc, *skitai.alias ("@sqlite3", DB_SQLITE3, "/tmp/temp.sqlite3"))
    add_cluster (wasc, *skitai.alias ("@postgresql", DB_PGSQL, "user:pass@127.0.0.1/mydb"))
    add_cluster (wasc, *skitai.alias ("@mongodb", DB_MONGODB, "127.0.0.1:27017/mydb"))
    add_cluster (wasc, *skitai.alias ("@redis", DB_REDIS, "127.0.0.1:6379"))
    assert "example" in wasc.clusters
    assert "postgresql" in wasc.clusters
    return wasc
   
    
            