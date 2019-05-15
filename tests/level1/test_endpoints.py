from skitai import DB_PGSQL, DB_SQLITE3
from skitai.corequest.dbi import endpoints, cluster_manager
import psycopg2
from sqlphile.pg2 import open2
from sqlphile.db3 import open
import os
import warnings
            
def test_endpoints (dbpath):
    try:
        conn = endpoints.make_endpoints (DB_PGSQL, [("192.168.0.80", "aw1", ("postgres", os.environ.get ("PGPASSWORD", "")))]) [0]
    except psycopg2.OperationalError:
        warnings.warn ("Please set PGPASSWORD", Warning)
        return   
    assert conn.closed == False
    with open2 (conn, endpoints.PGPOOL) as db:
        assert conn == db.conn        

def test_cluster_manager (dbpath):
    m = cluster_manager.ClusterManager ("sqlite3", [dbpath], DB_SQLITE3)
    with m.getconn () as db:
        db.select ("stocks").execute ()
        assert "id" in db.fetchall (True)[0]

    if not os.environ.get ("PGPASSWORD", ""):
        return
        
    m = cluster_manager.ClusterManager ("pg", ["postgres:{}@192.168.0.80/aw1".format (os.environ.get ("PGPASSWORD", ""))])    
    try:
        conn = m.getconn ()
    except psycopg2.OperationalError:
        return
    with conn as db:
        assert db.closed == False
        db.select ("auth_user").execute ()
        assert "id" in db.fetchall (True)[0]
    