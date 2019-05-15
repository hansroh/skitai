import skitai
import conftest
import sqlite3
from aquests.dbapi.synsqlite3 import SynConnect
from skitai.corequest.httpbase import task

def test_cluster_manager (wasc): 
    cluster = wasc.clusters_for_distcall ["sqlite3"]
    assert isinstance (cluster.get_endpoints ()[0], sqlite3.Connection)
    
    fkey = list (cluster.status () ['cluster'].keys ()) [0]     
    assert cluster.status () ["cluster"][fkey]["numactives"] == 0
    asyncon = cluster.get ()
    assert isinstance (asyncon, SynConnect)
    assert cluster.status () ["cluster"][fkey]["numactives"] == 1
    asyncon.set_active (False)
    assert cluster.status () ["cluster"][fkey]["numactives"] == 0
    
    assert cluster.parse_member ("asda:1231@127.0.0.1:5432/mydb") == (('asda', '1231'), '127.0.0.1:5432/mydb')

def test_task (wasc):
    cluster = wasc.clusters_for_distcall ["example"]
    cdc  = task.Task (cluster, "/index")
    