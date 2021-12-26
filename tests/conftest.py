import pytest, os, time
import confutil
import skitai
from atila import Atila
from rs4 import logger
from skitai.testutil import offline
from skitai.testutil.offline.server import Server, Conn, Channel
from skitai import PROTO_HTTP, PROTO_HTTPS, PROTO_WS, DB_PGSQL, DB_SQLITE3, DB_MONGODB, DB_REDIS
import sys
import pytest

def pytest_addoption (parser):
    parser.addoption (
        "--slow", action="store_true", default=False, help="run slow tests"
    )

def pytest_collection_modifyitems (config, items):
    if config.getoption ("--slow"):
        return
    skip_slow = pytest.mark.skip (reason = "need --slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker (skip_slow)

try:
    import pytest_ordering
except ImportError:
    raise
else:
    del pytest_ordering

@pytest.fixture
def is_pypy ():
    return '__pypy__' in sys.builtin_module_names

@pytest.fixture
def log ():
    logger = offline.logger ()
    yield logger
    logger.close ()

@pytest.fixture (scope = "module")
def app ():
    app_ = Atila (__name__)
    app_.logger = logger.screen_logger ()
    return app_

@pytest.fixture
def client ():
    return confutil.client

@pytest.fixture
def conn ():
    sock = Conn ()
    return sock

@pytest.fixture
def channel ():
    c = Channel ()
    yield c
    c.close ()

@pytest.fixture
def server ():
    s = Server ()
    yield s
    s.close ()

@pytest.fixture (scope = "session")
def wasc ():
    offline.activate (make_sync = True)
    return offline.wasc

@pytest.fixture (scope = "session")
def async_wasc ():
    from atila.was import WAS
    wasc = offline.setup_was (WAS) # nned real WAS from this testing

    assert "example" in wasc.clusters
    assert "postgresql" in wasc.clusters
    return wasc

DBPATH = offline.SAMPLE_DBPATH

@pytest.fixture (scope = "session")
def dbpath ():
    import sqlite3

    conn = sqlite3.connect (DBPATH)
    c = conn.cursor()
    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS stocks (id real, date text, trans text, symbol text, qty real, price real)''')
    c.execute("INSERT INTO stocks VALUES (1, '2006-01-05','BUY','RHAT',100,35.14)")
    c.execute('''CREATE TABLE IF NOT EXISTS people (id real, name text)''')
    c.execute("INSERT INTO people VALUES (1, 'Hans Roh')")
    conn.commit()
    c.fetchall()
    c.close ()
    yield DBPATH
    conn.close ()
    os.unlink (DBPATH)

