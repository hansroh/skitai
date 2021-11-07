from skitai.protocols.dbi.impl import syndbi, asynpsycopg2
from skitai.protocols.dbi.impl import request
from skitai import DB_SQLITE3, DB_PGSQL
from skitai.protocols.dbi.dbconnect import SQLError
import pytest

def callback1 (resp):
    assert resp.data [0].id == 1.0

def callback2 (resp):
    assert not resp.data

def callback3 (resp):
    assert len (resp.data) >= 2

def callback4 (resp):
    assert resp.data [0].symbol == "BIX"

def callback5 (resp):
    assert resp.code == 500

def test_str (dbpath, log):
    f = syndbi.SynConnect (dbpath, logger = log.get ("app"))

    statement = "SELECT * from stocks where id = 1"
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback1)
    f.execute (r)

    statement = 1
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback5)
    with pytest.raises (SQLError):
        f.execute (r)

